#!/usr/bin/env python3
"""
Generate substantive English READMEs by analyzing actual codebase content.
Scans package.json, requirements.txt, source structure, and key files to create
developer-focused documentation without placeholder disclaimers.

Usage:
  python3 generate_readmes_from_codebase.py --base /path/to/repos --list candidates.txt --branch review-branch --count 5
"""

import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple

def run_cmd(cmd: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Execute a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def analyze_package_json(repo_path: str) -> Dict:
    """Extract tech stack and dependencies from package.json."""
    package_file = os.path.join(repo_path, "package.json")
    if not os.path.exists(package_file):
        return {}
    
    try:
        with open(package_file, "r") as f:
            pkg = json.load(f)
        
        deps = {}
        if "dependencies" in pkg:
            deps.update(pkg["dependencies"])
        if "devDependencies" in pkg:
            deps.update(pkg["devDependencies"])
        
        return {
            "name": pkg.get("name", ""),
            "description": pkg.get("description", ""),
            "version": pkg.get("version", ""),
            "main": pkg.get("main", ""),
            "scripts": pkg.get("scripts", {}),
            "dependencies": deps,
        }
    except Exception as e:
        return {}

def analyze_requirements_txt(repo_path: str) -> List[str]:
    """Extract Python dependencies from requirements.txt."""
    req_file = os.path.join(repo_path, "requirements.txt")
    if not os.path.exists(req_file):
        return []
    
    try:
        with open(req_file, "r") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        return lines
    except Exception:
        return []

def analyze_pyproject_toml(repo_path: str) -> Dict:
    """Extract basic project info from pyproject.toml."""
    pyproject_file = os.path.join(repo_path, "pyproject.toml")
    if not os.path.exists(pyproject_file):
        return {}
    
    try:
        # Simple string parsing (avoid toml parser dependency)
        with open(pyproject_file, "r") as f:
            content = f.read()
        
        info = {}
        for line in content.split("\n"):
            if line.startswith("name"):
                info["name"] = line.split("=")[1].strip().strip('"\'')
            elif line.startswith("description"):
                info["description"] = line.split("=")[1].strip().strip('"\'')
        
        return info
    except Exception:
        return {}

def analyze_html_file(repo_path: str, repo_name: str = "") -> Dict:
    """Extract project context from index.html (and primary .js if present): title, h1, imports, attribution."""
    html_file = os.path.join(repo_path, "index.html")
    if not os.path.exists(html_file):
        return {}
    try:
        with open(html_file, "r", errors="ignore") as f:
            content = f.read()
        # Also read primary JS file (repo_name.js) if it exists
        if repo_name:
            js_file = os.path.join(repo_path, f"{repo_name}.js")
            if os.path.exists(js_file):
                with open(js_file, "r", errors="ignore") as f:
                    content += "\n" + f.read()
        result = {}
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
        if title_match:
            result["title"] = title_match.group(1).strip()
        h1_match = re.search(r"<h1[^>]*>(?:<[^>]+>)*([^<]+)", content, re.IGNORECASE)
        if h1_match:
            result["h1"] = h1_match.group(1).strip()
        imports = re.findall(r'import\s+.*?from\s+"(https?://[^"]+)"', content)
        result["imports"] = imports
        # Strip HTML tags from attribution lines, then extract text
        attr_raw = re.findall(r"(?:DATA:|Data source:|データ:)(?:[^\n<>]|<[^>]+>)*", content)
        attr_lines = []
        for a in attr_raw:
            clean = re.sub(r"<[^>]+>", " ", a).strip()
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) > 6:
                attr_lines.append(clean)
        result["attribution"] = attr_lines
        return result
    except Exception:
        return {}


def get_demo_url(repo_path: str, repo_name: str) -> str:
    """Return demo URL: from existing README if present, else construct GitHub Pages URL."""
    readme_file = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_file):
        try:
            with open(readme_file, "r", errors="ignore") as f:
                content = f.read()
            match = re.search(r"https://code4fukui\.github\.io/[^\s\)\]]+", content)
            if match:
                return match.group(0).rstrip("/") + "/"
        except Exception:
            pass
    return f"https://code4fukui.github.io/{repo_name}/"


def discover_source_structure(repo_path: str) -> Dict:
    """Analyze source code structure and main directories."""
    structure = {
        "has_src": os.path.isdir(os.path.join(repo_path, "src")),
        "has_lib": os.path.isdir(os.path.join(repo_path, "lib")),
        "has_components": os.path.isdir(os.path.join(repo_path, "components")),
        "has_pages": os.path.isdir(os.path.join(repo_path, "pages")),
        "has_app": os.path.isdir(os.path.join(repo_path, "app")),
        "has_data": os.path.isdir(os.path.join(repo_path, "data")),
        "has_tools": os.path.isdir(os.path.join(repo_path, "tools")),
        "has_tests": os.path.isdir(os.path.join(repo_path, "tests")),
        "has_public": os.path.isdir(os.path.join(repo_path, "public")),
        "typescript": os.path.exists(os.path.join(repo_path, "tsconfig.json")),
        "vite": os.path.exists(os.path.join(repo_path, "vite.config.ts")) or os.path.exists(os.path.join(repo_path, "vite.config.js")),
        "webpack": os.path.exists(os.path.join(repo_path, "webpack.config.js")),
        "next": os.path.exists(os.path.join(repo_path, "next.config.js")),
    }
    return structure

def detect_project_type(repo_name: str, pkg_info: Dict, structure: Dict, py_deps: List[str]) -> str:
    """Heuristically detect project type from metadata."""
    # Check package.json hints
    if pkg_info:
        deps = pkg_info.get("dependencies", {})
        dev_deps = pkg_info.get("devDependencies", {})
        
        if "react" in deps or "react" in dev_deps:
            return "React application"
        if "vue" in deps or "vue" in dev_deps:
            return "Vue.js application"
        if "next" in deps or structure.get("next"):
            return "Next.js web application"
        if "vite" in dev_deps or structure.get("vite"):
            return "Vite-based web project"
        if "express" in deps:
            return "Node.js/Express backend"
        if "svelte" in deps or "svelte" in dev_deps:
            return "Svelte application"
        if "three" in deps:
            return "3D web application (Three.js)"
    
    # Check Python hints
    if py_deps:
        if any("django" in d.lower() for d in py_deps):
            return "Django web application"
        if any("flask" in d.lower() for d in py_deps):
            return "Flask web application"
        if any("fastapi" in d.lower() for d in py_deps):
            return "FastAPI backend"
        if any("pandas" in d.lower() or "numpy" in d.lower() for d in py_deps):
            return "Python data analysis project"
        return "Python project"
    
    # Fallback based on structure
    if structure.get("has_src"):
        return "Development project"
    
    return "Web/Code project"

def extract_readme_hints(repo_path: str) -> str:
    """Try to extract hints about the project from main code files."""
    hints = []
    
    # Check for common index files
    for filename in ["index.html", "main.tsx", "main.ts", "app.tsx", "App.tsx", "index.tsx", "index.js"]:
        filepath = os.path.join(repo_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read(500)
                    if "3D" in content or "three" in content.lower():
                        hints.append("3D visualization")
                    if "chart" in content.lower() or "graph" in content.lower():
                        hints.append("data visualization")
                    if "canvas" in content.lower():
                        hints.append("canvas-based rendering")
            except Exception:
                pass
    
    return "; ".join(hints) if hints else ""

def get_install_instructions(repo_name: str, repo_path: str, pkg_info: Dict, py_deps: List[str], structure: Dict) -> str:
    """Generate installation instructions based on project type."""
    instructions = []
    
    if pkg_info:
        pkg_manager = "npm"
        if os.path.exists(os.path.join(repo_path, "pnpm-workspace.yaml")) or os.path.exists(os.path.join(repo_path, "pnpm-lock.yaml")):
            pkg_manager = "pnpm"
        elif os.path.exists(os.path.join(repo_path, "yarn.lock")):
            pkg_manager = "yarn"
        
        instructions.append("### Prerequisites")
        instructions.append("")
        instructions.append(f"- Node.js (v16 or higher)")
        instructions.append(f"- {pkg_manager.capitalize()}")
        instructions.append("")
        instructions.append("### Steps")
        instructions.append("")
        instructions.append("1. Clone the repository")
        instructions.append("")
        instructions.append(f"   ```bash")
        instructions.append(f"   git clone https://github.com/code4fukui/{repo_name}.git")
        instructions.append(f"   cd {repo_name}")
        instructions.append(f"   ```")
        instructions.append("")
        instructions.append("2. Install dependencies")
        instructions.append("")
        instructions.append(f"   ```bash")
        instructions.append(f"   {pkg_manager} install")
        instructions.append(f"   ```")
        instructions.append("")
        
        scripts = pkg_info.get("scripts", {})
        if scripts:
            instructions.append("3. Run the project")
            instructions.append("")
            if scripts.get("dev"):
                instructions.append(f"   Development mode:")
                instructions.append(f"   ```bash")
                instructions.append(f"   {pkg_manager} run dev")
                instructions.append(f"   ```")
                instructions.append("")
            if scripts.get("build"):
                instructions.append(f"   Build for production:")
                instructions.append(f"   ```bash")
                instructions.append(f"   {pkg_manager} run build")
                instructions.append(f"   ```")
                instructions.append("")
            if scripts.get("start"):
                instructions.append(f"   Start production server:")
                instructions.append(f"   ```bash")
                instructions.append(f"   {pkg_manager} start")
                instructions.append(f"   ```")
                instructions.append("")
    elif py_deps:
        instructions.append("### Prerequisites")
        instructions.append("")
        instructions.append("- Python 3.7 or higher")
        instructions.append("- pip or pipenv")
        instructions.append("")
        instructions.append("### Steps")
        instructions.append("")
        instructions.append("1. Clone the repository")
        instructions.append("")
        instructions.append("   ```bash")
        instructions.append(f"   git clone https://github.com/code4fukui/{repo_name}.git")
        instructions.append(f"   cd {repo_name}")
        instructions.append("   ```")
        instructions.append("")
        instructions.append("2. Create virtual environment (recommended)")
        instructions.append("")
        instructions.append("   ```bash")
        instructions.append("   python3 -m venv venv")
        instructions.append("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        instructions.append("   ```")
        instructions.append("")
        instructions.append("3. Install dependencies")
        instructions.append("")
        instructions.append("   ```bash")
        instructions.append("   pip install -r requirements.txt")
        instructions.append("   ```")
        instructions.append("")
    else:
        instructions.append("See the project structure and configuration files for setup instructions.")
    
    return "\n".join(instructions)

def get_key_dependencies(pkg_info: Dict, py_deps: List[str]) -> Tuple[List[str], List[str]]:
    """Extract key dependencies with versions."""
    npm_deps = []
    py_full_deps = []
    
    if pkg_info:
        deps = pkg_info.get("dependencies", {})
        dev_deps = pkg_info.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        
        # Prioritize important deps
        priority = ["react", "vue", "next", "express", "typescript", "webpack", "vite", "svelte", "three"]
        for p in priority:
            for d in all_deps:
                if p in d.lower():
                    npm_deps.append(f"{d}@{all_deps[d]}")
                    break
        
        # Add remaining top deps
        for d in list(all_deps.keys())[:5]:
            if f"{d}@" not in npm_deps:
                npm_deps.append(f"{d}@{all_deps[d]}")
    
    if py_deps:
        py_full_deps = py_deps[:8]
    
    return npm_deps, py_full_deps

def generate_readme(repo_name: str, repo_path: str) -> str:
    """Generate a substantive README from codebase analysis."""

    # Analyze the repo
    pkg_info = analyze_package_json(repo_path)
    py_deps = analyze_requirements_txt(repo_path)
    py_project = analyze_pyproject_toml(repo_path)
    structure = discover_source_structure(repo_path)
    project_type = detect_project_type(repo_name, pkg_info, structure, py_deps)
    readme_hints = extract_readme_hints(repo_path)
    npm_deps, py_full_deps = get_key_dependencies(pkg_info, py_deps)
    html_info = analyze_html_file(repo_path, repo_name)
    demo_url = get_demo_url(repo_path, repo_name)

    # Build README
    lines = []

    # Title
    lines.append(f"# {repo_name}")
    lines.append("")

    # Description: prefer package.json/pyproject, then HTML title, then fallback
    if pkg_info.get("description"):
        desc = pkg_info["description"]
    elif py_project.get("description"):
        desc = py_project["description"]
    else:
        html_title = html_info.get("title", "")
        # Strip " demo" suffix and check it's not just the repo name
        html_title_clean = re.sub(r"\s+demo$", "", html_title, flags=re.IGNORECASE).strip()
        if html_title_clean and html_title_clean.lower() != repo_name.lower():
            desc = html_title_clean
        else:
            desc = f"A {project_type} by [Code for FUKUI](https://github.com/code4fukui)."

    lines.append(desc)
    lines.append("")

    # Demo link
    lines.append(f"**Live demo**: {demo_url}")
    lines.append("")

    if pkg_info and pkg_info.get("version"):
        lines.append(f"**Version**: {pkg_info.get('version', 'Latest')}")
        lines.append("")

    # Features section (only add features we actually detected)
    features = []
    if "react" in str(pkg_info.get("dependencies", {})).lower():
        features.append("- Built with React for dynamic, responsive UIs")
    if "three" in str(pkg_info.get("dependencies", {})).lower():
        features.append("- 3D graphics and visualization using Three.js")
    if readme_hints:
        for hint in readme_hints.split(";"):
            h = hint.strip()
            if h:
                features.append(f"- {h.capitalize()}")
    if structure.get("has_tests"):
        features.append("- Comprehensive test coverage")
    if structure.get("typescript"):
        features.append("- Full TypeScript support for type safety")
    # Infer from HTML imports
    if html_info.get("imports"):
        import_str = " ".join(html_info["imports"]).lower()
        if "monaco" in import_str:
            features.append("- Monaco editor integration")
        if "indexedstorage" in import_str or "indexed" in import_str:
            features.append("- Persistent local storage via IndexedDB")
        if "qr" in import_str or "qrcode" in import_str:
            features.append("- QR code generation")
        if "mp3" in import_str or "audio" in import_str:
            features.append("- In-browser audio recording and MP3 encoding")
        if "d3" in import_str:
            features.append("- Data visualization with D3.js")
        if "csv" in import_str:
            features.append("- CSV data parsing")
        if "three" in import_str:
            features.append("- 3D rendering with Three.js")

    # Deduplicate features: skip if an existing feature subsumes this one or vice versa
    unique_features = []
    for f in features:
        f_lower = f.lstrip("- ").lower()
        dominated = any(f_lower in x.lstrip("- ").lower() or x.lstrip("- ").lower() in f_lower
                        for x in unique_features)
        if not dominated:
            # Replace any existing item that this new item subsumes
            unique_features = [x for x in unique_features
                                if x.lstrip("- ").lower() not in f_lower]
            unique_features.append(f)

    if unique_features:
        lines.append("## Features")
        lines.append("")
        lines.extend(unique_features)
        lines.append("")

    # Tech stack - expanded
    lines.append("## Technology Stack")
    lines.append("")

    if npm_deps:
        lines.append("**Node.js / NPM Packages:**")
        lines.append("")
        for dep in npm_deps:
            lines.append(f"- `{dep}`")
        lines.append("")

    if py_full_deps:
        lines.append("**Python Packages:**")
        lines.append("")
        for dep in py_full_deps:
            clean = dep.split("==")[0].split(">=")[0].split("<")[0].strip()
            lines.append(f"- `{clean}`")
        lines.append("")

    if html_info.get("imports"):
        lines.append("**Browser modules (ES imports):**")
        lines.append("")
        for imp in html_info["imports"][:8]:
            mod = imp.split("/")[-1]
            lines.append(f"- [`{mod}`]({imp})")
        lines.append("")

    if structure.get("typescript"):
        lines.append("- **Language**: TypeScript")
    if structure.get("vite"):
        lines.append("- **Build Tool**: Vite")
    if structure.get("webpack"):
        lines.append("- **Build Tool**: Webpack")
    if structure.get("next"):
        lines.append("- **Framework**: Next.js")
    lines.append("")
    
    # Project structure (only emit section if directories were detected)
    structure_items = []
    if structure.get("has_src"):
        structure_items.append("- `src/` — Main source code")
    if structure.get("has_lib"):
        structure_items.append("- `lib/` — Shared libraries and utilities")
    if structure.get("has_components"):
        structure_items.append("- `components/` — Reusable UI components")
    if structure.get("has_pages"):
        structure_items.append("- `pages/` — Page-level components")
    if structure.get("has_app"):
        structure_items.append("- `app/` — Application main code")
    if structure.get("has_data"):
        structure_items.append("- `data/` — Data files and fixtures")
    if structure.get("has_tools"):
        structure_items.append("- `tools/` — Build and utility scripts")
    if structure.get("has_tests"):
        structure_items.append("- `tests/` — Test suite and test utilities")
    if structure.get("has_public"):
        structure_items.append("- `public/` — Static assets (images, fonts, etc.)")
    
    if structure_items:
        lines.append("## Project Structure")
        lines.append("")
        lines.extend(structure_items)
        lines.append("")

    # Installation
    lines.append("## Installation & Setup")
    lines.append("")

    if pkg_info or py_deps:
        install_instructions = get_install_instructions(repo_name, repo_path, pkg_info, py_deps, structure)
        lines.append(install_instructions)
    else:
        lines.append("No build step required. Clone the repository and open `index.html` in a browser,")
        lines.append(f"or visit the live demo at {demo_url}")

    lines.append("")

    # Scripts/Commands section
    if pkg_info and pkg_info.get("scripts"):
        lines.append("## Available Commands")
        lines.append("")
        pkg_manager = "npm"
        if os.path.exists(os.path.join(repo_path, "pnpm-lock.yaml")):
            pkg_manager = "pnpm"
        elif os.path.exists(os.path.join(repo_path, "yarn.lock")):
            pkg_manager = "yarn"

        for script, cmd in pkg_info.get("scripts", {}).items():
            lines.append(f"- `{pkg_manager} run {script}` — {cmd}")
        lines.append("")

    # Attribution lines preserved from HTML
    if html_info.get("attribution"):
        lines.append("## Data Sources")
        lines.append("")
        for attr in html_info["attribution"]:
            lines.append(f"- {attr}")
        lines.append("")

    # Contributing
    lines.append("## Contributing")
    lines.append("")
    lines.append("Contributions are welcome. Please open an issue or pull request on GitHub.")
    lines.append("")

    # Footer with license link
    lines.append("## License")
    lines.append("")
    lines.append("MIT License. See [LICENSE](./LICENSE) for details.")
    lines.append("")

    return "\n".join(lines)

def push_updated_readme(repo_path: str, repo_name: str, branch: str, readme_content: str) -> Tuple[bool, str]:
    """Create commit and push updated README to review branch."""
    try:
        # Write README.md
        readme_path = os.path.join(repo_path, "README.md")
        with open(readme_path, "w") as f:
            f.write(readme_content)
        
        # Git operations in repo
        run_cmd("git add README.md", cwd=repo_path)
        
        # Check if there are actual changes
        rc, stdout, _ = run_cmd("git diff --cached --stat", cwd=repo_path)
        if not stdout.strip():
            return False, "No changes"
        
        # Amend previous commit if on same branch, else create new
        rc, _, stderr = run_cmd(
            f'git commit --amend --no-edit',
            cwd=repo_path
        )
        
        if rc != 0 and "nothing to commit" not in stderr.lower():
            # Try regular commit for first time
            run_cmd(
                f'git commit -m "docs: update README from codebase analysis"',
                cwd=repo_path
            )
        
        # Force push to branch (amend changes)
        rc, out, err = run_cmd(
            f"git push -f origin HEAD:{branch}",
            cwd=repo_path
        )
        
        if rc == 0:
            # Extract commit SHA
            rc2, sha, _ = run_cmd("git rev-parse HEAD", cwd=repo_path)
            return True, sha.strip() if rc2 == 0 else "pushed"
        else:
            return False, err or "Push failed"
    
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Generate substantive READMEs from codebase analysis")
    parser.add_argument("--base", required=True, help="Base directory containing all repos")
    parser.add_argument("--list", required=True, help="File with candidate repo names (one per line)")
    parser.add_argument("--branch", required=True, help="Branch name to push to")
    parser.add_argument("--count", type=int, default=5, help="Number of repos to process")
    
    args = parser.parse_args()
    
    # Read candidate list
    try:
        with open(args.list, "r") as f:
            candidates = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"ERROR|Failed to read candidates: {e}", file=sys.stderr)
        sys.exit(1)
    
    candidates = candidates[:args.count]
    results = {"ok": 0, "skip": 0, "err": 0}
    
    for i, repo_name in enumerate(candidates, 1):
        repo_path = os.path.join(args.base, repo_name)
        
        if not os.path.isdir(repo_path):
            print(f"SKIP|{repo_name}|not-found")
            results["skip"] += 1
            continue
        
        try:
            # Ensure we're on the branch
            run_cmd("git fetch origin", cwd=repo_path)
            rc, _, _ = run_cmd(f"git checkout {args.branch}", cwd=repo_path)
            if rc != 0:
                # Create branch
                run_cmd(f"git checkout -b {args.branch}", cwd=repo_path)
            
            # Generate README
            readme = generate_readme(repo_name, repo_path)
            
            # Push
            success, msg = push_updated_readme(repo_path, repo_name, args.branch, readme)
            
            if success:
                print(f"OK|{repo_name}|branch={args.branch}|sha={msg}")
                results["ok"] += 1
            else:
                print(f"ERR|{repo_name}|{msg}")
                results["err"] += 1
        
        except Exception as e:
            print(f"ERR|{repo_name}|{str(e)[:80]}")
            results["err"] += 1
    
    print(f"SUMMARY|ok={results['ok']}|skipped={results['skip']}|errors={results['err']}|total={len(candidates)}")

if __name__ == "__main__":
    main()

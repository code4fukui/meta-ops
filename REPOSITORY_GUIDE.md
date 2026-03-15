# Code for FUKUI Repository Guide

## What This Guide Is

This guide is a practical map of the Code for FUKUI repository ecosystem for international developers. It is based on the current repository set and the refreshed English and Japanese READMEs generated in this workflow.

As of this snapshot, the organization contains 1271 repositories. The collection is unusually broad: civic tech, open data publishing, tourism analytics, geospatial tools, visualization apps, reusable JavaScript utilities, education projects, creative coding, and XR experiments all live side by side.

## What Code for FUKUI Looks Like In Practice

Code for FUKUI is not a single product repository. It is a large working archive of public-interest software and reusable web tooling.

A lot of the output is practical and local:
- Fukui tourism data pipelines
- dashboards and visualizations
- maps and disaster/environment tools
- educational apps and civic explainers

Another large part of the org is general-purpose JavaScript, Deno, and web-component work that can be reused outside Fukui.

## Major Repository Families

### Tourism, Open Data, and Regional Analytics

This is one of the clearest high-value areas for global contributors because it combines public-interest data, reproducible ETL, and public-facing visualizations.

Representative repos in this workspace:
- `fukui-kanko-survey`
- `fukui-kanko-advice`
- `fukui-kanko-people-flow-data`
- `fukui-kanko-people-flow-visualization`
- `fukui-kanko-trend-report`
- `japan-kanko-dashboard`

Typical patterns:
- CSV and JSON open data publishing
- scheduled batch scripts
- GitHub Pages publishing
- HTML/JS dashboards
- React/Vite frontends for exploration and reporting

### Maps, Geospatial, and Public Information

Another strong cluster is mapping, geospatial overlays, and location-aware civic information. These repos are often small and direct: a map layer, a hazard view, an overlay, a data transformation, or a focused visualization.

Representative examples visible from the current repo set and generated docs include map- and hazard-oriented repos, tourism maps, and geospatial dashboards.

Typical patterns:
- client-side mapping
- GeoJSON and CSV ingestion
- browser-first deployments
- light server assumptions

### Reusable JavaScript and Web Utilities

A large share of the organization is made up of small focused libraries and developer utilities. Many repos are intentionally narrow: encoding, parsing, rendering, browser APIs, Web Components, or small Deno/JS helpers.

This matters because Code for FUKUI is not only a civic-tech org; it is also a prolific software workshop. Many repos are composable building blocks rather than apps.

Typical patterns:
- ES module packages
- Deno-compatible code
- no-build or minimal-build browser tooling
- narrow single-purpose utilities

### Visualization, XR, and Creative Computing

The org also contains many experimental and public-facing interactive projects: 3D viewers, AR/VR demos, WebXR, image/video tools, and creative prototypes.

These repos often emphasize:
- immediate browser demos
- visual output over backend complexity
- WebGL / Three.js style ecosystems
- small focused experiments rather than monoliths

### Education, Play, and Public Learning Tools

A distinct family of repos is designed to teach, explain, or engage. These include games, quizzes, typing tools, learning-oriented utilities, and culturally specific interactive projects.

This makes the org especially approachable for contributors who enjoy product clarity and fast feedback loops.

## Common Tech Stack Patterns

Across the current repo set, the most common patterns are:

- HTML, CSS, JavaScript, and TypeScript as the default surface area
- Deno for scripts, automation, and data-processing utilities
- React/Vite for richer visualization apps
- CSV and JSON as the dominant exchange formats
- GitHub Pages style static hosting assumptions
- low-ceremony repos with direct runnable entry points

Common repo shapes:
- a single `index.html` plus a few scripts
- data repository with generated CSVs/JSONs
- small library with a README and a couple of source files
- visualization monorepo with packages and shared components

## Good Starting Points For Global Developers

If your goal is to understand the ecosystem quickly, start with repos that reveal how the org works end to end.

### Best system repos

- `fukui-kanko-survey`
- `fukui-kanko-advice`
- `fukui-kanko-people-flow-data`
- `fukui-kanko-people-flow-visualization`
- `fukui-kanko-trend-report`

### Best entry-level contribution areas

- documentation improvements
- English/Japanese consistency fixes
- demo validation and link cleanup
- data schema explanation
- issue triage for small utility repos

## Working Norms For Global Contributors

The safest assumptions for contributing here are:

- prefer small, scoped changes
- preserve static-hosting friendliness
- expect some repos to be personal or experimental rather than productized
- document changes clearly in English
- keep Japanese content available where possible

For the README globalization work specifically:

- `README.md` is the English default entry point
- `README.ja.md` is the Japanese companion
- English READMEs should include a top link to `README.ja.md`
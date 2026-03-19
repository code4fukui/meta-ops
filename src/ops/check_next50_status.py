import subprocess
from pathlib import Path

base = Path('/home/ubuntu/code4fukui')
repos = [
'form-data-encoder','fragment-shader-examples','free-bgm-player','freq-analyzer','FSH','fu','fukucha','fukui','fukui-bichiku-navi','fukui-camp-pass','fukui-chijihai-hackathon-20240901','fukui-event','fukui-kanko','fukui-kanko-advice','fukui-kanko-civic-voice','fukui-kanko-coupon','fukui-kanko-hack','fukui-kanko-hackathon-20220716','fukui-kanko-hackathon-20230107','fukui-kanko-hackathon-20231216','fukui-kanko-hashtag','fukui-kanko-map','fukui-kanko-stat','fukui-kanko-wordcloud','fukui-movie-fes','fukui-night','fukui-pref','fukui-sea','fukui-spot-similar','fukui-tech','fukui_eatsafe','fukui_old_train','fukuigc','fukuoka-city','fukutetsu-opendata','fullscreen-canvas','gamemap','Gamepad','Gatcha-tag','GBizID-es','gBizINFO','GeocodingJP','geojson-map','gesture2sound','gifuct-js','GitHub','gl-matrix','glass-button','glb-viewer','glsl-parser'
]

print('repo|ahead|behind|local|upstream|status')
for r in repos:
    rp = base / r
    try:
        ahead = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','@{u}..HEAD'], text=True).strip())
        behind = int(subprocess.check_output(['git','-C',str(rp),'rev-list','--count','HEAD..@{u}'], text=True).strip())
        local = subprocess.check_output(['git','-C',str(rp),'rev-parse','--short','HEAD'], text=True).strip()
        upstream = subprocess.check_output(['git','-C',str(rp),'rev-parse','--short','@{u}'], text=True).strip()
        status = 'ALREADY_PUSHED' if ahead == 0 and behind == 0 and local == upstream else ('PENDING' if ahead > 0 and behind == 0 else 'DIVERGED')
        print(f'{r}|{ahead}|{behind}|{local}|{upstream}|{status}')
    except Exception as e:
        print(f'{r}|ERR|ERR|ERR|ERR|ERROR')

#!/usr/bin/env python3
"""Install and launch Radmir CRMP in an independent, logged prefix."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HOME=Path.home()
PREFIX=HOME/'Games/radmir-crmp/prefix'
STATE=HOME/'.local/state/radmir-lab'
DATA=HOME/'.var/app/io.github.Faugus.faugus-launcher/data/faugus-launcher'
RUNNER=HOME/'.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/GE-Proton11-11-x86_64'


def command(exe, logs):
    env={'WINEPREFIX':str(PREFIX),'PROTONPATH':str(RUNNER.resolve()),'GAMEID':'0',
         'UMU_LOG':'info','PROTON_LOG':'0','WINEDEBUG':os.environ.get('RADMIR_WINEDEBUG','-all,err+all,warn+seh'),
         'PROTON_USE_WOW64':'0','UMU_USE_STEAM':'1','UMU_CONTAINER_NSENTER':'1'}
    hud=Path(os.environ.get('XDG_DATA_HOME',str(HOME/'.local/share')))/'samp-linux-lab/radmir-crmp'
    if (hud/'MangoHud.conf').is_file() and (hud/'presets.conf').is_file() and (hud/'layers').is_dir():
        env.update(DXVK_HUD='0',MANGOHUD='1',
                   MANGOHUD_CONFIGFILE=str(hud/'MangoHud.conf'),
                   MANGOHUD_PRESETSFILE=str(hud/'presets.conf'),
                   VK_ADD_IMPLICIT_LAYER_PATH=str(hud/'layers'))
    args=['flatpak','run','--command=env','--filesystem='+str(RUNNER.resolve())+':ro',
          '--filesystem='+str(PREFIX),'--filesystem='+str(exe.parent),
          '--filesystem='+str(logs),'io.github.Faugus.faugus-launcher']
    for key in ['WINEDLLOVERRIDES','PROTON_USE_WINED3D','PROTON_HEAP_DELAY_FREE',
                'PROTON_FORCE_LARGE_ADDRESS_AWARE','PROTON_ENABLE_WAYLAND','STEAM_COMPAT_CONFIG']:
        args+=['-u',key]
    args += [k+'='+v for k,v in env.items()]
    return args+[str(DATA/'umu-run'),str(exe)]


def run(exe, logs, stage):
    path=logs/(stage+'.log')
    print('Запуск: '+str(exe)+'\nЛог: '+str(path),flush=True)
    with path.open('w') as output:
        proc=subprocess.Popen(command(exe,logs),cwd=exe.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        for line in proc.stdout:
            output.write(line); output.flush(); print(line,end='',flush=True)
        return proc.wait()


def candidates():
    result=[]
    if not (PREFIX/'drive_c').exists(): return result
    for p in (PREFIX/'drive_c').rglob('*.exe'):
        lower=str(p.relative_to(PREFIX/'drive_c')).lower()
        name=p.name.lower()
        if '/windows/' in '/'+lower or 'radmir' not in lower: continue
        if any(s in name for s in ['unins','helper','crash','setup','redist']): continue
        if 'launcher' in name or name in ['radmir.exe','rdmr.exe']:
            result.append(p)
    return result


def register(exe):
    p=DATA/'games.json'
    original=p.read_bytes() if p.exists() else b'[]'
    games=json.loads(original)
    record=next((g for g in games if g.get('gameid')=='radmir-crmp'),None)
    if record is None:
        record={'gameid':'radmir-crmp','title':'Radmir CRMP','launch_arguments':'PROTON_USE_WOW64=0',
                'game_arguments':'','playtime':0,'hidden':False,'runtime':'umu-steamrt4'}
        for key in ['mangohud','gamemode','sdl_enabled','addapp_enabled','addapp','addapp_bat',
                    'cover','no_sleep','icon','steamgriddb_id','pre_launch','post_launch',
                    'steam_user','disable_umu','discord_rpc']:
            record[key]=''
        record.update(addapp_delay='0',addapp_first=False,lossless_enabled=False,
                      lossless_multiplier=1,lossless_flow=100.0,lossless_performance=False,
                      lossless_hdr=False,lossless_present='fifo',category=False)
        games.append(record)
    record.update(path=str(exe),prefix=str(PREFIX),runner='GE-Proton11-11-x86_64')
    if p.exists():
        if p.read_bytes()!=original: raise RuntimeError('Faugus изменил список игр. Закройте его и повторите.')
        shutil.copy2(p,STATE/('games-before-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'))
    with tempfile.NamedTemporaryFile('w',dir=p.parent,delete=False) as f:
        json.dump(games,f,ensure_ascii=False,indent=2); f.write('\n'); temp=Path(f.name)
    temp.replace(p)
    (STATE/'launcher.json').write_text(json.dumps({'exe':str(exe)},ensure_ascii=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer',type=Path,help='Путь к официальному установщику Radmir CRMP')
    parser.add_argument('--exe',type=Path,help='Явный путь к установленному лаунчеру')
    args=parser.parse_args()
    if os.getuid()==0: raise RuntimeError('Запускайте без sudo')
    if not (RUNNER/'proton').is_file() or not (DATA/'umu-run').is_file(): raise RuntimeError('Не найден GE-Proton11-11 или UMU Faugus')
    STATE.mkdir(parents=True,exist_ok=True); STATE.chmod(0o700)
    PREFIX.mkdir(parents=True,exist_ok=True)
    with (STATE/'run.lock').open('w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Radmir уже запущен этим скриптом')
        exe=args.exe.expanduser().resolve() if args.exe else None
        saved=STATE/'launcher.json'
        if exe is None and saved.exists():
            candidate=Path(json.loads(saved.read_text())['exe'])
            if candidate.is_file(): exe=candidate
        logs=STATE/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        if exe is None:
            found=candidates()
            if len(found)==1: exe=found[0]
            elif len(found)>1:
                raise RuntimeError('Несколько EXE; передайте --exe с нужным путём:\n'+'\n'.join(map(str,found)))
        if exe is None:
            installer=args.installer.expanduser().resolve() if args.installer else None
            if installer is None:
                found=[p for p in (HOME/'Загрузки').iterdir() if p.is_file() and p.suffix.lower()=='.exe' and any(x in p.name.lower() for x in ['radmir','rdmr'])]
                if len(found)==1: installer=found[0]
                elif len(found)>1: raise RuntimeError('Несколько установщиков. Укажите --installer и путь к нужному.')
            if installer is None or not installer.is_file():
                raise RuntimeError('Скачайте официальный Windows-лаунчер Radmir CRMP с https://radmir.online/ в папку Загрузки и повторите эту команду. Установщик должен иметь radmir или rdmr в имени; иначе используйте --installer ПУТЬ.')
            logs.mkdir(mode=0o700)
            (logs/'test.json').write_text(json.dumps({'runner':str(RUNNER),'wow64':False,'prefix':str(PREFIX)},ensure_ascii=False)+'\n')
            print('Установите лаунчер в стандартную папку диска C:. После установки закройте его окно, чтобы скрипт продолжил.',flush=True)
            code=run(installer,logs,'installer')
            if code: raise RuntimeError(f'Установщик завершился с кодом {code}. Лог: {logs}/installer.log')
            found=candidates()
            if len(found)!=1: raise RuntimeError('Не удалось однозначно выбрать EXE лаунчера. Напишите, что установка завершена; я проверю созданные файлы. Логи: '+str(logs))
            exe=found[0]
        if not exe.is_file(): raise RuntimeError('EXE не найден: '+str(exe))
        exe.resolve().relative_to(PREFIX.resolve())
        logs.mkdir(mode=0o700,exist_ok=True)
        register(exe)
        print('Запись Radmir CRMP сохранена в Faugus. Запускаю лаунчер.',flush=True)
        code=run(exe,logs,'launcher')
        print('Запуск завершён, код '+str(code)+'. Логи: '+str(logs),flush=True)
        return code


if __name__=='__main__':
    os.umask(0o077)
    try: sys.exit(main())
    except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as exc:
        raise SystemExit('ОСТАНОВЛЕНО: '+str(exc))
    except KeyboardInterrupt: sys.exit(130)

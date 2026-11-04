#!/usr/bin/env python3
"""Temporarily make a real Full HD output primary for Xwayland, then run Radmir."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from setup import PREFIX,STATE,run
from display import close_prefix


def query():
    p=subprocess.run(['xrandr','--current'],capture_output=True,text=True,timeout=8)
    if p.returncode: raise RuntimeError(p.stderr.strip() or 'Xwayland недоступен')
    return p.stdout


def outputs(text):
    result={}
    for line in text.splitlines():
        match=re.match(r'^(\S+) connected (primary )?(\d+)x(\d+)[+-]',line)
        if match:
            result[match[1]]={'primary':bool(match[2]),'size':(int(match[3]),int(match[4]))}
    return result


def choose(data):
    for name in ['HDMI-A-3','DP-5']:
        if name in data and data[name]['size']==(1920,1080): return name
    return next((name for name,value in data.items() if value['size']==(1920,1080)),None)


def main():
    before=query(); data=outputs(before)
    selected=choose(data)
    if selected is None:
        print('Нет отдельного экрана Full HD; использую текущие экраны без изменений.',flush=True)
        close_prefix()
        logs=STATE/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-current-display')
        logs.mkdir(mode=0o700)
        return run(PREFIX/'drive_c/Program Files (x86)/RADMIR Games/Launcher/RADMIR Launcher.exe',logs,'launcher')
    previous=next((name for name,value in data.items() if value['primary']),None)
    launcher=PREFIX/'drive_c/Program Files (x86)/RADMIR Games/Launcher/RADMIR Launcher.exe'
    if not launcher.is_file(): raise RuntimeError('Не найден лаунчер Radmir')
    print('Закрываю только текущий сеанс Radmir, чтобы игра заново получила список экранов.',flush=True)
    close_prefix()
    with (STATE/'run.lock').open('w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Предыдущая команда ещё завершается. Повторите через несколько секунд.')
        logs=STATE/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-real-fullhd')
        logs.mkdir(mode=0o700)
        (logs/'xrandr-before.txt').write_text(before)
        try:
            subprocess.run(['xrandr','--output',selected,'--primary'],check=True,capture_output=True,text=True,timeout=8)
            after=query(); after_outputs=outputs(after)
            (logs/'xrandr-after.txt').write_text(after)
            if selected not in after_outputs or not after_outputs[selected]['primary']:
                raise RuntimeError('Xwayland не подтвердил выбор основного экрана; запуск остановлен.')
            if {k:v['size'] for k,v in data.items()}!={k:v['size'] for k,v in after_outputs.items()}:
                raise RuntimeError('Изменился список экранов; запуск остановлен.')
            print('Основной экран Xwayland на время теста: '+selected+' (1920x1080).',flush=True)
            print('Масштаб, разрешения и расположение экранов не менялись.',flush=True)
            print('В лаунчере нажмите Играть и проверьте 1920x1080x32 в списке.',flush=True)
            return run(launcher,logs,'launcher')
        finally:
            try:
                current=outputs(query())
                if current.get(selected,{}).get('primary'):
                    cmd=['xrandr','--output',previous,'--primary'] if previous in current else ['xrandr','--noprimary']
                    subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=8)
                    print('Прежний выбор основного экрана Xwayland восстановлен.',flush=True)
            except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
                print('Не удалось восстановить основной экран Xwayland: '+str(exc),file=sys.stderr)


if __name__=='__main__':
    os.umask(0o077)
    try: sys.exit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        raise SystemExit('ОСТАНОВЛЕНО: '+str(exc))
    except KeyboardInterrupt: sys.exit(130)

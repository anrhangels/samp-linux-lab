#!/usr/bin/env python3
"""Temporarily enable a URL encoding proxy in the Radmir prefix only."""
import datetime,json,os,re,subprocess,sys,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from setup import PREFIX,STATE,command
from display import close_prefix
from audio_proxy import SessionHandler
import play_fullhd
import signal
def interrupted(signum,frame):raise KeyboardInterrupt
for sig in [signal.SIGTERM,signal.SIGHUP]:signal.signal(sig,interrupted)

KEY=r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
NAMES=['ProxyEnable','ProxyServer','ProxyOverride']
MARKER=STATE/'audio-proxy-restore.json'

def snapshot():
    active=False;values={}
    section='['+KEY.replace('\\','\\\\')+']'
    for line in (PREFIX/'user.reg').read_text().splitlines():
        if line.startswith('['):active=line.split(']',1)[0]+']'==section
        if active:
            m=re.match(r'"([^"]+)"=(.*)$',line)
            if m and m[1] in NAMES:values[m[1]]=m[2]
    return values

def registry(values,logs,label):
    path=logs/(label+'.reg')
    lines=['Windows Registry Editor Version 5.00','','[HKEY_CURRENT_USER\\'+KEY+']']
    lines += ['"'+name+'"='+values.get(name,'-') for name in NAMES]
    path.write_text('\n'.join(lines)+'\n',encoding='utf-16')
    exe=PREFIX/'drive_c/windows/system32/reg.exe'
    args=command(exe,logs)+['import','Z:'+str(path).replace('/','\\')]
    args=['MANGOHUD=0' if a=='MANGOHUD=1' else a for a in args]
    with (logs/(label+'.log')).open('w') as out:
        result=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,timeout=90)
    if result.returncode:raise RuntimeError('Не удалось применить '+label+'; журнал '+str(logs))

def main():
    logs=STATE/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-audio-session');logs.mkdir(mode=0o700)
    close_prefix()
    if MARKER.exists():
        registry(json.loads(MARKER.read_text()),logs,'restore-interrupted')
        MARKER.unlink()
    if '--restore' in sys.argv:
        print('Прежние настройки прокси восстановлены.');return 0
    server=ThreadingHTTPServer(('127.0.0.1',0),SessionHandler);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    old=snapshot();MARKER.write_text(json.dumps(old)+'\n')
    try:
        port=server.server_address[1]
        registry({'ProxyEnable':'dword:00000001','ProxyServer':f'"http=127.0.0.1:{port};https=127.0.0.1:{port}"','ProxyOverride':'"<local>"'},logs,'enable-proxy')
        print('Запускаю Radmir с исправлением адресов музыки.',flush=True)
        return play_fullhd.main()
    finally:
        try:
            registry(old,logs,'restore-proxy');MARKER.unlink(missing_ok=True)
            print('Прежние сетевые настройки префикса Radmir восстановлены.',flush=True)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':
    os.umask(0o077)
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:sys.exit('ОСТАНОВЛЕНО: '+str(exc))

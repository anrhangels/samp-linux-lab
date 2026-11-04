"""Installation coordinator bundled in install-radmir.py."""
import argparse,base64,datetime,hashlib,json,os,re,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit,unquote
import setup
HOME=Path.home();ROOT=Path(__file__).resolve().parent
APP='io.github.Faugus.faugus-launcher'
LAUNCHER=setup.PREFIX/'drive_c/Program Files (x86)/RADMIR Games/Launcher/RADMIR Launcher.exe'
VERBS=['ucrtbase2019','d3dx9_43','d3dcompiler_43','d3dcompiler_47']

def call(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def fetch(url,destination,expected=None):
    if urlsplit(url).scheme!='https':raise RuntimeError('Для загрузки требуется HTTPS')
    print('Скачивание: '+url,flush=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.name+'.part');digest=hashlib.sha512()
    try:
        with urlopen(Request(url,headers={'User-Agent':'Radmir-Linux-Installer/1.0'}),timeout=45) as src,temporary.open('wb') as dst:
            if urlsplit(src.url).scheme!='https':raise RuntimeError('Небезопасное перенаправление')
            while chunk:=src.read(1024*1024):dst.write(chunk);digest.update(chunk)
        if expected and digest.digest()!=expected:raise RuntimeError('Не совпала SHA-512: '+destination.name)
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    return destination

def json_url(url):
    with urlopen(Request(url,headers={'User-Agent':'Radmir-Linux-Installer/1.0'}),timeout=30) as r:return json.load(r)

def dependencies():
    for binary in ['flatpak','xrandr']:
        if not shutil.which(binary):raise RuntimeError('Сначала установите системный пакет '+('xorg-xrandr' if binary=='xrandr' else binary))
    installed=subprocess.run(['flatpak','info',APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not installed:
        call(['flatpak','remote-add','--user','--if-not-exists','flathub','https://dl.flathub.org/repo/flathub.flatpakrepo'])
        call(['flatpak','install','--user','-y','flathub',APP])
    setup.DATA.mkdir(parents=True,exist_ok=True)
    if not (setup.DATA/'umu-run').is_file():
        fetch('https://github.com/Faugus/umu-launcher/releases/download/1.4.4-patch/umu-run',setup.DATA/'umu-run')
        (setup.DATA/'umu-run').chmod(0o755)
    if not (setup.RUNNER/'proton').is_file():
        release=json_url('https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/tags/GE-Proton11-11')
        assets=release['assets']
        archives=[a for a in assets if a['name'].endswith(('.tar.gz','.tar.xz')) and 'GE-Proton' in a['name']]
        archives.sort(key=lambda a:'x86_64' not in a['name'])
        if not archives:raise RuntimeError('В выпуске GE-Proton11-11 не найден архив')
        asset=archives[0]
        checks=next((a for a in assets if a['name']==asset['name']+'.sha512sum' or a['name']==asset['name'].removesuffix('.tar.gz').removesuffix('.tar.xz')+'.sha512sum'),None)
        if not checks:raise RuntimeError('Не найдена контрольная сумма GE-Proton11-11')
        with tempfile.TemporaryDirectory(prefix='radmir-proton-') as tmp:
            tmp=Path(tmp);check=fetch(checks['browser_download_url'],tmp/'checksum')
            expected=bytes.fromhex(check.read_text().split()[0])
            archive=fetch(asset['browser_download_url'],tmp/asset['name'],expected)
            with tarfile.open(archive) as tf:tf.extractall(tmp/'unpacked',filter='data')
            candidates=list((tmp/'unpacked').glob('*/proton'))
            if len(candidates)!=1:raise RuntimeError('Неожиданная структура архива Proton')
            setup.RUNNER.parent.mkdir(parents=True,exist_ok=True)
            if setup.RUNNER.exists():raise RuntimeError('Каталог Proton существует, но повреждён: '+str(setup.RUNNER))
            shutil.move(str(candidates[0].parent),str(setup.RUNNER))

def installer(logs):
    # This feed is shipped in the official launcher's resources/app-update.yml.
    # sha512 and version are published by the same official update service.
    failures=[]
    for base in ['https://dl.hasslecdn.com/launcher/hassle/','https://dl-ru.hasslecdn.com/launcher/hassle/']:
        try:
            metadata=fetch(base+'latest.yml',logs/'latest.yml').read_text()
            path=re.search(r'^path:\s*[\'"]?([^\r\n\'"]+)',metadata,re.M)
            digest=re.search(r'^sha512:\s*[\'"]?([A-Za-z0-9+/=]+)',metadata,re.M)
            if not path or not digest:raise RuntimeError('В latest.yml отсутствуют path/sha512')
            url=urljoin(base,path[1].strip())
            if urlsplit(url).hostname!=urlsplit(base).hostname:raise RuntimeError('Неожиданный домен установщика')
            dest=fetch(url,logs/'RADMIRLauncherSetup.exe',base64.b64decode(digest[1],validate=True))
            if dest.open('rb').read(2)!=b'MZ':raise RuntimeError('Вместо EXE получен другой файл')
            return dest
        except Exception as exc:failures.append(str(exc))
    raise RuntimeError('Не удалось скачать официальный установщик: '+'; '.join(failures))

def native_ready():
    for directory in ['system32','syswow64']:
        for name in ['ucrtbase','d3dx9_43','d3dcompiler_43','d3dcompiler_47']:
            path=setup.PREFIX/'drive_c/windows'/directory/(name+'.dll')
            if not path.is_file() or b'Wine builtin DLL' in path.read_bytes()[:256]:return False
    return True

def run_logged(args,path):
    args=['MANGOHUD=0' if a=='MANGOHUD=1' else a for a in args]
    print('Журнал: '+str(path),flush=True)
    with path.open('w') as out:call(args,stdout=out,stderr=subprocess.STDOUT)

def hud():
    runtime=call(['flatpak','info','--show-runtime',APP],capture_output=True,text=True).stdout.strip()
    location=Path(call(['flatpak','info','--show-location',runtime],capture_output=True,text=True).stdout.strip())
    metadata=(location/'metadata').read_text()
    section=re.search(r'\[Extension org\.freedesktop\.Platform\.VulkanLayer\]\n([^\[]*)',metadata)
    version=re.search(r'^version\s*=\s*(\S+)',section[1],re.M) if section else None
    if not version:raise RuntimeError('Не определена ветка MangoHud')
    ref='org.freedesktop.Platform.VulkanLayer.MangoHud//'+version[1]
    info=subprocess.run(['flatpak','info','--show-location',ref],capture_output=True,text=True)
    if info.returncode:
        call(['flatpak','install','--user','-y','flathub',ref])
        info=call(['flatpak','info','--show-location',ref],capture_output=True,text=True)
    source=Path(info.stdout.strip())/'files'
    target=HOME/'.local/share/samp-linux-lab/radmir-crmp'
    for arch,abi in [('x86','i386-linux-gnu'),('x86_64','x86_64-linux-gnu')]:
        library=source/'lib'/abi/'libMangoHud.so';dest=target/'lib'/abi/library.name
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(library,dest)
        manifest=json.loads((source/'share/vulkan/implicit_layer.d'/('MangoHud.'+arch+'.json')).read_text())
        manifest['layer']['library_path']=str(dest)
        (target/'layers').mkdir(exist_ok=True)
        (target/'layers'/('MangoHud.'+arch+'.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    for name in ['MangoHud.conf','presets.conf']:
        dest=target/name
        if not dest.exists():shutil.copy2(ROOT/name,dest)

def install():
    if os.getuid()==0:raise RuntimeError('Запускайте скрипт от обычного пользователя, без sudo')
    dependencies();setup.STATE.mkdir(parents=True,exist_ok=True);setup.PREFIX.mkdir(parents=True,exist_ok=True)
    logs=setup.STATE/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-install');logs.mkdir(mode=0o700)
    need_launcher=not LAUNCHER.is_file()
    downloaded=installer(logs) if need_launcher else None
    if not native_ready() or need_launcher:
        from display import close_prefix
        close_prefix()
        import fcntl
        with (setup.STATE/'run.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            backup=logs/'backup';backup.mkdir()
            for name in ['user.reg','system.reg','userdef.reg','winetricks.log']:
                if (setup.PREFIX/name).is_file():shutil.copy2(setup.PREFIX/name,backup/name)
            if not native_ready():
                for directory in ['system32','syswow64']:
                    for name in ['ucrtbase','d3dx9_43','d3dcompiler_43','d3dcompiler_47']:
                        rel=Path('drive_c/windows')/directory/(name+'.dll')
                        if (setup.PREFIX/rel).is_file():
                            (backup/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(setup.PREFIX/rel,backup/rel)
                dummy=ROOT/'init.exe'
                run_logged(setup.command(dummy,logs)[:-1]+['winetricks','--force']+VERBS,logs/'libraries.log')
                if not native_ready():raise RuntimeError('Не все библиотеки установлены; журнал '+str(logs))
            if downloaded:
                run_logged(setup.command(downloaded,logs)+['/S'],logs/'launcher-install.log')
                if not LAUNCHER.is_file():raise RuntimeError('Установщик не создал лаунчер в стандартной папке; журнал '+str(logs))
    setup.register(LAUNCHER)
    hud()
    bins=HOME/'.local/bin';bins.mkdir(parents=True,exist_ok=True)
    command=bins/'radmir'
    # shlex.quote supports home paths containing spaces and apostrophes.
    import shlex
    text='#!/bin/sh\nexec python3 '+shlex.quote(str(ROOT/'play_audio.py'))+' "$@"\n'
    if command.exists() and command.read_text()!=text:shutil.copy2(command,logs/'previous-radmir')
    command.write_text(text);command.chmod(0o755)
    print('\nГотово! Чтобы запустить Radmir, введите команду:\n\n  radmir\n')
    print('При первом запуске выберите RADMIR CRMP: файлы игры скачает официальный лаунчер.')
    if str(bins) not in os.environ.get('PATH','').split(':'):print('В этом терминале используйте: ~/.local/bin/radmir (добавьте ~/.local/bin в PATH).')

if __name__=='__main__':
    try:install()
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:sys.exit('ОСТАНОВЛЕНО: '+str(exc))

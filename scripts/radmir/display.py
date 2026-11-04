#!/usr/bin/env python3
"""Set a 1920x1080 Wine desktop only in the Radmir prefix and relaunch."""
import datetime
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from setup import PREFIX,STATE,command,register,run


def matches(pid):
    p=Path('/proc')/str(pid)
    if p.stat().st_uid!=os.getuid(): return None
    env=(p/'environ').read_bytes().split(b'\0')
    value=next((x.split(b'=',1)[1] for x in env if x.startswith(b'WINEPREFIX=')),None)
    if not value or Path(os.fsdecode(value)).resolve()!=PREFIX.resolve(): return None
    return (p/'stat').read_text().rsplit(')',1)[1].split()[19]


def processes():
    result={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid(): continue
        try:
            value=matches(int(p.name))
            if value: result[int(p.name)]=value
        except (OSError,ValueError,IndexError): pass
    return result


def close_prefix():
    for pid,start in processes().items():
        fd=None
        try:
            fd=os.pidfd_open(pid)
            if matches(pid)==start: signal.pidfd_send_signal(fd,signal.SIGTERM)
        except OSError: pass
        finally:
            if fd is not None: os.close(fd)
    for _ in range(40):
        if not processes(): time.sleep(1); return
        time.sleep(.25)
    raise RuntimeError('Radmir ещё работает. Закройте его окна и повторите команду.')


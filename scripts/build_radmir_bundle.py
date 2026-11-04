#!/usr/bin/env python3
"""Regenerate the standalone installer after editing scripts/radmir sources."""
import base64
import hashlib
import json
from pathlib import Path
import re
import zlib

ROOT=Path(__file__).resolve().parent
NAMES=['setup.py','play_fullhd.py','play_audio.py','audio_proxy.py','display.py','install.py','MangoHud.conf','presets.conf']
files={name:(ROOT/'radmir'/name).read_text() for name in NAMES}
for name,text in files.items():
    if name.endswith('.py'):compile(text,name,'exec')
payload=base64.b85encode(zlib.compress(json.dumps(files,ensure_ascii=False).encode(),9)).decode()
digest=hashlib.sha256(payload.encode()).hexdigest()
target=ROOT/'install-radmir.py'
source=target.read_text()
source,n=re.subn(r'^PAYLOAD=.*$',lambda m:'PAYLOAD='+repr(payload),source,count=1,flags=re.M)
assert n==1
source,n=re.subn(r'^DIGEST=.*$',lambda m:'DIGEST='+repr(digest),source,count=1,flags=re.M)
assert n==1
target.write_text(source)
print(target)

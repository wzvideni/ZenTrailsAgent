import os
import sys
import time
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge

print(subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process 'Zen Trails' -ErrorAction SilentlyContinue | Measure-Object).Count"],
    capture_output=True, text=True).stdout.strip(), "= processes")

b = Bridge()
print(b.cmd("find", "Segment")[1])
print(b.cmd("get", "type:ClickAndDrag", "segments")[1][:200])
print(b.cmd("shot", "created")[1].strip())
b.close()

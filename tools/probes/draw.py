"""Draw by real mouse drag, with focus handled properly, then verify game state."""
import os
import sys
import time
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge

def alive():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process 'Zen Trails' -ErrorAction SilentlyContinue | Measure-Object).Count"],
                         capture_output=True, text=True)
    return out.stdout.strip() not in ("0", "")

b = Bridge()
print("state:", b.cmd("get", "type:GameManager", "gameState")[1].strip())
print("focus(alt):", b.cmd("key", "18")[1].strip(), b.cmd("focus")[1].strip())
time.sleep(0.4)
print("segments before:", b.cmd("find", "Segment")[1].splitlines()[0])
print(b.cmd("drag", "820", "500", "1120", "760", "24")[1].strip())
time.sleep(2.0)
print("alive:", alive())
st, out = b.cmd("find", "Segment")
print("segments after:", out.splitlines()[0])
print("\n".join(out.splitlines()[1:6]))
b.close()

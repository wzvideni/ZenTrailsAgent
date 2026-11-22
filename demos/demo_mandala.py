"""AI-generated mandala: chains child segments with the golden angle, all via the game's own API."""
import colorsys
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from client import Bridge

b = Bridge()
print(b.cmd("call", "type:GameManager", "BeginMainGame")[1].strip())
time.sleep(4.5)
print(b.cmd("get", "type:GameManager", "gameState")[1].strip())

N = 36
ids = []
parent = "null"
last_out = ""
for i in range(N):
    length = 3.0 - 0.06 * i
    angle = 137.5077 if i else 0.0            # golden angle rotation
    r, g, bl = colorsys.hsv_to_rgb((i * 0.031) % 1.0, 0.55, 1.0)
    color = f"{r:.3f},{g:.3f},{bl:.3f},1"
    seg_id = 9000 + i
    args = [1 if i else 0, seg_id, parent, f"{length:.3f}", "1", f"{angle:.3f}",
            "1", "0.45", color, "0,0,0", "0", "1", "0", "null", "1", "0"]
    st, out = b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)
    last_out = f"{st} {out.strip()}"
    if st != "OK":
        print("failed at", i, out)
        break
    parent = str(seg_id)
    ids.append(seg_id)
    time.sleep(0.08)

print("created", len(ids), "segments; last:", last_out)
time.sleep(1.5)
print(b.cmd("shot", "mandala")[1].strip())
b.close()

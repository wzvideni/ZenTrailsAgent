"""Demo: drive Zen Trails entirely from outside the game (no mouse/keyboard)."""
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge

b = Bridge()

print(b.cmd("call", "type:GameManager", "BeginMainGame"))
time.sleep(4)

print("state:", b.cmd("get", "type:GameManager", "gameState"))

# (isChild, ID, parentID, length, speed, angle, drawTrail, trailWidth,
#  color(r,g,b,a), pos(x,y,z), layerOrder, glow, isGradient, gradient, centerCam, openInfoP)
made = []
for i in range(12):
    args = [0, 100 + i, "null", 2.0 + 0.15 * i, 1, 360.0 * i / 12.0,
            1, 0.4, "1,0.75,0.35,1", "0,0,0", 0, 1, 0, "null", 0, 0]
    st, out = b.cmd("call", "type:ClickAndDragMaster", "CreateNewSegment", *args)
    made.append((st, out.strip()))
    time.sleep(0.15)

print("created:", made[-1])
print("segments:", b.cmd("find", "Segment")[1].splitlines()[0])

time.sleep(1.0)
print(b.cmd("shot", "agent_draw"))
time.sleep(1.0)
b.close()

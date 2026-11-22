"""Step-by-step probe with liveness checks to find which command kills the game."""
import subprocess, time
from client import Bridge

def alive():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process 'Zen Trails' -ErrorAction SilentlyContinue | Measure-Object).Count"],
        capture_output=True, text=True)
    return out.stdout.strip() not in ("0", "")

steps = [
    ("ping", ()),
    ("get", ("type:GameManager", "gameState")),
    ("get", ("type:ClickAndDrag", "mousePoint")),
    ("mouse", ("900", "500", "move")),
    ("get", ("type:ClickAndDrag", "mousePoint")),
    ("focus", ()),
    ("shot", ("probe1",)),
]

for name, args in steps:
    b = Bridge()
    try:
        st, out = b.cmd(name, *args)
        print(f"{name:8s} {st:3s} {out.strip()[:120]!r}")
    except Exception as e:
        print(f"{name:8s} CLIENT-ERROR {type(e).__name__}")
    finally:
        b.close()
    time.sleep(0.6)
    ok = alive()
    print(f"         game alive: {ok}")
    if not ok:
        print("=> died after", name, args)
        break

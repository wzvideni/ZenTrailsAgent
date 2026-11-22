import time, subprocess
from client import Bridge

print(subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process 'Zen Trails' -ErrorAction SilentlyContinue | Measure-Object).Count"],
    capture_output=True, text=True).stdout.strip(), "= processes")

b = Bridge()
print(b.cmd("find", "Segment")[1])
print(b.cmd("get", "type:ClickAndDrag", "segments")[1][:200])
print(b.cmd("shot", "created")[1].strip())
b.close()

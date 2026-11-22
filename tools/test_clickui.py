"""Test zen_clickui end-to-end: main menu -> click Tutorial -> scene becomes Tutorial."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mcp_server


def show(name, args):
    r = mcp_server.handle_call(name, args)
    if isinstance(r, dict) and "content" in r:
        for c in r["content"]:
            if c["type"] == "text":
                print(f"[{name}] {c['text'].replace(chr(10), ' | ')[:200]}")
            else:
                print(f"[{name}] <{c['type']}>")
    else:
        print(f"[{name}] {r}")


print("=== go to main menu ===")
show("zen_call", {"selector": "type:GameManager", "method": "GoToMainMenu"})
time.sleep(3)

print("\n=== scene (should be MainMenu) ===")
show("zen_cmd", {"command": "scene", "args": ["0"]})

print("\n=== clickui TutorialButton ===")
show("zen_clickui", {"path": "Canvas/MainMenu/TutorialButton"})
time.sleep(3.5)

print("\n=== scene (should be Tutorial) ===")
show("zen_cmd", {"command": "scene", "args": ["0"]})

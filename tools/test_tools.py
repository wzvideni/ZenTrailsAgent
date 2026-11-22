"""Comprehensive test of every MCP tool against the live game."""
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
import mcp_server


def show(name, args):
    try:
        r = mcp_server.handle_call(name, args)
    except Exception as e:
        print(f"[{name}] EXC {type(e).__name__}: {e}")
        return
    if isinstance(r, dict) and "content" in r:
        for c in r["content"]:
            if c["type"] == "text":
                txt = c["text"].replace("\n", " | ")[:240]
                print(f"[{name}] {txt}")
            elif c["type"] == "image":
                print(f"[{name}] <image {len(c['data'])} base64 chars>")
            else:
                print(f"[{name}] <{c['type']}>")
    else:
        print(f"[{name}] {r}")


print("=== 1. zen_cmd ping ===")
show("zen_cmd", {"command": "ping"})

print("\n=== 2. zen_types filter ===")
show("zen_types", {"filter": "Manager"})

print("\n=== 3. zen_describe ===")
show("zen_describe", {"type": "GameManager"})

print("\n=== 4. zen_scene (depth 1) ===")
show("zen_scene", {"depth": 1})

print("\n=== 5. zen_find Segment ===")
show("zen_find", {"type": "Segment"})

print("\n=== 6. zen_get static state ===")
show("zen_get", {"selector": "type:GameManager", "members": "gameState"})

# grab a live Segment instance id
r = mcp_server.handle_call("zen_find", {"type": "Segment"})
seg_id = None
for c in r["content"]:
    if c["type"] == "text":
        for line in c["text"].splitlines():
            if line.startswith("obj "):
                seg_id = line.split()[1]
                break
if seg_id:
    print(f"\n=== 7. zen_get on obj:{seg_id} ===")
    show("zen_get", {"selector": f"obj:{seg_id}", "members": "length"})

    print(f"\n=== 8. zen_set length -> 5.5 ===")
    show("zen_set", {"selector": f"obj:{seg_id}", "member": "length", "value": "5.5"})

    print(f"\n=== 9. zen_get verify ===")
    show("zen_get", {"selector": f"obj:{seg_id}", "members": "length"})

    print(f"\n=== 10. zen_call UpdateLength (reads length into renderer) ===")
    show("zen_call", {"selector": f"obj:{seg_id}", "method": "UpdateLength"})

print("\n=== 11. zen_screenshot (inline image) ===")
show("zen_screenshot", {"name": "tooltest", "return_image": True})

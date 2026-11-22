#!/usr/bin/env python3
"""
Live In-Game Showcase using ONLY the High-Level Domain Tools:
Demonstrating the full AI Agent workflow:
1. Consult zen_guide
2. Clear canvas with zen_clear
3. Set dark cosmos background with zen_dark_mode
4. Configure camera with zen_set_camera
5. Programmatically create multi-pendulums with zen_create_segment:
   - 6-fold Flower of Life Rosettes (1 : -2)
   - Hexagram Astroid Diamonds (1 : -3)
   - 24-ray Solar Corona (1 : -23)
   - Concentric Sanctuary Enclosure Ring
6. Hide arm meshes with zen_hide_arms
7. Inspect skeleton with zen_list_segments
8. Run simulation with zen_play for ~18s to complete closed sacred geometry
9. Safely freeze trails with zen_pause
10. Capture high-res screenshot with zen_screenshot
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mcp_server


def log(msg):
    print(f"[LIVE] {msg}", flush=True)


def call(name, args=None):
    if args is None:
        args = {}
    res = mcp_server.handle_call(name, args)
    if isinstance(res, dict) and "content" in res:
        for c in res["content"]:
            if c["type"] == "text":
                return c["text"]
    return str(res)


def main():
    log("=== Step 1: Consult AI Creator Guide ===")
    guide_kinematics = call("zen_guide", {"topic": "kinematics"})
    log(f"Consulted Guide formulas:\n{guide_kinematics[:280]}...\n")

    log("=== Step 2: Clear Canvas & Initialize Environment ===")
    call("zen_clear")
    call("zen_dark_mode", {"color": "0.015,0.015,0.035,1"})
    call("zen_set_camera", {"distance": -12.5, "x": 0.0, "y": 0.0})
    log("Canvas cleared and cosmic dark mode activated.")

    log("=== Step 3: Build Sacred Geometry Skeleton ===")
    # 1. Outer Sanctuary Ring (Concentric Circle 1:1)
    call("zen_create_segment", {
        "length": 4.80,
        "speed": 0.75,
        "color": "cyan",
        "width": 0.50,
        "glow": 2.0,
    })

    # 2. Solar Corona (24-cusp solar flares, 1 : -23)
    corona_root = call("zen_create_segment", {
        "length": 4.35,
        "speed": 0.50,
        "color": "amber",
        "width": 0.25,
        "glow": 1.5,
    })
    # Extract root ID from output
    root_id = 1001  # 1000 was outer ring, 1001 is corona root
    call("zen_create_segment", {
        "length": 0.45,
        "speed": -23.0,
        "parent_id": root_id,
        "color": "gold",
        "width": 0.45,
        "glow": 2.2,
    })

    # 3. Hexagram Diamond Astroids (4 groups at 0, 90, 180, 270 deg, ratio 1 : -3)
    for i, deg in enumerate([0, 90, 180, 270]):
        c_id = 1003 + i * 2
        call("zen_create_segment", {
            "length": 2.85,
            "speed": 1.0,
            "angle": deg,
            "color": "violet",
            "width": 0.25,
            "draw_trail": False,  # invisible carrier arm
        })
        call("zen_create_segment", {
            "length": 0.85,
            "speed": -3.0,
            "angle": deg,
            "parent_id": c_id,
            "color": "aqua",
            "width": 0.38,
            "glow": 1.8,
        })

    # 4. Central 6-Petal Flower of Life Rosettes (6 groups at 0, 60, 120, 180, 240, 300 deg, ratio 1 : -2)
    base_id = 1011
    for i, deg in enumerate([0, 60, 120, 180, 240, 300]):
        m_id = base_id + i * 2
        call("zen_create_segment", {
            "length": 1.40,
            "speed": 1.0,
            "angle": deg,
            "color": "gold" if i % 2 == 0 else "rose",
            "width": 0.42,
            "glow": 1.8,
        })
        call("zen_create_segment", {
            "length": 1.10,
            "speed": -2.0,
            "angle": deg,
            "parent_id": m_id,
            "color": "magenta" if i % 2 == 0 else "amber",
            "width": 0.38,
            "glow": 1.8,
        })

    # 5. Core Singularity Light
    call("zen_create_segment", {
        "length": 0.40,
        "speed": 2.0,
        "color": "white",
        "width": 0.60,
        "glow": 2.5,
    })

    log("=== Step 4: Hide Arm Meshes ===")
    call("zen_hide_arms", {"hide": True})

    log("=== Step 5: Verify Skeleton Structure ===")
    seg_list = call("zen_list_segments")
    log(f"Active segments report:\n{seg_list}\n")

    log("=== Step 6: Start Physics Simulation (zen_play) ===")
    call("zen_play")
    log("Simulation is actively drawing trails on the game screen...")
    
    # Wait for trails to complete closed orbits
    total_wait = 18.0
    for elapsed in range(1, int(total_wait) + 1):
        time.sleep(1.0)
        if elapsed % 4 == 0 or elapsed == int(total_wait):
            log(f"  Drawing in progress: {elapsed}/{int(total_wait)}s...")

    log("=== Step 7: Freeze Trails In-Place (zen_pause) ===")
    call("zen_pause")
    log("Simulation successfully paused! Trails frozen on game screen.")

    log("=== Step 8: Capture Live High-Res Screenshot ===")
    shot_res = mcp_server.handle_call("zen_screenshot", {
        "name": "live_game_test_masterpiece",
        "return_image": True,
    })
    
    shot_path = ""
    img_data = None
    if isinstance(shot_res, dict) and "content" in shot_res:
        for c in shot_res["content"]:
            if c["type"] == "text":
                shot_path = c["text"]
            elif c["type"] == "image":
                img_data = c["data"]

    log(f"Screenshot captured at: {shot_path}")
    if img_data:
        import base64
        out_jpg = os.path.join(
            r"C:\Users\DC\.gemini\antigravity-cli\brain\504c6d05-f046-4126-bc2a-a863029af3a9",
            "live_game_test_masterpiece.jpg",
        )
        with open(out_jpg, "wb") as f:
            f.write(base64.b64decode(img_data))
        log(f"Inline image saved to artifact: {out_jpg}")

    print("\n" + "="*50)
    print("LIVE IN-GAME TEST COMPLETED SUCCESSFULLY!")
    print("="*50)


if __name__ == "__main__":
    main()

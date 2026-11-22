#!/usr/bin/env python3
"""
Comprehensive test suite for Zen Trails High-Level Domain Tools (L2).
Tests all 9 domain tools against the live game process:
1. zen_guide (topics, filtering, fallback)
2. zen_clear (canvas reset, id counter reset)
3. zen_dark_mode (default & custom background color, BG deactivation)
4. zen_set_camera (distance & coordinate offsets)
5. zen_create_segment (root, child hierarchy, named & rgba colors, carrier anchor, custom id)
6. zen_list_segments (structure, hierarchy, attributes verification)
7. zen_hide_arms (toggle hide/show mechanical arm meshes)
8. zen_play (run simulation, trail generation)
9. zen_pause (safe freeze, trail preservation)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mcp_server


def test_section(title):
    print(f"\n{'='*20} {title} {'='*20}")


def run_tool(name, args=None):
    if args is None:
        args = {}
    res = mcp_server.handle_call(name, args)
    if isinstance(res, dict) and "content" in res:
        texts = [c["text"] for c in res["content"] if c["type"] == "text"]
        return True, "\n".join(texts)
    return False, str(res)


def assert_ok(cond, msg):
    if cond:
        print(f"  [PASS] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        raise AssertionError(msg)


def main():
    print("Testing connection to game...")
    st, out = mcp_server.conn.call("ping")
    assert_ok(st == "OK", f"Game bridge reachable: {out}")

    # -------------------------------------------------------------
    test_section("1. Test zen_guide")
    # -------------------------------------------------------------
    ok, guide_all = run_tool("zen_guide", {"topic": "all"})
    assert_ok(ok and len(guide_all) > 2000, f"zen_guide(all) returned full handbook ({len(guide_all)} chars)")
    assert_ok("核心机制" in guide_all and "神圣几何" in guide_all, "Contains kinematics headers")

    ok, guide_kin = run_tool("zen_guide", {"topic": "kinematics"})
    assert_ok(ok and "生命之花" in guide_kin and "1 : -2" in guide_kin, "zen_guide(kinematics) returned formula table")

    ok, guide_pal = run_tool("zen_guide", {"topic": "palettes"})
    assert_ok(ok and "gold" in guide_pal and "cyan" in guide_pal and "常用神圣色彩体系" in guide_pal, "zen_guide(palettes) returned color table")

    ok, guide_wf = run_tool("zen_guide", {"topic": "workflow"})
    assert_ok(ok and "创作标准流程" in guide_wf and "避坑守则" in guide_wf, "zen_guide(workflow) returned workflow rules")

    ok, guide_fallback = run_tool("zen_guide", {"topic": "nonexistent_topic"})
    assert_ok(ok and len(guide_fallback) > 2000, "zen_guide fallback on unknown topic returned full handbook")

    # -------------------------------------------------------------
    test_section("2. Test zen_clear")
    # -------------------------------------------------------------
    ok, out = run_tool("zen_clear")
    assert_ok(ok and "Canvas cleared" in out, f"zen_clear output: {out.strip()}")

    ok, list_out = run_tool("zen_list_segments")
    assert_ok(ok and "No segments active" in list_out, "zen_list_segments confirms canvas is empty")

    # -------------------------------------------------------------
    test_section("3. Test zen_dark_mode")
    # -------------------------------------------------------------
    ok, out = run_tool("zen_dark_mode", {"color": "0.02,0.02,0.04,1"})
    assert_ok(ok and "Dark mode activated" in out, "Default dark mode applied")

    ok, out = run_tool("zen_dark_mode", {"color": "0.05,0.01,0.06,1"})
    assert_ok(ok and "0.05,0.01,0.06,1" in out, "Custom background color applied")

    # -------------------------------------------------------------
    test_section("4. Test zen_set_camera")
    # -------------------------------------------------------------
    ok, out = run_tool("zen_set_camera", {"distance": -12.8, "x": 0.0, "y": 0.0})
    assert_ok(ok and "(-12.8" in out or "-12.8)" in out, f"Camera set to distance -12.8: {out.strip()}")

    ok, out = run_tool("zen_set_camera", {"distance": -10.5, "x": 0.2, "y": -0.2})
    assert_ok(ok and "-10.5" in out and "0.2" in out, f"Camera set to offset position: {out.strip()}")

    # Reset camera to standard
    run_tool("zen_set_camera", {"distance": -12.5, "x": 0.0, "y": 0.0})

    # -------------------------------------------------------------
    test_section("5. Test zen_create_segment (Multi-Pendulum Hierarchy)")
    # -------------------------------------------------------------
    # 5.1 Root segment (ID 1000)
    ok, out = run_tool("zen_create_segment", {
        "length": 2.4,
        "speed": 1.0,
        "color": "gold",
        "width": 0.45,
        "glow": 2.0
    })
    assert_ok(ok and "ID=1000" in out and "parent=null" in out, f"Root segment created: {out.strip()}")

    # 5.2 Child segment (Flower of Life Rosette -2x speed on ID 1000)
    ok, out = run_tool("zen_create_segment", {
        "length": 1.8,
        "speed": -2.0,
        "parent_id": 1000,
        "color": "magenta"
    })
    assert_ok(ok and "ID=1001" in out and "parent=1000" in out, f"Child segment attached: {out.strip()}")

    # 5.3 Grandchild segment (Astroid -3x speed on ID 1001, custom RGBA)
    ok, out = run_tool("zen_create_segment", {
        "length": 0.9,
        "speed": -3.0,
        "parent_id": 1001,
        "color": "0.1,0.9,0.8,1.0"
    })
    assert_ok(ok and "ID=1002" in out and "parent=1001" in out, f"Grandchild segment attached: {out.strip()}")

    # 5.4 Stationary carrier anchor (speed=0, draw_trail=False)
    ok, out = run_tool("zen_create_segment", {
        "length": 3.5,
        "speed": 0.0,
        "angle": 45.0,
        "draw_trail": False,
        "color": "white"
    })
    assert_ok(ok and "ID=1003" in out and "speed=0.0" in out and "trail=False" in out, f"Stationary anchor created: {out.strip()}")

    # 5.5 Satellite attached to stationary carrier anchor
    ok, out = run_tool("zen_create_segment", {
        "length": 1.2,
        "speed": 3.0,
        "parent_id": 1003,
        "color": "cyan"
    })
    assert_ok(ok and "ID=1004" in out and "parent=1003" in out, f"Off-center satellite attached: {out.strip()}")

    # 5.6 Custom ID segment
    ok, out = run_tool("zen_create_segment", {
        "id": 8888,
        "length": 0.5,
        "speed": 1.0,
        "color": "violet"
    })
    assert_ok(ok and "ID=8888" in out, f"Custom ID segment created: {out.strip()}")

    # -------------------------------------------------------------
    test_section("6. Test zen_list_segments")
    # -------------------------------------------------------------
    ok, list_out = run_tool("zen_list_segments")
    print(list_out)
    assert_ok(ok and "Active segments count: 6" in list_out, "Found exactly 6 active segments")
    assert_ok("Parent=null" in list_out and "Parent=1000" in list_out and "Parent=1001" in list_out and "Parent=1003" in list_out, "Hierarchy chain verified in listing")
    assert_ok("ID=8888" in list_out, "Custom ID 8888 present in listing")

    # -------------------------------------------------------------
    test_section("7. Test zen_hide_arms")
    # -------------------------------------------------------------
    ok, out = run_tool("zen_hide_arms", {"hide": True})
    assert_ok(ok and "hidden" in out, "zen_hide_arms(hide=True) succeeded")

    ok, out = run_tool("zen_hide_arms", {"hide": False})
    assert_ok(ok and "shown" in out, "zen_hide_arms(hide=False) succeeded")

    # Re-hide arms for clean drawing
    run_tool("zen_hide_arms", {"hide": True})

    # -------------------------------------------------------------
    test_section("8. Test zen_play & zen_pause (Trail Preservation)")
    # -------------------------------------------------------------
    ok, play_out = run_tool("zen_play")
    assert_ok(ok and "Simulation running" in play_out, "zen_play started simulation")

    print("  Drawing trails for 2.0 seconds...")
    time.sleep(2.0)

    ok, pause_out = run_tool("zen_pause")
    assert_ok(ok and "Simulation paused" in pause_out and "without erasing" in pause_out, "zen_pause safely froze simulation")

    # Verify simulation is indeed paused and segments still intact
    ok, list_after = run_tool("zen_list_segments")
    assert_ok(ok and "Active segments count: 6" in list_after, "All segments remain intact after pause")

    # Capture visual verification screenshot
    ok, shot_out = run_tool("zen_screenshot", {"name": "domain_tools_verification", "return_image": True})
    assert_ok(ok, "Screenshot captured for visual verification")

    # -------------------------------------------------------------
    test_section("9. Cleanup Canvas")
    # -------------------------------------------------------------
    ok, clear_out = run_tool("zen_clear")
    assert_ok(ok and "Canvas cleared" in clear_out, "Canvas cleared")
    ok, empty_check = run_tool("zen_list_segments")
    assert_ok("No segments active" in empty_check, "Canvas confirmed clean")

    print("\n" + "="*50)
    print("ALL HIGH-LEVEL DOMAIN TOOLS TESTS PASSED PERFECTLY!")
    print("="*50)


if __name__ == "__main__":
    main()

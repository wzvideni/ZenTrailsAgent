"""Backward-compatible shim: re-export Bridge from the package."""
import sys

from zentrails_agent.client import Bridge

__all__ = ["Bridge"]

if __name__ == "__main__":
    b = Bridge()
    if len(sys.argv) > 1:
        name, args = sys.argv[1], sys.argv[2:]
        st, out = b.cmd(name, *args)
        print(f"[{st}]")
        print(out)
    else:
        print(b.cmd("ping"))
    b.close()

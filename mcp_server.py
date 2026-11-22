#!/usr/bin/env python3
"""Backward-compatible shim: run the MCP server from the package."""
from zentrails_agent.server import main, handle_call, conn, TOOLS, rpc_result, rpc_error

__all__ = ["main", "handle_call", "conn", "TOOLS", "rpc_result", "rpc_error"]

if __name__ == "__main__":
    main()

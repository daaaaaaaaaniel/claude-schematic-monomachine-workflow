#!/usr/bin/env python3
"""Minimal MCP stdio client for Konnect (KiCad 10 IPC): call tools from scripts in this repo.

    python3 tools/konnect_call.py list [toolset]          # list tools (after loading a toolset, if given)
    python3 tools/konnect_call.py call <tool> '<json>'    # one call; prints the result
    python3 tools/konnect_call.py batch file.json         # [[tool, {args}], ...] in one session

KONNECT points at the server binary (default: konnect on PATH). KiCad's PCB editor must be running with its API
server enabled (Preferences > Plugins > Enable KiCad API; kicad_common.json api.enable_server).
"""
import json
import os
import subprocess
import sys

BIN = os.environ.get("KONNECT", "konnect")
TOOLSETS = ["project", "pcb_board", "pcb_components", "pcb_routing", "sch_export", "verification"]   # loaded per session


class Client:
    def __init__(self):
        self.p = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr, env={**os.environ, "RUST_LOG": os.environ.get("RUST_LOG", "warn")},
                                  text=True, bufsize=1)
        self.n = 0
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                "clientInfo": {"name": "machine-filter-scripts", "version": "0"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.call("load_toolset", {"name": TOOLSETS})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.n += 1
        self.send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise SystemExit("konnect exited")
            msg = json.loads(line)
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"]))
                return msg["result"]

    def call(self, tool, args=None):
        r = self.rpc("tools/call", {"name": tool, "arguments": args or {}})
        text = "\n".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")
        try:
            data = json.loads(text)
        except ValueError:
            data = text
        if r.get("isError"):
            raise RuntimeError(f"{tool}: {text[:2000]}")
        return data

    def tools(self):
        return self.rpc("tools/list", {})["tools"]

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


def main():
    c = Client()
    try:
        if sys.argv[1] == "list":
            if len(sys.argv) > 2:
                print(c.call("load_toolset", {"name": sys.argv[2]}))
            for t in c.tools():
                print(t["name"], "-", t.get("description", "")[:120])
        elif sys.argv[1] == "call":
            print(json.dumps(c.call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}), indent=1))
        elif sys.argv[1] == "batch":
            for tool, args in json.load(open(sys.argv[2])):
                print(f"== {tool}")
                print(json.dumps(c.call(tool, args), indent=1)[:4000])
    finally:
        c.close()


if __name__ == "__main__":
    main()

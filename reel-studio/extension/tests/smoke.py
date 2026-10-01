"""Smoke test: unpack the .mcpb like Claude does, start the server, call the tools.
    python extension/tests/smoke.py <workdir> DEV   (run inside the extension's uv environment)
"""
import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
T = sys.argv[1]
async def main():
    env = dict(os.environ, REEL_HOME=f"{T}/home", REEL_LICENSE_KEY=sys.argv[2], REEL_DEV="1", PYTHONUTF8="1")
    params = StdioServerParameters(command="uv", args=["--directory", f"{T}/ext", "run", "src/server.py"], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            print("server:", init.serverInfo.name, "| instructions:", (init.instructions or "")[:80])
            tools = await s.list_tools(); print("tools:", [t.name for t in tools.tools])
            for name, args in [("reel_licence", {}), ("reel_guide", {}), ("reel_command", {"command": "setup-check"}),
                               ("reel_command", {"command": "effects"}), ("reel_inbox", {}),
                               ("reel_read", {"path": "../secret.txt"}), ("reel_write", {"path": "engine/x.py", "content": "x"})]:
                res = await s.call_tool(name, args)
                txt = res.content[0].text if res.content else ""
                print(f"--- {name} {args.get('command','')}: {txt[:300]!r}")
                if name == "reel_licence": assert txt.startswith("✓"), txt
                if name == "reel_guide": assert "Reel Studio" in txt, txt[:200]
                if name == "reel_read": assert "Only files inside" in txt, txt
                if name == "reel_write": assert "Only files in projects" in txt, txt
asyncio.run(main())
print("extension smoke test passed")

"""Prueba manual del canal MCP contra un servidor OGD-live corriendo en local.

Uso (con el servidor ya arrancado en 127.0.0.1:8000):
    python scripts/test_mcp.py
"""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_TREE = REPO_ROOT / "third_party" / "OG_Delineation" / "data" / "P53.fa.nw"


async def main() -> None:
    client = Client("http://127.0.0.1:8000/mcp/")
    async with client:
        tools = await client.list_tools()
        print("TOOLS:", [t.name for t in tools])

        newick_content = EXAMPLE_TREE.read_text()
        run_result = await client.call_tool(
            "run_ogd_analysis",
            {"newick_content": newick_content, "tree_filename": "P53.fa.nw"},
        )
        print("RUN RESULT:", run_result.data)
        job_id = run_result.data["job_id"]

        for _ in range(30):
            status = await client.call_tool("get_job_status", {"job_id": job_id})
            print("STATUS:", status.data)
            if status.data["status"] in ("done", "error"):
                break
            await asyncio.sleep(1)
        else:
            print("TIMEOUT esperando a que termine el job", file=sys.stderr)
            sys.exit(1)

        results = await client.call_tool("get_results", {"job_id": job_id, "max_rows": 3})
        print("RESULTS num_ogs_returned:", results.data["num_ogs_returned"])
        print("RESULTS ogs_info[0]:", results.data["ogs_info"][0] if results.data["ogs_info"] else None)

        jobs = await client.call_tool("list_jobs", {})
        print("JOBS:", jobs.data)


if __name__ == "__main__":
    asyncio.run(main())

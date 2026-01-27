from mcp.server.fastmcp import FastMCP
from . import control_service

mcp = FastMCP("Chiller MCP", json_response=True)

@mcp.tool()
def get_thresholds(plant_id: str) -> dict:
    return control_service.get_thresholds_for_llm(plant_id)

@mcp.tool()
def get_snapshot(plant_id: str) -> dict:
    return control_service.get_snapshot_for_llm(plant_id)

# (optional) เก็บไว้ fallback ถ้ายังอยากใช้ rule-based
@mcp.tool()
def recommend_rule(plant_id: str) -> dict:
    return control_service.suggestion(plant_id)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", mount_path="/mcp")

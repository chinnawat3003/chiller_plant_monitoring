from mcp.server.fastmcp import FastMCP
from . import control_service

mcp = FastMCP("Chiller MCP", json_response=True)

# UI-compatible rule-based suggestion (kept for existing frontend)
@mcp.tool()
def recommend_rule(plant_id: str) -> dict:
    return control_service.suggestion(plant_id)

# LLM-friendly: numeric snapshot only (no suggest)
@mcp.tool()
def get_state(plant_id: str) -> dict:
    return control_service.state_for_ai(plant_id)

# LLM-friendly: planning with objective switch
@mcp.tool()
def decide_actions(plant_id: str, objective: str = "chiller_only") -> dict:
    return control_service.decide_actions(plant_id, objective=objective)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", mount_path="/mcp")

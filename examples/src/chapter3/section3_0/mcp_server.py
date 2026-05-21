"""Chapter 3 baseline server (section 3.0).

Picks up where section 2.1.3 left off: an MCPServer with a single tool.
Section 3.1 adds resources, 3.2 expands tools, 3.3 adds prompts, 3.4 sampling,
3.5 OAuth. Each subsequent section starts from this baseline so the listings
can be read out of order.

Run: uv run python -m chapter3.section3_0.mcp_server
"""

from mcp.server import MCPServer
from pyflight_internal.airports import get_airports_by_country

mcp = MCPServer(
    "flight-booking-agent",
    version="0.1.0",
    website_url="https://mcp-at-scale.com/server",
)


@mcp.tool()
def search_airports(country: str):
    """Search airports in a specific country.

    The country is the alpha-2 code as defined in ISO-3166-2.
    """
    return get_airports_by_country(country)


def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()

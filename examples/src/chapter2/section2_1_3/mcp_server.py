from mcp.server import MCPServer
from pyflight_internal.airports import get_airports_by_country

mcp = MCPServer("flight-booking-agent", 
                version="0.1.0",
                website_url="https://mcp-at-scale.com/server")
def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)

@mcp.tool()
def search_airports(country):
    ''' Search airports in a specific country
    The country is the alpha-2 code as defined in ISO-3166-2 '''
    airports_by_country = get_airports_by_country(country)
    return airports_by_country

if __name__ == "__main__":
    main()

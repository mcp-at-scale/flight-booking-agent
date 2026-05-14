from mcp.server import MCPServer

mcp = MCPServer("flight-booking-agent", 
                version="0.1.0",
                website_url="https://mcp-at-scale.com/server")
def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()

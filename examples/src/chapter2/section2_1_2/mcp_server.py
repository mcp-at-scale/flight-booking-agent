from mcp.server import MCPServer

mcp = MCPServer("flight-booking-agent", 
                version="0.1.0")
def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()

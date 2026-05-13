from mcp.server import MCPServer

mcp = MCPServer("flight-booking-agent", 
                "0.1.0", 
                "A flight booking agent that can search for flights, book flights, and manage bookings.")
def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)
    print("Hello from chapter2!")


if __name__ == "__main__":
    main()

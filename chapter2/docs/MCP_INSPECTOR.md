# MCP Inspector Guide

The MCP Inspector is a web-based debugging tool for testing and visualizing MCP servers. It provides an interactive interface to test tools, resources, and monitor communication between the client and server.

## What is MCP Inspector?

The MCP Inspector is an official tool from the Model Context Protocol team that allows you to:

- **Test Tools**: Call tools with custom parameters and see responses
- **Browse Resources**: View all available resources and their schemas
- **Debug Communication**: See JSON-RPC messages in real-time
- **Validate Schemas**: Check that your server adheres to the MCP protocol
- **Interactive Testing**: Use a visual interface instead of command-line testing

## Running MCP Inspector Locally

### Prerequisites

- Node.js and npm installed
- The MCP server installed and configured

### Quick Start

```bash
cd chapter2
CLIENT_PORT=8001 npx @modelcontextprotocol/inspector uv run flight-booking-mcp
```

This will:
1. Start the MCP Inspector on port 8001
2. Launch the flight-booking MCP server
3. Connect the inspector to the server

### Access the Inspector

Open your browser and navigate to:
```
http://localhost:8001
```

## Using MCP Inspector in Docker

The Docker container has Node.js/npm pre-installed and port 8001 exposed for the inspector.

### Option 1: Run Interactively

```bash
# Start the container
docker run -d \
  --name flight-booking-dev \
  -p 8080:8080 \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd):/home/coder/workspace \
  flight-booking-agent

# Access the container
docker exec -it flight-booking-dev bash

# Run the inspector
cd workspace/chapter2
npx @modelcontextprotocol/inspector uv run flight-booking-mcp
```

Then open `http://localhost:8001` in your browser.

### Option 2: Run in Background (Advanced)

You can create a startup script to run both code-server and the MCP inspector:

```bash
#!/bin/bash
# Start code-server in the background
/home/coder/.local/bin/code-server /home/coder/workspace &

# Start MCP Inspector
cd /home/coder/workspace/chapter2
CLIENT_PORT=8001 npx @modelcontextprotocol/inspector uv run flight-booking-mcp
```

## Using the Inspector Interface

### 1. Tools Tab

The Tools tab shows all available MCP tools:

**search_flights**
- Test flight search with different origins, destinations, and dates
- Toggle `direct_only` to test direct vs. connecting flights
- Adjust layover times

**get_flight_details**
- Enter a flight number (e.g., "FL001")
- Optionally specify a date
- See detailed flight information

**list_airports**
- Filter by country or city
- View all available airports

**list_airlines**
- See all airlines in the system

**get_routes_from_airport**
- Enter an airport code
- See all available destinations

### 2. Resources Tab

Browse available resources:

- **airport://*** - View airport details by code
- **airline://*** - View airline information by code
- **routes://summary** - See network statistics

### 3. Messages Tab

View the raw JSON-RPC communication:
- Request messages sent to the server
- Response messages from the server
- Error messages and debugging info

### 4. Server Info Tab

View server metadata:
- Server name and version
- Available capabilities
- Protocol version

## Example Testing Workflow

### Test Flight Search

1. Go to the **Tools** tab
2. Select **search_flights**
3. Fill in the form:
   ```
   origin: JFK
   destination: LHR
   date: 2025-01-20
   direct_only: false
   ```
4. Click **Execute**
5. View the formatted flight results

### Test Resources

1. Go to the **Resources** tab
2. Click on **airport://**
3. Enter a code (e.g., "CDG")
4. View the resource URI: `airport://CDG`
5. See the airport details returned

### Debug Communication

1. Go to the **Messages** tab
2. Execute any tool or resource
3. See the raw JSON-RPC request:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/call",
     "params": {
       "name": "search_flights",
       "arguments": {
         "origin": "JFK",
         "destination": "LHR",
         "date": "2025-01-20"
       }
     }
   }
   ```
4. See the response from the server

## Common Issues

### Inspector Won't Start

**Error: `npx: command not found`**
- Solution: Ensure Node.js and npm are installed
- Check: `node --version && npm --version`

**Error: Port 8001 already in use**
- Solution: Use a different port
- Command: `CLIENT_PORT=8002 npx @modelcontextprotocol/inspector uv run flight-booking-mcp`

### Inspector Can't Connect to Server

**Error: Server not responding**
- Ensure the MCP server command is correct
- Check server logs for errors
- Verify Python dependencies are installed: `cd chapter2 && uv sync`

### Tools Return Errors

**Error: Invalid date format**
- Use YYYY-MM-DD format (e.g., "2025-01-20")

**Error: Airport not found**
- Check airport codes in the data/airports.json file
- Valid codes: JFK, LHR, CDG, NRT, DXB, etc.

## Environment Variables

- `CLIENT_PORT`: Port for the inspector web interface (default: 6006)
- Set in Docker: Already configured to 8001

## Alternative Testing Methods

### Using curl (Advanced)

Test the server directly via stdio:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  uv run flight-booking-mcp | \
  jq '.'
```

### Using MCP Client Libraries

Build your own test client using the MCP Python SDK:

```python
from mcp.client import Client
import asyncio

async def test_server():
    async with Client() as client:
        # Connect to server
        await client.connect_stdio("uv", "run", "flight-booking-mcp")

        # List tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")

        # Call a tool
        result = await client.call_tool(
            "search_flights",
            origin="JFK",
            destination="LHR",
            date="2025-01-20"
        )
        print(f"Search results: {result}")

asyncio.run(test_server())
```

## Tips for Effective Testing

1. **Start Simple**: Test basic tools like `list_airlines` before complex searches
2. **Use Valid Data**: Refer to the data files for valid codes and values
3. **Check Dates**: Use future dates for flight searches
4. **Test Edge Cases**: Try invalid inputs to test error handling
5. **Monitor Messages**: Watch the Messages tab to understand the protocol

## Resources

- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [MCP Documentation](https://modelcontextprotocol.io)
- [Flight Booking Server Docs](MCP_SERVER.md)
- [Chapter 2 README](README.md)

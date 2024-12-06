import asyncio
import websockets
import datetime
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

# Store connected clients for each port
clients_8080 = set()
clients_8001 = set()

def get_timestamp():
    """Get current timestamp in readable format"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_message(port, message):
    """Print formatted log message to console"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] Message from port {port}:")
    print(f"  → {message}")

async def safe_send(websocket, message):
    """Safely send a message to a websocket with error handling"""
    try:
        await websocket.send(message)
        return True
    except (ConnectionClosedError, ConnectionClosedOK, websockets.exceptions.WebSocketException):
        return False

async def broadcast_message(clients, message):
    """Broadcast message to all clients and remove dead connections"""
    dead_clients = set()
    
    for client in clients:
        success = await safe_send(client, message)
        if not success:
            dead_clients.add(client)
    
    # Remove dead clients
    for dead_client in dead_clients:
        clients.discard(dead_client)
    
    return len(clients) - len(dead_clients)  # Return number of successful sends

async def relay_8080_to_8001(websocket):
    """Handle connections on port 8080 and relay messages to port 8001"""
    client_id = id(websocket)  # Get unique identifier for this client
    try:
        clients_8080.add(websocket)
        print(f"[{get_timestamp()}] New client connected to port 8080 (ID: {client_id})")
        print(f"Active connections - Port 8080: {len(clients_8080)}, Port 8001: {len(clients_8001)}")
        
        async for message in websocket:
            log_message(8080, message)
            if clients_8001:
                successful_sends = await broadcast_message(clients_8001, message)
                print(f"  ↳ Forwarded to {successful_sends} active clients on port 8001")
            else:
                print("  ↳ No clients connected to port 8001")
    except (ConnectionClosedError, ConnectionClosedOK) as e:
        print(f"[{get_timestamp()}] Client {client_id} connection closed on port 8080: {str(e)}")
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling client {client_id} on port 8080: {str(e)}")
    finally:
        clients_8080.discard(websocket)
        print(f"[{get_timestamp()}] Client disconnected from port 8080 (ID: {client_id})")
        print(f"Active connections - Port 8080: {len(clients_8080)}, Port 8001: {len(clients_8001)}")

async def relay_8001_to_8080(websocket):
    """Handle connections on port 8001 and relay messages to port 8080"""
    client_id = id(websocket)  # Get unique identifier for this client
    try:
        clients_8001.add(websocket)
        print(f"[{get_timestamp()}] New client connected to port 8001 (ID: {client_id})")
        print(f"Active connections - Port 8080: {len(clients_8080)}, Port 8001: {len(clients_8001)}")
        
        async for message in websocket:
            log_message(8001, message)
            if clients_8080:
                successful_sends = await broadcast_message(clients_8080, message)
                print(f"  ↳ Forwarded to {successful_sends} active clients on port 8080")
            else:
                print("  ↳ No clients connected to port 8080")
    except (ConnectionClosedError, ConnectionClosedOK) as e:
        print(f"[{get_timestamp()}] Client {client_id} connection closed on port 8001: {str(e)}")
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling client {client_id} on port 8001: {str(e)}")
    finally:
        clients_8001.discard(websocket)
        print(f"[{get_timestamp()}] Client disconnected from port 8001 (ID: {client_id})")
        print(f"Active connections - Port 8080: {len(clients_8080)}, Port 8001: {len(clients_8001)}")

async def main():
    # Start WebSocket servers on both ports, binding to all network interfaces
    server_8080 = await websockets.serve(
        relay_8080_to_8001, 
        "0.0.0.0", 
        8080,
        ping_interval=20,  # Send ping every 20 seconds
        ping_timeout=10    # Wait 10 seconds for pong response
    )
    server_8001 = await websockets.serve(
        relay_8001_to_8080, 
        "0.0.0.0", 
        8001,
        ping_interval=20,
        ping_timeout=10
    )
    
    print(f"[{get_timestamp()}] WebSocket relay server running...")
    print("Listening on all network interfaces:")
    print("  ws://0.0.0.0:8080")
    print("  ws://0.0.0.0:8001")
    print("-" * 50)
    
    # Keep the server running
    await asyncio.gather(
        server_8080.wait_closed(),
        server_8001.wait_closed()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] Server terminated by user")

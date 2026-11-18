from fastapi.staticfiles import StaticFiles
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

players = {}
lock = asyncio.Lock()



async def send_to_all(message):
    async with lock:
        connections = list(players.values())

    for connection in connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass


@app.websocket("/ws")
async def multiplayer(websocket: WebSocket):

    await websocket.accept()

    # Find en ledig spillerplads
    async with lock:
        player_id = None

        for i in (1, 2):
            if i not in players:
                player_id = i
                break

        if player_id is not None:
            players[player_id] = websocket

    # Hvis begge pladser er optaget
    if player_id is None:
        await websocket.send_json({
            "type": "full",
            "message": "Spillet er fuldt"
        })
        await websocket.close()
        return

    print("Spiller", player_id, "forbundet")

    await websocket.send_json({
        "type": "welcome",
        "player": player_id
    })

    await send_to_all({
        "type": "player_joined",
        "player": player_id
    })

    try:
        while True:

            data = await websocket.receive_json()

            await send_to_all({
                "type": "player_message",
                "player": player_id,
                "data": data
            })

    except WebSocketDisconnect:
        pass

    finally:

        async with lock:
            if players.get(player_id) is websocket:
                del players[player_id]

        print("Spiller", player_id, "forlod spillet")

        await send_to_all({
            "type": "player_left",
            "player": player_id
        })

app.mount("/", StaticFiles(directory="website", html=True), name="website")
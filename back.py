from fastapi import (
    FastAPI,
    WebSocket,
    HTTPException,
    Request,
    WebSocketDisconnect,
)
from typing import Dict
import random

app = FastAPI()

rooms: Dict[str, Dict] = {}


@app.get("/")
async def root():
    return {"message": "Server is up and running"}


def validate_number(number: str) -> bool:
    """Validates that a number has 4 digits and they are not repeated."""
    return len(number) == 4 and len(set(number)) == 4


@app.post("/create_room")
async def create_room(request: Request):
    data = await request.json()

    room_id = data.get("room_id")
    player = data.get("player")

    if not room_id:
        raise HTTPException(status_code=400, detail="Room ID is required.")
    if not player:
        raise HTTPException(status_code=400, detail="Player name is required.")

    if room_id in rooms:
        raise HTTPException(status_code=400, detail="The room already exists.")

    rooms[room_id] = {
        "players": [player],
        "turn": None,
        "player1_number": None,
        "player2_number": None,
        "websockets": [],
    }

    return {"message": "Room created", "room_id": room_id}


@app.post("/join_room/")
async def join_room(request: Request):
    data = await request.json()

    room_id = data.get("room_id")
    player = data.get("player")

    if not room_id:
        raise HTTPException(status_code=400, detail="Room ID is required.")
    if not player:
        raise HTTPException(status_code=400, detail="Player name is required.")
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found.")
    if len(rooms[room_id]["players"]) >= 2:
        raise HTTPException(
            status_code=400, detail="The room is already full.")

    rooms[room_id]["players"].append(player)

    return {"message": f"{player} joined room {room_id}"}


@app.post("/submit_number/")
async def submit_number(request: Request):
    data = await request.json()

    room_id = data.get("room_id")
    player = data.get("player")
    number = data.get("number")

    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found.")
    if not validate_number(number):
        raise HTTPException(status_code=400, detail="Invalid number.")

    if rooms[room_id]["players"][0] == player:
        rooms[room_id]["player1_number"] = number
    elif rooms[room_id]["players"][1] == player:
        rooms[room_id]["player2_number"] = number
    else:
        raise HTTPException(
            status_code=400, detail="Player does not belong to the room."
        )

    if rooms[room_id]["player1_number"] and rooms[room_id]["player2_number"]:
        rooms[room_id]["turn"] = random.choice(rooms[room_id]["players"])
        await notify_turn(room_id)

    return {"message": "Number received"}


@app.post("/play/")
async def play(request: Request):
    data = await request.json()

    room_id = data.get("room_id")
    player = data.get("player")
    number = data.get("number")

    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found.")
    if rooms[room_id]["turn"] != player:
        raise HTTPException(status_code=400, detail="It's not your turn.")

    opponent_number = (
        rooms[room_id]["player1_number"]
        if player == rooms[room_id]["players"][1]
        else rooms[room_id]["player2_number"]
    )
    correct = sum(1 for a, b in zip(number, opponent_number) if a == b)
    incorrect = sum(1 for n in number if n in opponent_number) - correct

    rooms[room_id]["turn"] = (
        rooms[room_id]["players"][1]
        if player == rooms[room_id]["players"][0]
        else rooms[room_id]["players"][0]
    )

    await notify_turn(room_id)

    return {
        "correct": correct,
        "incorrect": incorrect,
        "next_turn": rooms[room_id]["turn"],
    }


@app.websocket("/ws/{room_id}/{player}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player: str):
    await websocket.accept()

    if room_id not in rooms or player not in rooms[room_id]["players"]:
        await websocket.close(code=1008)
        return

    rooms[room_id]["websockets"].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        rooms[room_id]["websockets"].remove(websocket)
        await websocket.close()


async def notify_turn(room_id: str):
    turn = rooms[room_id]["turn"]
    message = {"message": f"It's {turn}'s turn"}
    for ws in rooms[room_id]["websockets"]:
        await ws.send_json(message)


@app.get("/wait_for_players/{room_id}")
async def wait_for_players(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found.")
    players = rooms[room_id]["players"]
    return {"connected_players": len(players)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

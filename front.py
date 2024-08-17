import requests
import time
import websockets
import asyncio


def request_number():
    while True:
        number = input("Enter a 4-digit number (no repeating digits): ")
        if len(number) == 4 and len(set(number)) == 4:
            return number
        print("Invalid number. Try again.")


def wait_for_two_players(base_url, room_id):
    print(f"Waiting for both players to connect in room {room_id}")
    while True:
        response = requests.get(f"{base_url}/wait_for_players/{room_id}")
        if response.status_code != 200:
            print(f"GET request failed with status code {
                  response.status_code}")
            time.sleep(5)
            continue

        data = response.json()
        if data["connected_players"] == 2:
            print("Both players are connected. The game will start.")
            break
        else:
            print("Waiting for a second player to connect...")
        time.sleep(5)


async def handle_game(ws_url, room_id, player, base_url):
    async with websockets.connect(
        f"{ws_url}/ws/{room_id}/{player}"
    ) as websocket:
        number = request_number()
        requests.post(
            f"{base_url}/submit_number/",
            json={"room_id": room_id, "player": player, "number": number}
        )
        print("Number sent.")

        while True:
            message = await websocket.recv()
            data = eval(message)
            if data.get("message").startswith("It's the turn of"):
                if player in data["message"]:
                    print("It's your turn.")
                    turn_number = request_number()
                    response = requests.post(
                        f"{base_url}/play/",
                        json={"room_id": room_id, "player": player,
                              "number": turn_number}
                    )
                    result = response.json()
                    if response.status_code == 200:
                        if result["correct"] == 4:
                            print("You won!")
                            break
                        print(
                            f"Correct numbers in the correct position: {
                                result['correct']}"
                        )
                        print(
                            f"Correct numbers in the wrong position: {
                                result['incorrect']}"
                        )
                    else:
                        print("It's not your turn or an error occurred.")
                else:
                    print(data["message"])


def main():
    ip = input("Enter the server IP (127.0.0.1): ")
    if not ip:
        ip = "127.0.0.1"

    port = input("Enter the server port (8000): ")
    if not port:
        port = "8000"
    base_url = f"http://{ip}:{port}"
    ws_url = f"ws://{ip}:{port}"

    response = requests.get(f"{base_url}/")
    if response.status_code != 200:
        print("The server is not running."
              "Please enter the correct server IP and port.")
        return

    while True:
        print("1. Create room")
        print("2. Join a room")
        option = input("Choose an option: ")
        if not option:
            continue
        elif not option.isdigit() or int(option) < 1 or int(option) > 2:
            print("Invalid option. Enter 1 or 2.")
            continue

        player = input("Enter your name: ")
        if not player:
            print("Name cannot be empty.")
            continue

        if option == '1':
            room_id = input("Enter a name for the room: ")
            print(f"Creating room {room_id}.")
            response = requests.post(
                f"{base_url}/create_room",
                json={"room_id": room_id, "player": player}
            )
            if response.status_code == 400:
                print("The room already exists. Do you want to create "
                      "a new one or join an existing one?")

            elif response.status_code == 200:
                print("Room created successfully.")
                break
            elif response.status_code == 422:
                print("Error creating the room. Do you want to create"
                      "a new one or join an existing one?")
        elif option == '2':
            room_id = input("Enter the room ID: ")
            print(f"Joining room {room_id}.")
            response = requests.post(
                f"{base_url}/join_room/",
                json={"room_id": room_id, "player": player}
            )
            if response.status_code == 200:
                print(f"You have joined room {room_id}.")
                break

    print("Waiting for players to connect...")
    wait_for_two_players(base_url, room_id)

    asyncio.run(handle_game(ws_url, room_id, player, base_url))


if __name__ == "__main__":
    main()

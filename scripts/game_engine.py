import json
import random

SHIPS = [
    {"name": "Carrier",    "size": 5},
    {"name": "Battleship", "size": 4},
    {"name": "Cruiser",    "size": 3},
    {"name": "Submarine",  "size": 3},
    {"name": "Destroyer",  "size": 2},
]

ROWS = list("ABCDEFGHIJ")
COLS = list(range(1, 11))

def empty_board():
    return {r: {str(c): "." for c in COLS} for r in ROWS}

def place_ships_random(board):
    ship_positions = {}
    for ship in SHIPS:
        placed = False
        attempts = 0
        while not placed and attempts < 200:
            attempts += 1
            orientation = random.choice(["H", "V"])
            if orientation == "H":
                row = random.choice(ROWS)
                col = random.randint(1, 10 - ship["size"] + 1)
                cells = [(row, str(col + i)) for i in range(ship["size"])]
            else:
                row_idx = random.randint(0, 10 - ship["size"])
                col = random.randint(1, 10)
                cells = [(ROWS[row_idx + i], str(col)) for i in range(ship["size"])]
            if all(board[r][c] == "." for r, c in cells):
                for r, c in cells:
                    board[r][c] = "S"
                ship_positions[ship["name"]] = cells
                placed = True
    return board, ship_positions

def parse_coordinate(coord):
    coord = coord.strip().upper()
    if len(coord) < 2 or len(coord) > 3:
        return None, None
    row = coord[0]
    col = coord[1:]
    if row not in ROWS:
        return None, None
    if not col.isdigit() or int(col) < 1 or int(col) > 10:
        return None, None
    return row, col

def fire(board, hit_overlay, ship_positions, coord):
    row, col = parse_coordinate(coord)
    if row is None:
        return "INVALID", None
    if hit_overlay[row][col] in ["X", "O"]:
        return "ALREADY_FIRED", None
    if board[row][col] == "S":
        hit_overlay[row][col] = "X"
        sunk_ship = check_sunk(board, hit_overlay, ship_positions, row, col)
        if sunk_ship:
            return "SUNK", sunk_ship
        return "HIT", None
    else:
        hit_overlay[row][col] = "O"
        return "MISS", None

def check_sunk(board, hit_overlay, ship_positions, hit_row, hit_col):
    for ship_name, cells in ship_positions.items():
        if (hit_row, hit_col) in cells:
            if all(hit_overlay[r][c] == "X" for r, c in cells):
                return ship_name
    return None

def is_game_over(ship_positions, hit_overlay):
    for ship_name, cells in ship_positions.items():
        if not all(hit_overlay[r][c] == "X" for r, c in cells):
            return False
    return True

def render_board(board, hit_overlay, hide_ships=True):
    lines = ["  " + " ".join(str(c) for c in COLS)]
    for row in ROWS:
        cells = []
        for col in [str(c) for c in COLS]:
            overlay = hit_overlay[row][col]
            if overlay in ["X", "O"]:
                cells.append(overlay)
            elif board[row][col] == "S" and not hide_ships:
                cells.append("S")
            else:
                cells.append(".")
        lines.append(row + " " + " ".join(cells))
    return "\n".join(lines)

def new_game_state(chat_id_p2, offset=0):
    board_p1, ships_p1 = place_ships_random(empty_board())
    board_p2, ships_p2 = place_ships_random(empty_board())
    state = {
        "chat_id_p2": chat_id_p2,
        "turn": "P1",
        "status": "ACTIVE",
        "board_p1": board_p1,
        "board_p2": board_p2,
        "ships_p1": ships_p1,
        "ships_p2": ships_p2,
        "hits_p1": empty_board(),
        "hits_p2": empty_board(),
        "offset": int(offset)
    }
    return json.dumps(state)

def apply_move(state_json, coord, firing_player):
    state = json.loads(state_json)
    if firing_player == "P1":
        result, sunk = fire(
            state["board_p2"], state["hits_p1"],
            state["ships_p2"], coord
        )
    else:
        result, sunk = fire(
            state["board_p1"], state["hits_p2"],
            state["ships_p1"], coord
        )
    if result in ["INVALID", "ALREADY_FIRED"]:
        return json.dumps({"result": result, "sunk": None,
                           "state": state_json, "game_over": False})
    if firing_player == "P1":
        game_over = is_game_over(state["ships_p2"], state["hits_p1"])
        state["turn"] = "P2" if not game_over else "DONE"
    else:
        game_over = is_game_over(state["ships_p1"], state["hits_p2"])
        state["turn"] = "P1" if not game_over else "DONE"
    if game_over:
        state["status"] = "DONE"
    return json.dumps({
        "result": result,
        "sunk": sunk,
        "state": json.dumps(state),
        "game_over": game_over
    })

def get_board_view(state_json, player):
    state = json.loads(state_json)
    if player == "P1":
        enemy_view = render_board(state["board_p2"], state["hits_p1"], hide_ships=True)
        own_view   = render_board(state["board_p1"], state["hits_p2"], hide_ships=False)
    else:
        enemy_view = render_board(state["board_p1"], state["hits_p2"], hide_ships=True)
        own_view   = render_board(state["board_p2"], state["hits_p1"], hide_ships=False)
    return json.dumps({"enemy_view": enemy_view, "own_view": own_view})

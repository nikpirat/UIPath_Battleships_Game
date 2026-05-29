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


# ── Board helpers ────────────────────────────────────────────────────────────

def empty_board():
    return {r: {str(c): "." for c in COLS} for r in ROWS}


def place_ships_random(board):
    ship_positions = {}
    for ship in SHIPS:
        placed, attempts = False, 0
					
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
    row, col = coord[0], coord[1:]
    if row not in ROWS or not col.isdigit() or not (1 <= int(col) <= 10):
        return None, None
    return row, col

def render_board(board, hit_overlay, hide_ships=True):
    lines = ["   " + "  ".join(str(c) for c in COLS)]
    for row in ROWS:
        cells = []
        for col in [str(c) for c in COLS]:
            overlay = hit_overlay[row][col]
            if overlay == "X":
                cells.append("[X]")
            elif overlay == "O":
                cells.append("[O]")
            elif board[row][col] == "S" and not hide_ships:
                cells.append("[S]")
            else:
                cells.append("[~]")
        lines.append(row + " " + "".join(cells))
    return "\n".join(lines)


# ── Game logic ───────────────────────────────────────────────────────────────

def check_sunk(hit_overlay, ship_positions, hit_row, hit_col):
    for ship_name, cells in ship_positions.items():
        # cells may be lists after JSON round-trip, normalize to tuples
        cells_normalized = [tuple(c) for c in cells]
        if (hit_row, hit_col) in cells_normalized:
            if all(hit_overlay[r][c] == "X" for r, c in cells_normalized):
                return ship_name
    return None


def is_game_over(ship_positions, hit_overlay):
    return all(
        hit_overlay[r][c] == "X"
        for cells in ship_positions.values()
        for r, c in (tuple(cell) for cell in cells)  # normalize
    )


def fire(board, hit_overlay, ship_positions, coord):
    row, col = parse_coordinate(coord)
    if row is None:
        return "INVALID", None
    if hit_overlay[row][col] in ["X", "O"]:
        return "ALREADY_FIRED", None
    if board[row][col] == "S":
        hit_overlay[row][col] = "X"
        sunk = check_sunk(hit_overlay, ship_positions, row, col)
        return ("SUNK" if sunk else "HIT"), sunk
    hit_overlay[row][col] = "O"
    return "MISS", None


# ── Public API (called from UiPath) ─────────────────────────────────────────

def new_game_state(chat_id_p2, offset=0):
    """Create a fresh game state with randomly placed ships for both players."""
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
        "hits_p1": empty_board(),   # shots fired BY P1 (land on P2's board)
        "hits_p2": empty_board(),   # shots fired BY P2 (land on P1's board)
        "offset": int(offset),
    }
    return json.dumps(state)


def apply_move(state_json, coord, firing_player, current_offset=None):
    """
    Apply a shot by `firing_player` at `coord`.
    Returns JSON: { result, sunk, state, game_over }
    result: HIT | MISS | SUNK | INVALID | ALREADY_FIRED
    """
    state = json.loads(state_json)

    if firing_player == "P1":
							
        result, sunk = fire(state["board_p2"], state["hits_p1"], state["ships_p2"], coord)
									
		 
    else:
							
        result, sunk = fire(state["board_p1"], state["hits_p2"], state["ships_p1"], coord)
									
		 

    if current_offset is not None:
        state["offset"] = int(current_offset)

    if result in ("INVALID", "ALREADY_FIRED"):
        return json.dumps({"result": result, "sunk": None,
                           "state": json.dumps(state), "game_over": False})

    if firing_player == "P1":
        game_over = is_game_over(state["ships_p2"], state["hits_p1"])
        if game_over:
            state["turn"] = "DONE"
        elif result == "MISS":
            state["turn"] = "P2"
        # HIT / SUNK: stay on P1
    else:
        game_over = is_game_over(state["ships_p1"], state["hits_p2"])
        if game_over:
            state["turn"] = "DONE"
        elif result == "MISS":
            state["turn"] = "P1"
        # HIT / SUNK: stay on P2

    if game_over:
        state["status"] = "DONE"

    return json.dumps({
        "result":    result,
        "sunk":      sunk,
        "state":     json.dumps(state),
        "game_over": game_over,
    })


def get_board_view(state_json, player):
    """
    Return own fleet view + enemy attack view for `player`.
    own_view   – player's own board showing where enemy hit them
    enemy_view – enemy's board showing only the player's own hits (ships hidden)
    """
    state = json.loads(state_json)
    if player == "P1":
        # P1's fleet with P2's hits on it; P2's board with P1's attacks marked
        own_view   = render_board(state["board_p1"], state["hits_p2"], hide_ships=False)
        enemy_view = render_board(state["board_p2"], state["hits_p1"], hide_ships=True)
    else:
																					   
        own_view   = render_board(state["board_p2"], state["hits_p1"], hide_ships=False)
        enemy_view = render_board(state["board_p1"], state["hits_p2"], hide_ships=True)
    return json.dumps({"own_view": own_view, "enemy_view": enemy_view})


def get_dual_board_message(state_json, player):
    """
    Convenience: returns a formatted string with both boards for Telegram.
    Uses the same overlay logic as get_board_view.
    """
    views = json.loads(get_board_view(state_json, player))
    return (
        "YOUR FLEET:\n```\n" + views["own_view"] + "\n```" +
        "\n\nYOUR ATTACKS:\n```\n" + views["enemy_view"] + "\n```"
    )


def result_message(result, sunk_ship=""):
    """
    Returns a human-readable result string.
    """
    if result == "HIT":
        return "HIT! Well done."
    if result == "MISS":
        return "Miss."
    if result == "SUNK":
        return f"You sunk the {sunk_ship}!"
    return ""


def p1_take_turn(state_json, coord):
    """
    Convenience wrapper: apply P1's move AND return the updated board display
    string ready for the next MessageBox — avoids a second Python scope in XAML.
    Returns JSON: { result, sunk, state, game_over, board_display, result_msg }
    """
    move = json.loads(apply_move(state_json, coord, "P1"))
    if move["result"] not in ("INVALID", "ALREADY_FIRED"):
        views = json.loads(get_board_view(move["state"], "P1"))
        move["board_display"] = (
            "=== YOUR FLEET ===\n"   + views["own_view"] +
            "\n\n=== YOUR ATTACKS ===\n" + views["enemy_view"]
        )
        move["result_msg"] = result_message(move["result"], move["sunk"] or "")
    else:
        views = json.loads(get_board_view(state_json, "P1"))
        move["board_display"] = (
            "=== YOUR FLEET ===\n"   + views["own_view"] +
            "\n\n=== YOUR ATTACKS ===\n" + views["enemy_view"]
        )
        move["result_msg"] = ""
        move["state"] = state_json  # keep state unchanged
    return json.dumps(move)


def p2_take_turn(state_json, coord, current_offset):
    """
    Convenience wrapper: apply P2's move AND return everything TakeTurnP2 needs
    in one call — the dual board message, result string, updated state.
    Returns JSON: { result, sunk, state, game_over, board_msg, result_msg }
    """
    move = json.loads(apply_move(state_json, coord, "P2", current_offset))
    if move["result"] not in ("INVALID", "ALREADY_FIRED"):
        move["board_msg"] = get_dual_board_message(move["state"], "P2")
        p1_views = json.loads(get_board_view(move["state"], "P1"))
        move["p1_board_display"] = (
            "=== YOUR FLEET ===\n" + p1_views["own_view"] +
            "\n\n=== YOUR ATTACKS ===\n" + p1_views["enemy_view"]
        )
    else:
        move["board_msg"] = ""
        move["p1_board_display"] = state_json  # unused on invalid, safe fallback
    move["result_msg"] = result_message(move["result"], move.get("sunk") or "")
    return json.dumps(move)
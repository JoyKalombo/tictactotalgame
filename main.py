import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

# --- Initialise Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_creds"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")
    })

# Initialize game state
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'board': [None] * 9,  # Board starts with None (empty)
        'current_player': 'Player 1',
        'player1_numbers': [],
        'player2_numbers': [],
        'selected_number': None,
        'winner': None,
        'target1': 16,
        'target2': 14,
        'used_numbers': set(),
        'game_mode': 'computer',
        'room_id': None
    }

# Game logic
def check_winner(player_numbers, target_sum):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]              # Diagonals
    ]

    for condition in win_conditions:
        line_numbers = [
            st.session_state.game_state['board'][i] for i in condition
            if st.session_state.game_state['board'][i] in player_numbers
        ]
        if len(line_numbers) == 3 and sum(line_numbers) == target_sum:
            return True
    return False


def select_number(number):
    if number not in st.session_state.game_state['used_numbers']:
        st.session_state.game_state['selected_number'] = number
        st.session_state.game_state['used_numbers'].add(number)


def make_move(index):
    if st.session_state.game_state['winner']:
        return

    selected_number = st.session_state.game_state['selected_number']
    current_player = st.session_state.game_state['current_player']

    if st.session_state.game_state['board'][index] is None:
        st.session_state.game_state['board'][index] = selected_number

        if current_player == 'Player 1':
            st.session_state.game_state['player1_numbers'].append(selected_number)
            st.session_state.game_state['current_player'] = 'Player 2'

            if st.session_state.game_state['game_mode'] == 'player':
                update_firebase_game_state()
            else:
                if not st.session_state.game_state['winner']:
                    computer_move()
        else:
            st.session_state.game_state['player2_numbers'].append(selected_number)
            st.session_state.game_state['current_player'] = 'Player 1'

        # Check for a winner
        if check_winner(st.session_state.game_state['player1_numbers'], st.session_state.game_state['target1']):
            st.session_state.game_state['winner'] = 'Player 1 wins'
        elif check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
            st.session_state.game_state['winner'] = 'Player 2 wins'


def computer_move():
    available_moves = [
        i for i, val in enumerate(st.session_state.game_state['board']) if val is None
    ]

    if available_moves:
        move = random.choice(available_moves)
        available_numbers = [
            num for num in range(1, 10)
            if num not in st.session_state.game_state['used_numbers']
        ]
        chosen_number = random.choice(available_numbers)

        st.session_state.game_state['board'][move] = chosen_number
        st.session_state.game_state['used_numbers'].add(chosen_number)
        st.session_state.game_state['player2_numbers'].append(chosen_number)
        st.session_state.game_state['current_player'] = 'Player 1'

        if check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
            st.session_state.game_state['winner'] = 'Computer wins'


def update_firebase_game_state():
    if st.session_state.game_state['room_id']:
        ref = db.reference(f"games/{st.session_state.game_state['room_id']}")
        ref.set(st.session_state.game_state)


def display_board():
    cols = st.columns(3)
    for i in range(3):
        for j in range(3):
            index = i * 3 + j
            with cols[j]:
                if st.session_state.game_state['board'][index] is None:
                    st.button(' ', key=index, on_click=make_move, args=(index,))
                else:
                    st.write(str(st.session_state.game_state['board'][index]))


def number_selection():
    available_numbers = list(range(1, 10))
    for num in available_numbers:
        if num not in st.session_state.game_state['used_numbers']:
            st.button(str(num), key=f"select_{num}", on_click=select_number, args=(num,))


def reset_game():
    st.session_state.game_state = {
        'board': [None] * 9,
        'current_player': 'Player 1',
        'player1_numbers': [],
        'player2_numbers': [],
        'selected_number': None,
        'winner': None,
        'target1': 16,
        'target2': 14,
        'used_numbers': set(),
        'game_mode': 'computer',
        'room_id': None
    }

# Main game loop
st.title("Tic Tac Total: Player vs Computer")

# Game mode selection
game_mode = st.selectbox("Select Game Mode:", ["Play Against Computer", "Play Against Player"])

if game_mode == "Play Against Player":
    st.session_state.game_state['game_mode'] = 'player'
    if st.session_state.game_state['room_id'] is None:
        st.session_state.game_state['room_id'] = f"game_{random.randint(1000, 9999)}"
    st.write(f"Join room: {st.session_state.game_state['room_id']}")

if st.session_state.game_state['winner']:
    st.write(st.session_state.game_state['winner'])
    st.button("Reset Game", on_click=reset_game)
else:
    st.write(f"Current Player: {st.session_state.game_state['current_player']}")

    if st.session_state.game_state['current_player'] == 'Player 1' and not st.session_state.game_state['winner']:
        st.write("Select a number to place on the board:")
        number_selection()

    display_board()
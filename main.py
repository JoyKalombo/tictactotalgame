import os
import json
import streamlit as st
import firebase_admin
import random
from firebase_admin import credentials, db
from dotenv import load_dotenv


# --- Firebase Setup ---
def initialize_firebase():
    """Initialize Firebase app with credentials from Streamlit secrets."""
    if not firebase_admin._apps:
        db_url = st.secrets["firebase_db_url"]
        if not db_url:
            st.error("Firebase database URL is not set correctly in Streamlit secrets!")
        else:
            st.write(f"Firebase Database URL: {db_url}")  # Display URL (for debugging)

        cred = credentials.Certificate(json.loads(st.secrets["firebase_creds"]))
        firebase_admin.initialize_app(cred, {
            'databaseURL': db_url  # Fetch URL from Streamlit secrets
        })


# --- Game State Initialization ---
def initialize_game_state():
    """Initialize game state in session."""
    if 'game_state' not in st.session_state:
        st.session_state.game_state = {
            'board': [None] * 9,  # Empty board
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


# --- Game Logic ---
def check_winner(player_numbers, target_sum):
    """Check if the player has a winning sum of selected numbers."""
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]  # Diagonals
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
    """Select number for the current player and mark it as used."""
    if number not in st.session_state.game_state['used_numbers']:
        st.session_state.game_state['selected_number'] = number
        st.session_state.game_state['used_numbers'].add(number)


def update_firebase_game_state():
    """Update the game state to Firebase when playing against another player."""
    if st.session_state.game_state['room_id']:
        st.write(f"Updating Firebase for room: {st.session_state.game_state['room_id']}")
        ref = db.reference(f"games/{st.session_state.game_state['room_id']}")
        ref.set(st.session_state.game_state)
    else:
        st.write("Error: room_id is None.")


def make_move(index):
    """Make a move by placing the selected number on the board."""
    if st.session_state.game_state['winner']:
        return  # Stop if there's already a winner

    selected_number = st.session_state.game_state['selected_number']
    current_player = st.session_state.game_state['current_player']

    if st.session_state.game_state['board'][index] is None:
        st.session_state.game_state['board'][index] = selected_number

        # Update numbers for each player
        if current_player == 'Player 1':
            st.session_state.game_state['player1_numbers'].append(selected_number)
            st.session_state.game_state['current_player'] = 'Player 2'
        else:
            st.session_state.game_state['player2_numbers'].append(selected_number)
            st.session_state.game_state['current_player'] = 'Player 1'

        # Check for a winner after the move
        if check_winner(st.session_state.game_state['player1_numbers'], st.session_state.game_state['target1']):
            st.session_state.game_state['winner'] = 'Player 1 wins'
        elif check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
            st.session_state.game_state['winner'] = 'Player 2 wins'

        # After a move, update Firebase if in multiplayer mode
        if st.session_state.game_state['game_mode'] == 'player':
            update_firebase_game_state()


def computer_move():
    """Simulate a computer move by randomly selecting an available spot."""
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


# --- UI Functions ---
def display_board():
    """Display the game board using Streamlit columns."""
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
    """Allow the player to select a number to place on the board."""
    available_numbers = list(range(1, 10))
    for num in available_numbers:
        if num not in st.session_state.game_state['used_numbers']:
            if st.session_state.game_state['current_player'] == 'Player 1' and not st.session_state.game_state['winner']:
                st.button(f"Player 1: {num}", key=f"select_{num}", on_click=select_number, args=(num,))
            elif st.session_state.game_state['current_player'] == 'Player 2' and not st.session_state.game_state['winner']:
                st.button(f"Player 2: {num}", key=f"select_{num}", on_click=select_number, args=(num,))


def reset_game():
    """Reset the game to its initial state."""
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


# --- Main Game Loop ---
def main():
    st.title("Tic Tac Total: Player vs Computer")

    # Display the target totals for each player
    st.write(f"Player 1's target total: {st.session_state.game_state['target1']}")
    st.write(f"Player 2's target total: {st.session_state.game_state['target2']}")

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
        number_selection()

    display_board()


if __name__ == "__main__":
    initialize_firebase()
    initialize_game_state()
    main()
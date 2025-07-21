import random
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import os
import json

# Firebase setup... initialise firebase admin SDK
if not firebase_admin._apps:
    # Load credentials directly from the Streamlit secrets
    firebase_creds = st.secrets["firebase_creds"]  # This is a string, not a file path

    # Parse the string into a dictionary using json.loads
    firebase_creds_dict = json.loads(firebase_creds)

    # Initialize Firebase app with the credentials
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["firebase"]["db_url"]  # Use the db_url from the secrets file
    })

# Initialize game state
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'board': [None, None, None, None, None, None, None, None, None],  # Board starts with None (empty)
        'current_player': 'Player 1',  # Start with Player 1
        'player1_numbers': [],  # Numbers selected by Player 1
        'player2_numbers': [],  # Numbers selected by Player 2 (Computer)
        'selected_number': None,  # The number selected by the player
        'winner': None,  # To store winner
        'target1': 16,  # Target sum for Player 1
        'target2': 14,  # Target sum for Player 2 (Computer)
        'used_numbers': set(),  # Keep track of all used numbers to prevent repetition
        'game_mode': 'computer',  # Default mode is against computer
        'room_id': None  # Room ID for multiplayer game
    }


# Game logic
def check_winner(player_numbers, target_sum):
    win_conditions = [
        [0, 1, 2],  # First row
        [3, 4, 5],  # Second row
        [6, 7, 8],  # Third row
        [0, 3, 6],  # First column
        [1, 4, 7],  # Second column
        [2, 5, 8],  # Third column
        [0, 4, 8],  # Diagonal
        [2, 4, 6]  # Diagonal
    ]

    for condition in win_conditions:
        line_numbers = [st.session_state.game_state['board'][i] for i in condition if
                        st.session_state.game_state['board'][i] in player_numbers]

        if len(line_numbers) == 3 and sum(line_numbers) == target_sum:
            return True
    return False


def select_number(number):
    if number not in st.session_state.game_state['used_numbers']:  # Check if the number is already used
        st.session_state.game_state['selected_number'] = number
        st.session_state.game_state['used_numbers'].add(number)  # Mark number as used


def make_move(index):
    if st.session_state.game_state['winner']:
        return  # Prevent making a move if there is a winner

    selected_number = st.session_state.game_state['selected_number']
    current_player = st.session_state.game_state['current_player']

    # Ensure the spot is available (empty)
    if st.session_state.game_state['board'][index] is None:  # Ensure the spot is empty
        # Place the number on the board
        st.session_state.game_state['board'][index] = selected_number

        # Track the player's numbers
        if current_player == 'Player 1':
            st.session_state.game_state['player1_numbers'].append(selected_number)
            st.session_state.game_state['current_player'] = 'Player 2'  # Switch to other player
            if st.session_state.game_state['game_mode'] == 'player':  # Multiplayer mode
                update_firebase_game_state()
            else:
                if not st.session_state.game_state['winner']:  # If no winner, let computer play
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
    available_moves = [i for i, val in enumerate(st.session_state.game_state['board'])
                       if val is None]

    if available_moves:
        move = random.choice(available_moves)
        # Select a random number from the remaining available ones (that are not already chosen)
        available_numbers = [num for num in range(1, 10) if num not in st.session_state.game_state['used_numbers']]
        chosen_number = random.choice(available_numbers)

        st.session_state.game_state['board'][move] = chosen_number
        st.session_state.game_state['used_numbers'].add(chosen_number)  # Mark as used
        st.session_state.game_state['current_player'] = 'Player 1'

        if check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
            st.session_state.game_state['winner'] = 'Computer wins'


def update_firebase_game_state():
    if st.session_state.game_state['room_id']:
        ref = db.reference(f"games/{st.session_state.game_state['room_id']}")
        ref.set(st.session_state.game_state)  # Update the game state on Firebase


def display_board():
    cols = st.columns(3)  # Create 3 columns for each row

    for i in range(3):
        with cols[i]:
            for j in range(3):
                index = i * 3 + j
                # Show button for each empty spot on the board
                if st.session_state.game_state['board'][index] is None:
                    st.button(' ', key=index, on_click=make_move, args=(index,))
                else:
                    # Display the number if already selected
                    st.write(str(st.session_state.game_state['board'][index]))


# Number selection for Player 1
def number_selection():
    available_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    for num in available_numbers:
        # Disable the button if the number has already been used
        if num not in st.session_state.game_state['used_numbers']:
            st.button(str(num), key=f"select_{num}", on_click=select_number, args=(num,))


def reset_game():
    # Reset all game state variables to initial values
    st.session_state.game_state = {
        'board': [None, None, None, None, None, None, None, None, None],
        'current_player': 'Player 1',
        'player1_numbers': [],
        'player2_numbers': [],
        'selected_number': None,
        'winner': None,
        'target1': 16,
        'target2': 14,
        'used_numbers': set(),
        'game_mode': 'computer',
        'room_id': None  # Reset the room ID for multiplayer
    }


# Main game loop
st.title("Tic Tac Total: Player vs Computer")

# Game mode selection
game_mode = st.selectbox("Select Game Mode:", ["Play Against Computer", "Play Against Player"])

if game_mode == "Play Against Player":
    st.session_state.game_state['game_mode'] = 'player'
    # Generate a unique room_id for multiplayer play
    if st.session_state.game_state['room_id'] is None:
        st.session_state.game_state['room_id'] = f"game_{random.randint(1000, 9999)}"
    st.write(f"Join room: {st.session_state.game_state['room_id']}")

if st.session_state.game_state['winner']:
    st.write(st.session_state.game_state['winner'])
    # Display reset button after the game ends
    st.button("Reset Game", on_click=reset_game)
else:
    st.write(f"Current Player: {st.session_state.game_state['current_player']}")

# Allow Player 1 to select a number only if the game is still active
if st.session_state.game_state['current_player'] == 'Player 1' and not st.session_state.game_state['winner']:
    st.write("Select a number to place on the board:")
    number_selection()

display_board()
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
        try:
            # Check for Streamlit secrets first
            if "firebase_creds" in st.secrets and "firebase_db_url" in st.secrets:
                cred_dict = st.secrets["firebase_creds"]
                db_url = st.secrets["firebase_db_url"]
            # Fallback for local testing with .env file
            else:
                load_dotenv()
                cred_json = os.getenv("FIREBASE_CREDS")
                db_url = os.getenv("FIREBASE_DB_URL")
                if cred_json:
                    cred_dict = json.loads(cred_json)
                else:
                    st.error("Firebase credentials not found.")
                    return

            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            st.success("Firebase initialized successfully!")
        except Exception as e:
            st.error(f"Error initializing Firebase: {e}")


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
            'room_id': None,
            'player_turn_changed': False  # Flag to manage turn-based logic
        }


# --- Firebase Integration Functions ---
def get_firebase_game_state(room_id):
    """Retrieve game state from Firebase."""
    if room_id:
        ref = db.reference(f"games/{room_id}")
        return ref.get()
    return None


def update_firebase_game_state():
    """Update the game state to Firebase."""
    room_id = st.session_state.game_state['room_id']
    if room_id:
        ref = db.reference(f"games/{room_id}")
        # Convert set to list for JSON serialization
        state_to_save = st.session_state.game_state.copy()
        state_to_save['used_numbers'] = list(state_to_save['used_numbers'])
        ref.set(state_to_save)
    else:
        st.error("Error: room_id is not set.")


def sync_from_firebase():
    """Sync game state from Firebase if in multiplayer mode."""
    if st.session_state.game_state['game_mode'] == 'player' and st.session_state.game_state['room_id']:
        firebase_state = get_firebase_game_state(st.session_state.game_state['room_id'])
        if firebase_state:
            # Convert used_numbers back to a set
            firebase_state['used_numbers'] = set(firebase_state['used_numbers'])
            st.session_state.game_state.update(firebase_state)


# --- Game Logic ---
def check_winner(player_numbers, target_sum):
    """Check if the current board state has a winner for a given player."""
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]  # Diagonals
    ]
    board = st.session_state.game_state['board']
    for condition in win_conditions:
        # Check if all three spots in the condition are filled with numbers from the current player
        line_values = [board[i] for i in condition]
        if all(val is not None for val in line_values) and sum(line_values) == target_sum:
            return True
    return False


def select_number(number):
    """Set the number to be placed on the board."""
    st.session_state.game_state['selected_number'] = number
    st.success(
        f"{st.session_state.game_state['current_player']} selected number {number}. Now click on a spot on the board to place it.")


def make_move(index):
    """Place the selected number on the board and update game state."""
    game_state = st.session_state.game_state

    if game_state['winner'] or game_state['selected_number'] is None or game_state['board'][index] is not None:
        return  # Do nothing if game is over, no number is selected, or spot is taken

    selected_number = game_state['selected_number']
    current_player = game_state['current_player']

    # Place the number and update state
    game_state['board'][index] = selected_number
    game_state['used_numbers'].add(selected_number)

    if current_player == 'Player 1':
        game_state['player1_numbers'].append(selected_number)
        if check_winner(game_state['player1_numbers'], game_state['target1']):
            game_state['winner'] = 'Player 1 wins!'
    else:  # Player 2 or Computer
        game_state['player2_numbers'].append(selected_number)
        if check_winner(game_state['player2_numbers'], game_state['target2']):
            game_state['winner'] = 'Player 2 wins!'

    # Reset selected number and change player turn
    game_state['selected_number'] = None
    if not game_state['winner']:
        game_state['current_player'] = 'Player 2' if current_player == 'Player 1' else 'Player 1'
        game_state['player_turn_changed'] = True

    # Update Firebase if in multiplayer mode
    if game_state['game_mode'] == 'player':
        update_firebase_game_state()
        st.experimental_rerun()  # Rerun to sync with other player


def computer_move():
    """Simulate a computer's turn."""
    game_state = st.session_state.game_state

    available_moves = [i for i, val in enumerate(game_state['board']) if val is None]
    available_numbers = [num for num in range(1, 10) if num not in game_state['used_numbers']]

    if available_moves and available_numbers:
        move_index = random.choice(available_moves)
        chosen_number = random.choice(available_numbers)

        # Place the computer's number and update state
        game_state['board'][move_index] = chosen_number
        game_state['used_numbers'].add(chosen_number)
        game_state['player2_numbers'].append(chosen_number)

        if check_winner(game_state['player2_numbers'], game_state['target2']):
            game_state['winner'] = 'Computer wins!'

        game_state['current_player'] = 'Player 1'
        game_state['player_turn_changed'] = True


# --- UI Functions ---
def display_board():
    """Display the game board using Streamlit columns."""
    for i in range(3):
        cols = st.columns(3)
        for j in range(3):
            index = i * 3 + j
            with cols[j]:
                val = st.session_state.game_state['board'][index]
                if val is None:
                    # The button is disabled if a number hasn't been selected or if there's a winner
                    is_disabled = st.session_state.game_state['selected_number'] is None or st.session_state.game_state[
                        'winner']
                    st.button(' ', key=f"board_{index}", on_click=make_move, args=(index,), disabled=is_disabled)
                else:
                    st.button(str(val), key=f"board_{index}", disabled=True)


def number_selection_ui():
    """Display the number selection buttons for the current player."""
    st.subheader("Select a number:")
    available_numbers = [num for num in range(1, 10) if num not in st.session_state.game_state['used_numbers']]
    cols = st.columns(len(available_numbers))
    for i, num in enumerate(available_numbers):
        with cols[i]:
            if st.button(str(num), key=f"select_{num}",
                         disabled=st.session_state.game_state['selected_number'] is not None):
                select_number(num)


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
        'game_mode': st.session_state.game_state['game_mode'],  # Keep the same mode
        'room_id': st.session_state.game_state['room_id'] if st.session_state.game_state[
                                                                 'game_mode'] == 'player' else None,
        'player_turn_changed': False
    }


# --- Main Game Loop ---
def main():
    st.title("Tic Tac Total: The Number Game")

    # Initialize Firebase and game state
    initialize_firebase()
    initialize_game_state()

    # --- Game Mode Selection ---
    with st.sidebar:
        st.subheader("Game Options")
        game_mode_choice = st.selectbox("Select Game Mode:", ["Play Against Computer", "Play Against Player"],
                                        key='mode_select')

        if game_mode_choice == "Play Against Player":
            st.session_state.game_state['game_mode'] = 'player'
            if st.session_state.game_state['room_id'] is None:
                st.session_state.game_state['room_id'] = f"game_{random.randint(1000, 9999)}"
            st.success(f"Multiplayer Room ID: **{st.session_state.game_state['room_id']}**")
            st.info("Share this ID with a friend to play!")
            sync_from_firebase()
        else:
            if st.session_state.game_state['game_mode'] == 'player':
                reset_game()  # Reset if switching back to computer mode
            st.session_state.game_state['game_mode'] = 'computer'
            st.session_state.game_state['room_id'] = None

    st.write(f"Player 1's target total: **{st.session_state.game_state['target1']}**")
    st.write(f"Player 2's target total: **{st.session_state.game_state['target2']}**")
    st.write("---")

    # --- Game UI ---
    if st.session_state.game_state['winner']:
        st.balloons()
        st.success(st.session_state.game_state['winner'])
        st.button("Reset Game", on_click=reset_game)

    else:
        st.write(f"Current Player: **{st.session_state.game_state['current_player']}**")

        # Display the number selection UI
        number_selection_ui()

        # Check for computer's turn and make a move
        if st.session_state.game_state['game_mode'] == 'computer' and st.session_state.game_state[
            'current_player'] == 'Player 2' and st.session_state.game_state['player_turn_changed']:
            st.info("Computer is thinking...")
            computer_move()
            st.session_state.game_state['player_turn_changed'] = False  # Reset flag
            st.experimental_rerun()

        display_board()


if __name__ == "__main__":
    main()
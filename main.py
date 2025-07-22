import random
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import os  # Import the os module

# --- Firebase Setup ---
# Initialize Firebase Admin SDK if it hasn't been initialized yet.
# This check prevents re-initialization errors in Streamlit.
if not firebase_admin._apps:
    try:
        # Load Firebase credentials directly as a JSON string from Streamlit secrets.
        # The 'firebase_creds' key in .streamlit/secrets.toml should contain the full JSON.
        firebase_creds_str = st.secrets["firebase_creds"]
        firebase_creds_dict = json.loads(firebase_creds_str)

        # Initialize Firebase app with the credentials and database URL from environment variable.
        cred = credentials.Certificate(firebase_creds_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv("FIREBASE_DB_URL")  # Access db_url via os.getenv
        })
        st.success("Firebase initialized successfully!")
    except KeyError as e:
        st.error(
            f"Firebase secret '{e}' not found. Please ensure 'firebase_creds' and 'FIREBASE_DB_URL' are set in your Streamlit secrets.")
        st.stop()  # Stop the app if secrets are missing
    except json.JSONDecodeError:
        st.error(
            "Error decoding Firebase credentials. Ensure 'firebase_creds' in your Streamlit secrets is a valid JSON string.")
        st.stop()  # Stop the app if JSON is invalid
    except Exception as e:
        st.error(f"An unexpected error occurred during Firebase initialization: {e}")
        st.stop()  # Stop for other errors

# --- Game State Initialization ---
# Initialize game state in Streamlit's session_state.
# This ensures the state persists across reruns of the app.
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'board': [None] * 9,  # The game board (3x3), initialized with None (empty)
        'current_player': 'Player 1',  # Start with Player 1
        'player1_numbers': [],  # Numbers selected by Player 1
        'player2_numbers': [],  # Numbers selected by Player 2 (Computer/Opponent)
        'selected_number': None,  # The number selected by the player for their turn
        'winner': None,  # Stores the winner of the game (e.g., 'Player 1 wins', 'Draw')
        'target1': 16,  # Target sum for Player 1 to win
        'target2': 14,  # Target sum for Player 2 (Computer/Opponent) to win
        'used_numbers': [],  # List to keep track of all used numbers (for Firebase compatibility)
        'game_mode': 'computer',  # Default mode: 'computer' or 'player' (multiplayer)
        'room_id': None,  # Room ID for multiplayer games
        'player_role': None,  # 'host' or 'joiner' in multiplayer
        'message': 'Welcome to Tic Tac Total!',  # Messages to display to the user
    }


# --- Game Logic Functions ---

def check_winner(player_numbers, target_sum):
    """
    Checks if a player has won the game.
    A player wins if they have 3 numbers in a row, column, or diagonal that sum up to their target.
    """
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]  # Diagonals
    ]

    current_board = st.session_state.game_state['board']

    for condition in win_conditions:
        # Get numbers from the board that match the current win condition and belong to the player
        line_numbers_on_board = [current_board[i] for i in condition if current_board[i] is not None]

        # Filter these numbers to only include those that were played by the current player
        player_specific_line = [num for num in line_numbers_on_board if num in player_numbers]

        # Check if all three spots in the condition are filled by the player's numbers
        # and if their sum matches the target sum.
        if len(player_specific_line) == 3 and sum(player_specific_line) == target_sum:
            return True
    return False


def select_number(number):
    """
    Selects a number for the current player to place on the board.
    The number is stored in session_state.selected_number.
    """
    # Check if the number has already been used on the board
    if number in st.session_state.game_state['used_numbers']:
        st.session_state.game_state['message'] = "This number has already been used. Please select another."
        return

    # Check if a winner has already been declared
    if st.session_state.game_state['winner']:
        st.session_state.game_state['message'] = "Game is over. Reset to play again."
        return

    st.session_state.game_state['selected_number'] = number
    st.session_state.game_state['message'] = f"You selected {number}. Now click an empty square on the board."


def make_move(index):
    """
    Places the currently selected number on the board at the given index.
    Updates game state, checks for winner, and triggers computer move if applicable.
    """
    # Prevent moves if there's a winner, no number selected, or the spot is not empty
    if st.session_state.game_state['winner']:
        st.session_state.game_state['message'] = "Game is already over."
        return
    if st.session_state.game_state['selected_number'] is None:
        st.session_state.game_state['message'] = "Please select a number first."
        return
    if st.session_state.game_state['board'][index] is not None:
        st.session_state.game_state['message'] = "This spot is already taken."
        return

    selected_number = st.session_state.game_state['selected_number']
    current_player = st.session_state.game_state['current_player']

    # Update the board and used numbers
    st.session_state.game_state['board'][index] = selected_number
    st.session_state.game_state['used_numbers'].append(selected_number)  # Add to used numbers

    # Track numbers for the current player
    if current_player == 'Player 1':
        st.session_state.game_state['player1_numbers'].append(selected_number)
    else:  # Player 2 (Computer or Human)
        st.session_state.game_state['player2_numbers'].append(selected_number)

    # Reset selected number after placing it
    st.session_state.game_state['selected_number'] = None

    # Check for winner after the move
    if check_winner(st.session_state.game_state['player1_numbers'], st.session_state.game_state['target1']):
        st.session_state.game_state['winner'] = 'Player 1 wins!'
        st.session_state.game_state['message'] = 'Player 1 wins! Game Over.'
    elif check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
        st.session_state.game_state['winner'] = 'Player 2 wins!'
        st.session_state.game_state['message'] = 'Player 2 wins! Game Over.'
    elif len(st.session_state.game_state['used_numbers']) == 9:  # All squares filled, no winner
        st.session_state.game_state['winner'] = 'It\'s a draw!'
        st.session_state.game_state['message'] = 'It\'s a draw! Game Over.'
    else:
        # Switch to the next player
        st.session_state.game_state['current_player'] = 'Player 2' if current_player == 'Player 1' else 'Player 1'
        st.session_state.game_state['message'] = f"{st.session_state.game_state['current_player']}'s turn."

    # If in multiplayer mode, update Firebase after every move
    if st.session_state.game_state['game_mode'] == 'player' and st.session_state.game_state['room_id']:
        update_firebase_game_state()
    elif st.session_state.game_state['game_mode'] == 'computer' and not st.session_state.game_state['winner']:
        # If against computer and no winner yet, trigger computer's move
        computer_move()

    st.rerun()  # Rerun the app to update the UI


def computer_move():
    """
    Handles the computer's move in single-player mode.
    The computer selects a random available number and a random empty spot.
    """
    if st.session_state.game_state['winner']:
        return

    available_moves = [i for i, val in enumerate(st.session_state.game_state['board']) if val is None]
    available_numbers = [num for num in range(1, 10) if num not in st.session_state.game_state['used_numbers']]

    if available_moves and available_numbers:
        move_index = random.choice(available_moves)
        chosen_number = random.choice(available_numbers)

        st.session_state.game_state['board'][move_index] = chosen_number
        st.session_state.game_state['used_numbers'].append(chosen_number)  # Add to used numbers
        st.session_state.game_state['player2_numbers'].append(chosen_number)  # Computer's numbers

        # Check for winner after computer's move
        if check_winner(st.session_state.game_state['player2_numbers'], st.session_state.game_state['target2']):
            st.session_state.game_state['winner'] = 'Player 2 (Computer) wins!'
            st.session_state.game_state['message'] = 'Computer wins! Game Over.'
        elif len(st.session_state.game_state['used_numbers']) == 9:
            st.session_state.game_state['winner'] = 'It\'s a draw!'
            st.session_state.game_state['message'] = 'It\'s a draw! Game Over.'
        else:
            st.session_state.game_state['current_player'] = 'Player 1'
            st.session_state.game_state['message'] = 'Player 1\'s turn.'
    else:  # No more moves or numbers, it's a draw
        st.session_state.game_state['winner'] = 'It\'s a draw!'
        st.session_state.game_state['message'] = 'It\'s a draw! Game Over.'

    st.rerun()  # Rerun to update UI after computer move


def reset_game():
    """
    Resets the game state to its initial values.
    If in multiplayer, also resets the Firebase room state.
    """
    st.session_state.game_state = {
        'board': [None] * 9,
        'current_player': 'Player 1',
        'player1_numbers': [],
        'player2_numbers': [],
        'selected_number': None,
        'winner': None,
        'target1': 16,
        'target2': 14,
        'used_numbers': [],
        'game_mode': st.session_state.game_state['game_mode'],  # Keep current game mode
        'room_id': st.session_state.game_state['room_id'],  # Keep room ID if in multiplayer
        'player_role': st.session_state.game_state['player_role'],  # Keep player role
        'message': 'Game reset. Player 1\'s turn.' if st.session_state.game_state[
                                                          'game_mode'] == 'computer' else 'Game reset. Waiting for players.'
    }

    # If in multiplayer, also reset the room in Firebase
    if st.session_state.game_state['game_mode'] == 'player' and st.session_state.game_state['room_id']:
        update_firebase_game_state()  # Overwrite with initial state

    st.rerun()  # Rerun to update UI after reset


# --- Firebase Multiplayer Functions ---

def update_firebase_game_state():
    """
    Updates the current game state in Firebase Realtime Database.
    """
    if st.session_state.game_state['room_id']:
        try:
            ref = db.reference(f"games/{st.session_state.game_state['room_id']}")
            # Firebase Realtime Database stores lists, so 'used_numbers' is fine as a list.
            ref.set(st.session_state.game_state)
            st.session_state.game_state['message'] = "Game state updated in Firebase."
        except Exception as e:
            st.session_state.game_state['message'] = f"Error updating Firebase: {e}"
            st.error(f"Error updating Firebase: {e}")


def get_firebase_game_state():
    """
    Fetches the game state from Firebase Realtime Database and updates local session state.
    """
    if st.session_state.game_state['room_id']:
        try:
            ref = db.reference(f"games/{st.session_state.game_state['room_id']}")
            firebase_data = ref.get()
            if firebase_data:
                # Update local game state with data from Firebase
                st.session_state.game_state.update(firebase_data)
                st.session_state.game_state['message'] = "Game state synced from Firebase."
            else:
                st.session_state.game_state[
                    'message'] = "No game found for this Room ID. Please create or join a valid room."
                st.session_state.game_state['room_id'] = None  # Clear invalid room ID
        except Exception as e:
            st.session_state.game_state['message'] = f"Error fetching from Firebase: {e}"
            st.error(f"Error fetching from Firebase: {e}")
    st.rerun()  # Rerun to update UI after sync


def create_room():
    """
    Creates a new unique room in Firebase for multiplayer game.
    """
    new_room_id = f"game_{random.randint(1000, 9999)}"
    st.session_state.game_state['room_id'] = new_room_id
    st.session_state.game_state['game_mode'] = 'player'
    st.session_state.game_state['player_role'] = 'host'
    st.session_state.game_state['message'] = f"Room created: {new_room_id}. Share this ID with your opponent!"

    # Initialize the room state in Firebase
    update_firebase_game_state()
    st.rerun()


def join_room(room_id_input):
    """
    Attempts to join an existing room in Firebase.
    """
    if not room_id_input:
        st.session_state.game_state['message'] = "Please enter a Room ID to join."
        return

    try:
        ref = db.reference(f"games/{room_id_input}")
        firebase_data = ref.get()
        if firebase_data:
            st.session_state.game_state.update(firebase_data)  # Update local state with room data
            st.session_state.game_state['room_id'] = room_id_input
            st.session_state.game_state['game_mode'] = 'player'
            st.session_state.game_state['player_role'] = 'joiner'
            st.session_state.game_state['message'] = f"Successfully joined room: {room_id_input}!"
        else:
            st.session_state.game_state['message'] = "Room does not exist. Please check the ID or create a new one."
            st.session_state.game_state['room_id'] = None  # Clear invalid room ID
    except Exception as e:
        st.session_state.game_state['message'] = f"Error joining room: {e}"
        st.error(f"Error joining room: {e}")
    st.rerun()


# --- Streamlit UI Layout ---

st.set_page_config(layout="centered", page_title="Tic Tac Total")

st.markdown("""
    <style>
    .main {
        background: linear-gradient(to bottom right, #4B0082, #4682B4); /* Dark purple to steel blue */
        color: white;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        background-color: #6A5ACD; /* Slate Blue */
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 20px;
        font-size: 18px;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #7B68EE; /* Medium Slate Blue */
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    .stButton>button:active {
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .board-cell {
        background-color: #2C3E50; /* Dark Blue Gray */
        border: 2px solid #34495E; /* Darker Blue Gray */
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3em;
        font-weight: bold;
        color: #ECF0F1; /* Light Gray */
        height: 100px; /* Fixed height for cells */
        width: 100%; /* Make width responsive within column */
    }
    .board-cell-empty {
        background-color: #34495E; /* Darker Blue Gray */
        cursor: pointer;
    }
    .board-cell-empty:hover {
        background-color: #4A647A; /* Slightly lighter on hover */
    }
    .number-button {
        background-color: #1ABC9C; /* Turquoise */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 15px;
        font-size: 24px;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease-in-out;
    }
    .number-button:hover {
        background-color: #16A085; /* Darker Turquoise */
        transform: translateY(-1px);
    }
    .number-button-selected {
        background-color: #F39C12; /* Orange */
        color: white;
        border: 3px solid #E67E22; /* Darker Orange */
        transform: scale(1.05);
    }
    .number-button-used {
        background-color: #7F8C8D; /* Gray */
        color: #BDC3C7; /* Lighter Gray */
        cursor: not-allowed;
    }
    .stTextInput>div>div>input {
        background-color: #34495E;
        color: white;
        border: 1px solid #2C3E50;
        border-radius: 8px;
        padding: 10px;
    }
    .stSelectbox>div>div {
        background-color: #34495E;
        color: white;
        border-radius: 8px;
    }
    .stSelectbox>div>div>div {
        color: white;
    }
    h1 {
        color: #FFD700; /* Gold */
        text-align: center;
        font-size: 3em;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Tic Tac Total")

# Display current message
if st.session_state.game_state['message']:
    st.info(st.session_state.game_state['message'])

# Game Mode Selection
game_mode_options = ["Play Against Computer", "Play Against Player"]
selected_game_mode = st.selectbox("Select Game Mode:", game_mode_options,
                                  index=0 if st.session_state.game_state['game_mode'] == 'computer' else 1)

# Update game mode in session state if changed
if selected_game_mode == "Play Against Player" and st.session_state.game_state['game_mode'] == 'computer':
    st.session_state.game_state['game_mode'] = 'player'
    st.session_state.game_state['message'] = 'Multiplayer mode selected. Create or join a room.'
    reset_game()  # Reset game when switching modes
elif selected_game_mode == "Play Against Computer" and st.session_state.game_state['game_mode'] == 'player':
    st.session_state.game_state['game_mode'] = 'computer'
    st.session_state.game_state['room_id'] = None  # Clear room ID for single player
    st.session_state.game_state['player_role'] = None
    st.session_state.game_state['message'] = 'Single player mode selected.'
    reset_game()  # Reset game when switching modes

# Multiplayer Room Management
if st.session_state.game_state['game_mode'] == 'player':
    st.subheader("Multiplayer Room")
    if not st.session_state.game_state['room_id']:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create New Room", key="create_room_btn"):
                create_room()
        with col2:
            room_id_input = st.text_input("Enter Room ID to Join:", key="room_id_input")
            if st.button("Join Room", key="join_room_btn"):
                join_room(room_id_input)
    else:
        st.write(f"**Current Room ID:** `{st.session_state.game_state['room_id']}`")
        if st.session_state.game_state['player_role']:
            st.write(f"**Your Role:** `{st.session_state.game_state['player_role']}`")

        # Add a sync button for multiplayer to manually fetch latest state
        if st.button("Sync Game State", key="sync_game_state_btn"):
            get_firebase_game_state()

# Display current player and game status
if st.session_state.game_state['winner']:
    st.success(st.session_state.game_state['winner'])
else:
    st.write(f"**Current Player:** {st.session_state.game_state['current_player']}")

# Number selection for Player 1 (or Host in multiplayer)
# Only allow number selection if it's Player 1's turn and no winner
is_player_1_turn = st.session_state.game_state['current_player'] == 'Player 1'
is_host_turn_in_multiplayer = (st.session_state.game_state['game_mode'] == 'player' and
                               st.session_state.game_state['player_role'] == 'host' and
                               st.session_state.game_state['current_player'] == 'Player 1')
is_joiner_turn_in_multiplayer = (st.session_state.game_state['game_mode'] == 'player' and
                                 st.session_state.game_state['player_role'] == 'joiner' and
                                 st.session_state.game_state['current_player'] == 'Player 2')

if not st.session_state.game_state['winner']:
    if (st.session_state.game_state['game_mode'] == 'computer' and is_player_1_turn) or \
            (st.session_state.game_state['game_mode'] == 'player' and is_host_turn_in_multiplayer) or \
            (st.session_state.game_state['game_mode'] == 'player' and is_joiner_turn_in_multiplayer):

        st.subheader("Select a number:")
        num_cols = st.columns(3)  # Create 3 columns for number buttons
        available_numbers = [num for num in range(1, 10) if num not in st.session_state.game_state['used_numbers']]

        for i, num in enumerate(range(1, 10)):
            with num_cols[i % 3]:  # Distribute buttons across 3 columns
                is_used = num not in available_numbers
                is_selected = st.session_state.game_state['selected_number'] == num

                button_class = "number-button"
                if is_used:
                    button_class += " number-button-used"
                elif is_selected:
                    button_class += " number-button-selected"

                # Using Streamlit's native button for functionality
                if st.button(str(num), key=f"select_{num}",
                             on_click=select_number, args=(num,),
                             disabled=is_used or st.session_state.game_state['winner'] is not None):
                    pass  # The on_click handles the state update

# Game Board Display
st.subheader("Game Board")
board_cols = st.columns(3)  # Create 3 columns for the board

for i in range(3):  # Rows
    with board_cols[i]:  # Each column represents a row in this layout
        for j in range(3):  # Cells in each row
            index = i * 3 + j
            cell_value = st.session_state.game_state['board'][index]

            # Determine if the cell is clickable
            is_clickable = cell_value is None and \
                           st.session_state.game_state['selected_number'] is not None and \
                           st.session_state.game_state['winner'] is None and \
                           (
                                   (st.session_state.game_state['game_mode'] == 'computer' and
                                    st.session_state.game_state['current_player'] == 'Player 1') or
                                   (st.session_state.game_state['game_mode'] == 'player' and
                                    st.session_state.game_state['player_role'] == 'host' and
                                    st.session_state.game_state['current_player'] == 'Player 1') or
                                   (st.session_state.game_state['game_mode'] == 'player' and
                                    st.session_state.game_state['player_role'] == 'joiner' and
                                    st.session_state.game_state['current_player'] == 'Player 2')
                           )

            if st.button(str(cell_value) if cell_value is not None else ' ',
                         key=f"board_{index}",
                         on_click=make_move, args=(index,),
                         disabled=not is_clickable,
                         help="Click to place your selected number" if is_clickable else ""):
                pass  # The on_click handles the state update

# Reset Game Button
if st.button("Reset Game", key="reset_game_btn"):
    reset_game()
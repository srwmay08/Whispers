# main.py
# mud_project/main.py
import os
import sys
import time
import threading
import random
import traceback
import datetime
import pytz
import math # Ensure math is imported
import re

# Ensure the project directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

try:
    import config
    from database import connection as db_connection
    from database import player_handler
    from classes import player as player_class # Ensure this alias is used if Player class is named Player
    from database import data_loader
    from game_logic import character_creation
    from game_logic import combat
    from game_logic import environment as environment_system
    from game_logic import monster_respawn as respawn_system
    from game_logic import loot_handler
except ImportError as e:
    print(f"ERROR: Critical module import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- Global Variable Initializations ---
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
# Consider async_mode='eventlet' or 'gevent' for production if threading causes issues.
# For development, 'threading' is often fine.
socketio = SocketIO(app, async_mode='threading')

active_players = {} # Stores active Player objects, keyed by SID
player_creation_sessions = {} # Stores temporary data for clients in creation/login phase, keyed by SID

# Game Data Dictionaries (populated by data_loader)
GAME_ROOMS = {}
GAME_ITEMS = {}
GAME_NPCS = {}
GAME_MONSTER_TEMPLATES = {}
GAME_RACES = {}
GAME_LOOT_TABLES = {}
GAME_EQUIPMENT_TABLES = {}

TRACKED_DEFEATED_ENTITIES = {} # For monster/NPC respawn tracking
ENTITY_COMBAT_PARTICIPANTS = {} # Tracks entities currently engaged in combat AI

game_tick_counter = 0
game_loop_active = True # Flag to control the game tick loop thread

# --- HELPER FUNCTION DEFINITIONS ---

def get_opposite_direction(direction: str) -> str:
    """Returns the opposite direction string for arrival messages."""
    direction_lower = str(direction).lower()
    opposites = {
        "north": "the south", "south": "the north", "east": "the west", "west": "the east",
        "up": "below", "down": "above", "northeast": "the southwest",
        "northwest": "the southeast", "southeast": "the northwest", "southwest": "the northeast",
        "in": "out", "out": "in"
    }
    return opposites.get(direction_lower, f"another direction ({direction_lower})")

def send_player_stats_update(player_object: player_class.Player):
    """Sends the player's current stats to their client."""
    if player_object and hasattr(player_object, 'sid') and player_object.sid:
        try:
            # Ensure get_client_data can handle potentially missing GAME_RACES or GAME_ITEMS if called early
            client_data = {"raw_stats": player_object.get_client_data(GAME_RACES, GAME_ITEMS)}
            socketio.emit('stats_update', client_data, room=player_object.sid)
        except Exception as e:
            print(f"Error sending stats update for SID {player_object.sid}: {e}")
            traceback.print_exc()

def broadcast_to_room(room_id, message_text, message_type="ambient_other_player", exclude_sids=None):
    """Broadcasts a message to all players in a specific room, optionally excluding some SIDs."""
    if exclude_sids is None:
        exclude_sids = []
    try:
        room_id_int = int(room_id)
    except ValueError:
        if config.DEBUG_MODE:
            print(f"DEBUG BROADCAST_TO_ROOM: Invalid room_id format '{room_id}'. Cannot broadcast.")
        return

    # Iterate over a copy of items if active_players can be modified during iteration elsewhere
    for sid_broadcast, player_obj_broadcast in list(active_players.items()):
        if hasattr(player_obj_broadcast, 'current_room_id') and \
           player_obj_broadcast.current_room_id == room_id_int and \
           sid_broadcast not in exclude_sids:
            player_obj_broadcast.add_message(message_text, message_type)

def send_room_description(player_object: player_class.Player):
    """Sends the current room's description and details to the player."""
    if not player_object or not hasattr(player_object, 'sid'):
        return

    current_room_id = getattr(player_object, 'current_room_id', config.DEFAULT_START_ROOM_ID)
    if not isinstance(current_room_id, int): # Ensure current_room_id is an integer
        try:
            current_room_id = int(current_room_id)
        except ValueError: # If conversion fails, default to start room
            current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        player_object.current_room_id = current_room_id # Update player object

    room_data = GAME_ROOMS.get(current_room_id)

    if not room_data:
        player_object.add_message(f"Error: You are in an unknown room (ID: {current_room_id})! Moving to safety...", "error_critical")
        player_object.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        if player_handler: # Save player after moving them to a safe room
            player_handler.save_player(player_object)
        room_data = GAME_ROOMS.get(player_object.current_room_id)
        if not room_data: # If default room is also invalid, this is a critical setup error
            player_object.add_message({"text": "Lost in the void. The world unravels. Contact an admin.", "type": "error_critical"})
            # Consider disconnecting the player or other critical error handling
            return

    # Get base or environmentally modified description
    final_room_description = environment_system.get_description_for_room(room_data)
    all_present_names = []

    # Gather names of other players in the room
    for sid, p_other in active_players.items():
        if hasattr(p_other, 'current_room_id') and p_other.current_room_id == current_room_id and sid != player_object.sid:
            all_present_names.append(p_other.name)

    # Gather names of NPCs in the room (not recently defeated)
    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template and not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key):
            all_present_names.append(npc_template.get("name", npc_key))

    # Gather names of Monsters in the room (not recently defeated)
    monster_names_list_for_room_desc = []
    for i, monster_template_key in enumerate(room_data.get("monsters", [])):
        monster_template = GAME_MONSTER_TEMPLATES.get(monster_template_key)
        if monster_template:
            # Conceptual runtime ID for checking defeat status
            conceptual_runtime_id_for_check = f"{current_room_id}_{monster_template_key}_{i}"
            if not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(conceptual_runtime_id_for_check):
                monster_names_list_for_room_desc.append(monster_template.get("name", "a creature"))
    if monster_names_list_for_room_desc:
        all_present_names.extend(monster_names_list_for_room_desc)

    all_present_names.sort()
    present_entities_str = "ALSO HERE: " + ", ".join(all_present_names) + "." if all_present_names else ""

    # Gather names of visible items on the ground
    visible_item_names = []
    # Static items from room definition
    for item_id_static in room_data.get("items", []):
        item_tpl_static = GAME_ITEMS.get(item_id_static)
        if item_tpl_static:
            visible_item_names.append(item_tpl_static.get("name", item_id_static))
    # Dynamic items (corpses, dropped items) from room's "objects"
    for obj_id_dyn, obj_data_dynamic in room_data.get("objects", {}).items():
        if obj_data_dynamic.get("is_corpse") or obj_data_dynamic.get("is_ground_item"):
            visible_item_names.append(obj_data_dynamic.get("name", "an object"))

    items_on_ground_str = ""
    if visible_item_names:
        sorted_unique_items = sorted(list(set(visible_item_names)))
        items_on_ground_str = "YOU ALSO SEE: " + ", ".join(sorted_unique_items) + "."
    else:
        items_on_ground_str = "YOU ALSO SEE: (nothing)"

    # Construct the payload for the client
    room_data_payload = {
        "name": room_data.get("name", "Nowhere Special"),
        "description": final_room_description,
        "presence_summary": present_entities_str,
        "items_summary": items_on_ground_str,
        "exits": ", ".join(k.upper() for k in room_data.get("exits", {}).keys()) or "None",
        "type": "room_data_update" # Client uses this type to handle the payload
    }
    player_object.add_message(room_data_payload)


def add_item_object_to_room(room_data, item_id, game_items_data):
    """Adds a dynamic item object (e.g., dropped item) to the room's 'objects' list."""
    item_template = game_items_data.get(item_id)
    if not item_template:
        if config.DEBUG_MODE: print(f"DEBUG ADD_ITEM_TO_ROOM: Item template for '{item_id}' not found.")
        return None

    # Create a unique ID for this instance of the item on the ground
    ground_item_instance_id = f"ground_{item_id}_{int(time.time())}_{random.randint(1000,9999)}"

    item_object_data = {
        "id": ground_item_instance_id,
        "item_template_id": item_id, # Store the original template ID
        "name": item_template.get("name", item_id),
        "description": item_template.get("look_description_ground", item_template.get("description", "An item lies here.")),
        "keywords": list(set(item_template.get("keywords", []) + [item_template.get("name", item_id).lower(), item_id.lower()])),
        "is_ground_item": True,
        "is_container": item_template.get("is_container", False),
        "inventory": list(item_template.get("inventory", [])) if item_template.get("is_container") else [], # Copy inventory if it's a container
        "created_at": time.time() # For potential decay or other time-based logic
    }

    room_data.setdefault("objects", {})[ground_item_instance_id] = item_object_data
    if config.DEBUG_MODE:
        print(f"DEBUG ADD_ITEM_TO_ROOM: Added '{item_object_data['name']}' (ID: {ground_item_instance_id}) to room {room_data.get('id', 'UNKNOWN_ROOM_ID')}.")
    return item_object_data

def find_combat_target_in_room(player_object: player_class.Player, target_name_query: str, room_data: dict):
    """Finds a combat target (player, NPC, or monster) in the room based on query."""
    if not target_name_query: return None, None, None, None
    target_name_lower = target_name_query.lower()
    current_room_id = player_object.current_room_id
    if not isinstance(current_room_id, int): # Ensure room ID is int for comparisons
        try: current_room_id = int(current_room_id)
        except ValueError: current_room_id = 0 # Or handle error appropriately

    # Priority 1: Find other players
    for other_sid, other_player_obj in active_players.items():
        if other_sid != player_object.sid and \
           hasattr(other_player_obj, 'current_room_id') and other_player_obj.current_room_id == current_room_id and \
           hasattr(other_player_obj, 'name') and other_player_obj.name.lower() == target_name_lower:
            # Target is player obj, type, sid, full_match_data (None for players)
            return other_player_obj, "player", other_player_obj.sid, None

    # Priority 2: Find NPCs
    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template:
            name_lower = npc_template.get("name", "").lower()
            keywords = [k.lower() for k in npc_template.get("keywords", [])]
            partial_name_match = any(part == target_name_lower for part in name_lower.split())

            if name_lower == target_name_lower or target_name_lower in keywords or \
               npc_key.lower() == target_name_lower or partial_name_match:
                if combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key): # Check if NPC is defeated
                    if config.DEBUG_MODE: print(f"DEBUG TARGETING: NPC '{npc_key}' is recently defeated. Skipping.")
                    continue
                # Key is runtime_id for NPCs
                return npc_template, "npc", npc_key, {"runtime_id": npc_key, "template": npc_template}

    # Priority 3: Find Monsters
    query_base_name = target_name_lower
    query_instance_num_str = None
    match_numbered = re.match(r"(.+?)\s*(\d+)$", target_name_lower)
    if match_numbered:
        query_base_name = match_numbered.group(1).strip()
        query_instance_num_str = match_numbered.group(2)

    matching_alive_monsters = []
    current_monster_index_for_naming = {} # For "goblin 1", "goblin 2" if multiple of same base name

    for i, monster_template_key in enumerate(room_data.get("monsters", [])):
        monster_template = GAME_MONSTER_TEMPLATES.get(monster_template_key)
        if not monster_template:
            continue

        monster_runtime_id = f"{current_room_id}_{monster_template_key}_{i}" # Consistent runtime ID

        if combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(monster_runtime_id):
            if config.DEBUG_MODE: print(f"DEBUG TARGETING: Monster '{monster_runtime_id}' is recently defeated. Skipping.")
            continue

        monster_name_lower = monster_template.get("name", "").lower()
        monster_keywords = [k.lower() for k in monster_template.get("keywords", [])]

        if monster_name_lower == query_base_name or \
           query_base_name in monster_keywords or \
           monster_template_key.lower() == query_base_name or \
           any(part == query_base_name for part in monster_name_lower.split()):

            current_monster_index_for_naming[monster_name_lower] = current_monster_index_for_naming.get(monster_name_lower, 0) + 1
            instance_num_assigned = current_monster_index_for_naming[monster_name_lower]

            matching_alive_monsters.append({
                "template": monster_template,
                "type": "monster",
                "key": monster_template_key, # Original template key
                "runtime_id": monster_runtime_id,
                "instance_num_in_room_for_targeting": instance_num_assigned,
                "original_index_in_room_list": i
            })

    if not matching_alive_monsters:
        return None, None, None, None

    if query_instance_num_str: # If "goblin 2" was queried
        target_instance_num = int(query_instance_num_str)
        for m_match in matching_alive_monsters:
            if m_match["instance_num_in_room_for_targeting"] == target_instance_num:
                return m_match["template"], m_match["type"], m_match["key"], m_match
        return None, None, None, None # Specific numbered instance not found
    else: # No number specified, return the first match
        m_match = matching_alive_monsters[0]
        return m_match["template"], m_match["type"], m_match["key"], m_match

    return None, None, None, None # Should not be reached if logic above is correct

def find_object_in_room(player_obj, target_name_query: str, room_data_dict: dict):
    """Finds an object (item on ground, corpse, room feature) in the room."""
    if not target_name_query or not room_data_dict: return None, None
    target_lower = target_name_query.lower()

    # Priority 1: Dynamic Room Objects (corpses, items on ground from room_data["objects"])
    for obj_id, obj_data in room_data_dict.get("objects", {}).items():
        obj_name_lower = obj_data.get("name", "").lower()
        obj_keywords = [k.lower() for k in obj_data.get("keywords", [])]

        if obj_name_lower == target_lower or target_lower in obj_keywords:
            return obj_id, obj_data
        if obj_data.get("is_corpse"):
            original_name = obj_data.get("original_name", "").lower()
            if target_lower == "corpse" or target_lower == original_name or target_lower in original_name.split():
                return obj_id, obj_data
        if obj_data.get("is_ground_item"):
            item_template_id = obj_data.get("item_template_id", "").lower()
            if target_lower == item_template_id:
                return obj_id, obj_data

    # Priority 2: Static items in room (room_data["items"])
    for item_id_static in room_data_dict.get("items", []):
        item_template = GAME_ITEMS.get(item_id_static)
        if item_template:
            item_name_lower = item_template.get("name", "").lower()
            item_keywords = [k.lower() for k in item_template.get("keywords", [])]
            if item_name_lower == target_lower or target_lower in item_keywords or item_id_static.lower() == target_lower:
                return item_id_static, {
                    "id": item_id_static, "name": item_template.get("name"),
                    "description": item_template.get("description", "It's an item."),
                    "is_static_item": True, "keywords": item_keywords,
                    "item_template_id": item_id_static
                }

    # Priority 3: Defined Room Features (e.g., "well", "notice_board" from room_data["objects"])
    for obj_id, obj_data in room_data_dict.get("objects", {}).items():
        if not obj_data.get("is_corpse") and not obj_data.get("is_ground_item"): # If it's a feature
            obj_name_lower = obj_data.get("name", "").lower()
            obj_keywords = [k.lower() for k in obj_data.get("keywords", [])]
            if obj_name_lower == target_lower or target_lower in obj_keywords or obj_id.lower() == target_lower:
                return obj_id, obj_data

    return None, None


def finalize_character_creation(sid, player_shell: player_class.Player, game_races_data: dict, game_items_data: dict):
    """Finalizes character creation, saves the player, and adds them to active players."""
    session = player_creation_sessions.get(sid) # Should exist at this point

    if not player_shell:
        if sid: # Ensure sid is valid before emitting
            emit('game_messages', {'messages': [{"text": "Error: Character data lost during finalization.", "type": "error_critical"}]}, room=sid)
        if session: # Clean up session if it still exists
            player_creation_sessions.pop(sid, None)
        if config.DEBUG_MODE: print(f"ERROR FINALIZE: player_shell is None for SID {sid}.")
        return

    race_key = player_shell.race
    race_data = game_races_data.get(race_key)

    if race_data:
        # Apply racial skill bonuses
        if not hasattr(player_shell, 'skills'): # Should be initialized in Player class constructor
            player_shell.skills = getattr(config, 'INITIAL_SKILLS', {}).copy()
        for skill, bonus in race_data.get("skill_bonuses", {}).items():
            player_shell.skills[skill] = player_shell.skills.get(skill, 0) + bonus

        # Apply racial bonus inventory
        if not hasattr(player_shell, 'inventory'): # Should be initialized
            player_shell.inventory = []
        for item_key_inv in race_data.get("bonus_inventory", []):
            if item_key_inv in game_items_data:
                player_shell.inventory.append(item_key_inv)
            elif config.DEBUG_MODE:
                print(f"DEBUG FINALIZE: Bonus inventory item '{item_key_inv}' for race '{race_key}' not in GAME_ITEMS.")

        # Determine starting room
        start_zone_id_from_race = race_data.get("starting_zone_id")
        default_start_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        final_start_room = default_start_room_id

        if start_zone_id_from_race is not None:
            try:
                start_zone_id_int = int(start_zone_id_from_race)
                if start_zone_id_int in GAME_ROOMS: # Check against loaded game rooms
                    final_start_room = start_zone_id_int
                else:
                    player_shell.add_message(f"Race starting area ID '{start_zone_id_from_race}' unknown; using default room {default_start_room_id}.", "system_warning")
            except ValueError:
                player_shell.add_message(f"Race starting area ID '{start_zone_id_from_race}' is not a valid number; using default room {default_start_room_id}.", "system_warning")
        player_shell.current_room_id = final_start_room
    else: # No race data found for the player's chosen race
        player_shell.add_message(f"Error: Race data for '{race_key}' not found. Using default start room.", "error_critical")
        player_shell.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)

    # Calculate derived stats (Max HP/MP/SP etc.) AFTER race is set and base stats are assigned
    if hasattr(player_shell, 'calculate_derived_stats'):
        player_shell.calculate_derived_stats(game_races_data, game_items_data)

    # Set current HP/MP/SP to their new maximums
    player_shell.hp = getattr(player_shell, 'max_hp', 10)
    player_shell.mp = getattr(player_shell, 'max_mp', 0)
    player_shell.sp = getattr(player_shell, 'max_sp', 0)

    # Calculate training points
    if hasattr(player_shell, 'calculate_training_points'):
        player_shell.calculate_training_points(game_races_data)

    player_shell.creation_phase = None # Mark creation as fully complete on the player object

    if player_handler and player_handler.save_player(player_shell):
        active_players[sid] = player_shell # Add to active players
        if session: # Clean up the creation session
            player_creation_sessions.pop(sid, None)

        player_shell.add_message(f"Character {player_shell.name} created successfully!", "event_highlight")
        broadcast_to_room(player_shell.current_room_id, f"{player_shell.name} appears.", "ambient_player_arrival", exclude_sids=[sid])
        send_room_description(player_shell) # Send initial room description

        # Send all queued messages for the player, then stats
        final_messages = player_shell.get_queued_messages()
        if final_messages:
            emit('game_messages', {'messages': final_messages}, room=sid)
        send_player_stats_update(player_shell) # Send initial stats
        if config.DEBUG_MODE:
            print(f"DEBUG FINALIZE: Character '{player_shell.name}' (SID: {sid}) finalized and added to active_players.")
    else: # Failed to save
        error_msg = "A critical error occurred saving your character after creation."
        player_shell.add_message(error_msg, "error_critical")
        # Still send messages even if save failed, so user sees the error
        error_messages_on_save_fail = player_shell.get_queued_messages()
        if error_messages_on_save_fail:
             emit('game_messages', {'messages': error_messages_on_save_fail}, room=sid)
        # Do not remove from player_creation_sessions here if save failed, player might be stuck
        # Or, disconnect them. For now, they'll get the error.
        if config.DEBUG_MODE: print(f"ERROR FINALIZE: Failed to save player '{player_shell.name}' (SID: {sid}).")


# --- Socket.IO Event Handlers ---

@socketio.on('connect')
def handle_connect(*args):
    sid = request.sid
    if config.DEBUG_MODE:
        print(f"DEBUG: Client connected: SID {sid}")
        if args and any(arg is not None for arg in args): # Check if any actual auth data was passed
            print(f"DEBUG: handle_connect received args: {args}")

    player_creation_sessions[sid] = {
        "phase": "awaiting_login_name",
        "sid": sid,
        "messages_queue": [],
        "player_shell": None
    }
    try:
        emit('game_messages', {
            'messages': [
                {"text": getattr(config, 'WELCOME_MESSAGE', "Welcome!"), "type": "system_highlight"},
                {"text": "Enter 'login <name>' or 'create <name>'", "type": "prompt"}
            ]
        }, room=sid)
        if config.DEBUG_MODE:
            print(f"DEBUG: Emitted initial game_messages to SID {sid}")
    except Exception as e_emit:
        print(f"ERROR: Failed to emit initial messages to SID {sid}. Error: {e_emit}")
        if sid in player_creation_sessions:
            del player_creation_sessions[sid]

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    player = active_players.get(sid)
    if player:
        last_room_id = player.current_room_id
        if player_handler and player_handler.save_player(player):
            if config.DEBUG_MODE: print(f"DEBUG: Player {player.name} ({sid}) data saved on disconnect.")
        else:
            print(f"ERROR: Save failed for {player.name} ({sid}) on disconnect.")
        
        active_players.pop(sid, None) # Remove from active players
        if config.DEBUG_MODE: print(f"DEBUG: Player '{player.name}' ({sid}) removed from active players.")
        broadcast_to_room(last_room_id, f"{player.name} vanished.", "ambient_player_departure", exclude_sids=[sid])

    if sid in player_creation_sessions: # Also clean up if they disconnect during creation
        player_creation_sessions.pop(sid, None)
        if config.DEBUG_MODE: print(f"DEBUG: Player creation session for SID {sid} cleared on disconnect.")
    
    if config.DEBUG_MODE: print(f"DEBUG: Client SID {sid} session fully closed after disconnect.")


@socketio.on('player_command')
def handle_player_command(data):
    sid = request.sid
    command_input = data.get('command', '').strip()

    if config.DEBUG_MODE:
        print(f"\nDEBUG CMD: SID={sid}, Command='{command_input}'")
    if not command_input:
        return

    try:
        player = active_players.get(sid)
        session = player_creation_sessions.get(sid)

        if player: # Player is already logged in and active
            player.add_message(f"> {command_input}", "echo")

            if hasattr(player, 'next_action_time') and time.time() < player.next_action_time:
                player.add_message(f"Wait {max(0.0, round(player.next_action_time - time.time(), 1))}s.", "error_rt")
            else:
                room_id_before_move = player.current_room_id
                current_room_data = GAME_ROOMS.get(room_id_before_move)
                action_taken = False
                command_lower = command_input.lower()

                if not current_room_data:
                    player.add_message(f"Error: You are in an unknown room (ID: {room_id_before_move})! Moving to safety...", "error_critical")
                    player.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
                    if player_handler: player_handler.save_player(player)
                    current_room_data = GAME_ROOMS.get(player.current_room_id)
                    if not current_room_data:
                        player.add_message("PANIC: Default room is also invalid. Contact admin.", "error_critical")
                        all_msgs_panic = player.get_queued_messages()
                        if all_msgs_panic: socketio.emit('game_messages', {'messages': all_msgs_panic}, room=sid)
                        return
                    send_room_description(player)

                # --- Custom Object Actions (from room definition) ---
                if current_room_data and not action_taken:
                    for obj_id, obj_data in current_room_data.get("objects", {}).items():
                        if obj_data.get("interactable") and isinstance(obj_data.get("actions"), dict):
                            for action_phrase, action_result in obj_data["actions"].items():
                                if command_lower == action_phrase.lower():
                                    action_taken = True
                                    if isinstance(action_result, int): # Move to room ID
                                        player.add_message(f"You {action_phrase}...", "feedback_action")
                                        broadcast_to_room(room_id_before_move, f"{player.name} {action_phrase}.", "ambient_other_player", [sid])
                                        player.current_room_id = action_result
                                        send_room_description(player)
                                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_move', 1.0)
                                    elif isinstance(action_result, str): # Script key
                                        player.add_message(f"You attempt to {action_phrase}. (Action: {action_result} - not fully implemented).", "system_info")
                                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                                    else:
                                        player.add_message(f"You try to {action_phrase}, but nothing specific happens.", "feedback_neutral")
                                    break
                        if action_taken: break
                
                # --- Standard Command Parsing ---
                if not action_taken:
                    parts = command_input.split(" ", 1)
                    verb = parts[0].lower()
                    raw_target_arg = parts[1].strip() if len(parts) > 1 else None
                    target_arg = None

                    if raw_target_arg:
                        if verb == "say": target_arg = raw_target_arg
                        else:
                            look_verbs = ["look", "l", "examine", "ex", "exa"]
                            if verb in look_verbs and raw_target_arg.lower().startswith("at ") and len(raw_target_arg) > 3:
                                target_arg = raw_target_arg[3:].strip()
                            else: target_arg = raw_target_arg
                    
                    if config.DEBUG_MODE: print(f"DEBUG CMD PARSED (Fallback): Verb='{verb}', TargetArg='{target_arg}' (RawInputTarget='{raw_target_arg}')")

                    # --- MOVEMENT (via exit name) ---
                    if current_room_data and verb in current_room_data.get("exits", {}):
                        action_taken = True
                        destination_room_id = current_room_data["exits"][verb]
                        player_name_for_broadcast = player.name if hasattr(player, 'name') else "Someone"
                        player.add_message(f"You move {verb}.", "feedback_move")
                        broadcast_to_room(room_id_before_move, f"{player_name_for_broadcast} leaves heading {verb}.", "ambient_player_departure", [sid])
                        player.current_room_id = destination_room_id
                        new_room_data_check = GAME_ROOMS.get(destination_room_id)
                        if new_room_data_check:
                            broadcast_to_room(destination_room_id, f"{player_name_for_broadcast} arrives from {get_opposite_direction(verb)}.", "ambient_player_arrival", [sid])
                            send_room_description(player)
                        else:
                            player.add_message("You try to move, but the way is blocked.", "error_move"); player.current_room_id = room_id_before_move; send_room_description(player)
                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_move', 0.5)
                    
                    # --- LOOK ---
                    elif verb == "look" or verb == "l" or verb == "examine" or verb == "ex" or verb == "exa":
                        action_taken = True
                        # (Your existing detailed look logic - ensure it's complete)
                        # ...
                        rt_look_cmd = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                        if target_arg and current_room_data:
                            target_entity_data_look, entity_type_look, _, _ = find_combat_target_in_room(player, target_arg, current_room_data)
                            if target_entity_data_look:
                                look_desc_entity = target_entity_data_look.get("look_description", target_entity_data_look.get("description", f"You see {target_entity_data_look.get('name', target_arg)}."))
                                if entity_type_look in ["npc", "monster"] and target_entity_data_look.get("equipped"):
                                    equipped_str_parts_look = [f"<{config.EQUIPMENT_SLOTS.get(slot_key_look, slot_key_look).replace('_', ' ').title()}> {GAME_ITEMS.get(item_id_look,{}).get('name',item_id_look)}" for slot_key_look, item_id_look in target_entity_data_look.get("equipped", {}).items() if item_id_look and GAME_ITEMS.get(item_id_look)]
                                    if equipped_str_parts_look: look_desc_entity += "\nThey are equipped with:\n" + "\n".join(equipped_str_parts_look)
                                player.add_message(look_desc_entity, "feedback_look_target")
                            else: 
                                obj_id_look, obj_data_look = find_object_in_room(player, target_arg, current_room_data)
                                if obj_data_look:
                                    look_desc_obj = obj_data_look.get("description", "You see nothing special about it.")
                                    if obj_data_look.get("is_corpse") and obj_data_look.get("inventory") and not obj_data_look.get("searched_and_emptied", False):
                                        look_desc_obj += " It looks like it might have something on it."
                                    elif obj_data_look.get("is_container") and obj_data_look.get("inventory"):
                                        look_desc_obj += " It contains:\n" + "".join([f"  - {GAME_ITEMS.get(item_id_in_cont, {}).get('name', item_id_in_cont)}\n" for item_id_in_cont in obj_data_look.get("inventory", [])])
                                    player.add_message(look_desc_obj, "feedback_look_target")
                                else: player.add_message(f"You don't see '{target_arg}' here.", "error")
                        else: send_room_description(player) 
                        player.next_action_time = time.time() + rt_look_cmd
                    
                    # --- ATTACK ---
                    elif verb == "attack":
                        action_taken = True
                        # (Your existing detailed attack logic - ensure it's complete)
                        # ...
                        rt_look = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2); rt_attack = config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
                        if not target_arg: player.add_message("Attack whom or what?", "error"); player.next_action_time = time.time() + rt_look
                        elif not current_room_data: player.add_message("You can't attack in the void.", "error"); player.next_action_time = time.time() + rt_look
                        else:
                            target_data, target_type, target_id_or_key, target_full_match_data = find_combat_target_in_room(player, target_arg, current_room_data)
                            if target_data:
                                if target_type == "player":
                                    if not current_room_data.get("pvp", getattr(config, "PVP_ENABLED_ROOM_TAG", False)): player.add_message("PvP is not allowed here.", "error_pvp")
                                    else: player.add_message("PvP combat is not fully implemented.", "system_info")
                                    player.next_action_time = time.time() + rt_attack
                                elif target_type in ["monster", "npc"]:
                                    monster_runtime_id_for_combat = target_id_or_key
                                    if target_type == "monster" and target_full_match_data: monster_runtime_id_for_combat = target_full_match_data.get("runtime_id", target_id_or_key)
                                    combat_results = combat.handle_player_attack(player, target_data, target_type, target_arg, GAME_ITEMS, monster_runtime_id=monster_runtime_id_for_combat)
                                    if combat_results.get('broadcast_message'): broadcast_to_room(player.current_room_id, combat_results['broadcast_message'], "ambient_combat", [player.sid])
                                    if combat_results.get('defeated') and not combat_results.get('already_defeated'):
                                        defeated_runtime_id = combat_results.get('target_runtime_id'); defeated_name = combat_results.get('target_name', 'creature')
                                        if config.DEBUG_MODE: print(f"DEBUG MAIN_DEFEAT: {player.name} def. {defeated_name} (Key:{target_id_or_key}, RuntimeID: {defeated_runtime_id})")
                                        xp_val = target_data.get("xp_value", 0)
                                        if xp_val > 0 and hasattr(player, 'add_xp_to_pool'): player.add_xp_to_pool(xp_val, GAME_RACES)
                                        faction_hits = target_data.get("faction_hits_on_kill", [])
                                        if faction_hits and hasattr(player, 'update_faction'):
                                            for hit in faction_hits: player.update_faction(hit["faction_id"], hit["amount"])
                                        resp_time = target_data.get("respawn_time_seconds", 300)
                                        if "spawn_config" in target_data: resp_time = target_data["spawn_config"].get("respawn_time_seconds", resp_time)
                                        TRACKED_DEFEATED_ENTITIES[defeated_runtime_id] = {"template_key": target_id_or_key, "type": target_type, "room_id": player.current_room_id, "defeated_at": time.time(), "eligible_at": time.time() + resp_time, "chance": target_data.get("respawn_chance", 0.5), "is_unique": target_data.get("is_unique", False), "original_instance_index": target_full_match_data.get("original_index_in_room_list") if target_full_match_data else None}
                                        if config.DEBUG_MODE: print(f"DEBUG RESPAWN_TRACK: Added {defeated_runtime_id}. Eligible at {time.time() + resp_time:.0f}")
                                        if target_data.get("leaves_corpse", True):
                                            corpse_obj = loot_handler.create_corpse_object_data(target_data, defeated_runtime_id, GAME_ITEMS, GAME_EQUIPMENT_TABLES)
                                            if corpse_obj and current_room_data: current_room_data.setdefault("objects", {})[corpse_obj["id"]] = corpse_obj; player.add_message(f"The {defeated_name} slumps, leaving a corpse.", "event_defeat_corpse")
                                    player.next_action_time = time.time() + rt_attack
                                else: player.add_message("You can't attack that!", "error"); player.next_action_time = time.time() + rt_look
                            else: player.add_message(f"You don't see '{target_arg}' to attack.", "error"); player.next_action_time = time.time() + rt_look

                    # --- Other commands like SEARCH, SKIN, GET, EQUIP, UNEQUIP, INVENTORY ---
                    # (Ensure your full logic for these commands is present here)
                    # ...
                    elif verb == "search":
                        action_taken = True; rt_search_default = getattr(config, 'SEARCH_BASE_ROUNDTIME', 1.5); perception_stat = player.stats.get(getattr(config, 'STAT_FOR_SEARCH_TIME_REDUCTION', 'perception'), 0); reduction_per_10_points = getattr(config, 'SEARCH_PERCEPTION_REDUCTION_PER_10POINTS', 0.5); time_reduction = (perception_stat // 10) * reduction_per_10_points; final_search_rt = max(getattr(config, 'SEARCH_MIN_ROUNDTIME_SECONDS', 0.5), rt_search_default - time_reduction); final_search_rt = min(final_search_rt, getattr(config, 'SEARCH_MAX_ROUNDTIME_SECONDS', 5.0))
                        if not target_arg: player.add_message("Search what?", "error")
                        elif not current_room_data: player.add_message("You can't search here.", "error")
                        else:
                            obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data:
                                target_display_name_search = obj_data.get("name", target_arg)
                                if obj_data.get("is_corpse"):
                                    if obj_data.get("searched_and_emptied"): player.add_message(f"The {target_display_name_search} has already been searched.", "feedback_neutral")
                                    else:
                                        corpse_inventory_ids = obj_data.get("inventory", [])
                                        if config.DEBUG_MODE: print(f"DEBUG SEARCH: Corpse inventory IDs: {corpse_inventory_ids}")
                                        
                                        items_moved_to_ground_names = [] 
                                        if corpse_inventory_ids: 
                                            player.add_message(f"You search the {target_display_name_search}...", "feedback_search_corpse"); 
                                            for item_id_on_corpse in list(corpse_inventory_ids): 
                                                if config.DEBUG_MODE: print(f"DEBUG SEARCH: Processing item '{item_id_on_corpse}' from corpse.")
                                                item_object_placed = add_item_object_to_room(current_room_data, item_id_on_corpse, GAME_ITEMS)                                             
                                                if item_object_placed: 
                                                    items_moved_to_ground_names.append(item_object_placed.get("name", item_id_on_corpse))
                                                    if config.DEBUG_MODE: print(f"DEBUG SEARCH: Item '{item_id_on_corpse}' successfully added to room, name '{item_object_placed.get('name')}' added to spill list.")
                                                elif config.DEBUG_MODE: print(f"DEBUG SEARCH: Item '{item_id_on_corpse}' FAILED to be added to room (add_item_object_to_room returned None).")
                                        
                                        obj_data["inventory"] = [] 
                                        
                                        if items_moved_to_ground_names: 
                                            player.add_message("...and its contents spill onto the ground:", "event_highlight");                                             
                                            for name_loot in items_moved_to_ground_names: 
                                                player.add_message(f"- A {name_loot}", "feedback_loot_drop")
                                        elif corpse_inventory_ids and not items_moved_to_ground_names: 
                                            player.add_message("...but find nothing you can retrieve from it.", "feedback_search_empty")
                                            if config.DEBUG_MODE: print(f"DEBUG SEARCH: Corpse had items {corpse_inventory_ids} but items_moved_to_ground_names was empty.")
                                        else: 
                                             player.add_message(f"You search the {target_display_name_search} but find nothing of value.", "feedback_search_empty")
                                        
                                        obj_data["searched_and_emptied"] = True; obj_data["description"] = f"The searched remains of {obj_data.get('original_name', 'a creature')}."
                                        if obj_id in current_room_data.get("objects", {}): del current_room_data["objects"][obj_id];                                             
                                        if config.DEBUG_MODE: print(f"DEBUG SEARCH: Corpse '{obj_id}' removed."); broadcast_to_room(player.current_room_id, f"The {target_display_name_search} crumbles to dust.", "ambient_neutral", [sid])
                                        
                                elif obj_data.get("is_container") and not obj_data.get("is_ground_item"): 
                                    if obj_data.get("searched_and_emptied"): player.add_message(f"The {target_display_name_search} appears empty.", "feedback_neutral")
                                    else: 
                                        container_inv = obj_data.get("inventory", []); items_moved = []
                                        if container_inv: player.add_message(f"You search the {target_display_name_search}...", "feedback_search_corpse")
                                        for item_id_cont in list(container_inv): item_obj_placed = add_item_object_to_room(current_room_data, item_id_cont, GAME_ITEMS);                                         
                                        if item_obj_placed: items_moved.append(item_obj_placed.get("name", item_id_cont))
                                        obj_data["inventory"] = []
                                        if items_moved: player.add_message("...revealing its contents on the ground:", "event_highlight");                                         
                                        for name_loot in items_moved: player.add_message(f"- A {name_loot}", "feedback_loot_drop")
                                        else: player.add_message("...but find nothing retrievable.", "feedback_search_empty")
                                        obj_data["searched_and_emptied"] = True
                                else: player.add_message(f"You find nothing special by searching the {target_display_name_search}.", "feedback_search_empty")
                            else: player.add_message(f"You don't see '{target_arg}' to search here.", "error")
                        player.next_action_time = time.time() + final_search_rt

                    elif verb == "skin":
                        action_taken = True; rt_skin = getattr(config, 'SKIN_BASE_ROUNDTIME', 2.0); player.next_action_time = time.time() + rt_skin
                        if not target_arg: player.add_message("Skin what?", "error")
                        elif not current_room_data: player.add_message("There's nothing here to skin.", "error")
                        else:
                            obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data and obj_data.get("is_corpse"):
                                corpse_name_skin = obj_data.get("name", "corpse")
                                if obj_data.get("skinned"): player.add_message(f"The {corpse_name_skin} has already been skinned.", "feedback_neutral")
                                else:
                                    original_template_key = obj_data.get("original_template_key")
                                    if config.DEBUG_MODE: print(f"DEBUG SKIN: Corpse obj_data: {obj_data}, original_template_key: '{original_template_key}'")
                                    monster_template = None
                                    if original_template_key: monster_template = GAME_MONSTER_TEMPLATES.get(original_template_key)
                                    
                                    if not monster_template: 
                                        player.add_message(f"Error: Could not identify original creature for {corpse_name_skin}.", "error_critical")
                                    elif monster_template.get("skinnable"):
                                        player_skill_value = player.skills.get(monster_template.get("skinning", {}).get("skill_required", "survival"), 0)
                                        if config.DEBUG_MODE: print(f"DEBUG SKIN: Player skill '{monster_template.get('skinning', {}).get('skill_required', 'survival')}' value: {player_skill_value}")
                                        
                                        skinned_item_ids = loot_handler.generate_skinning_loot(monster_template, player_skill_value, GAME_ITEMS)
                                        
                                        if skinned_item_ids:
                                            player.add_message(f"You attempt to skin the {corpse_name_skin}...", "feedback_action")
                                            items_added_to_ground_skin = []
                                            for item_id_skinned in skinned_item_ids:
                                                item_object_placed_skin = add_item_object_to_room(current_room_data, item_id_skinned, GAME_ITEMS)
                                                if item_object_placed_skin:
                                                    items_added_to_ground_skin.append(item_object_placed_skin.get("name", item_id_skinned))
                                                    player.add_message(f"You successfully skin a {item_object_placed_skin.get('name', item_id_skinned)} from the corpse. It falls to the ground.", "feedback_get_item") 
                                                else: 
                                                    player.add_message(f"You skin something, but it vanishes before you can grab it.", "error") 
                                            obj_data["skinned"] = True; obj_data["description"] = f"The skinned remains of {obj_data.get('original_name', 'a creature')}."
                                        else: 
                                            skinning_failure_msg = monster_template.get("skinning",{}).get("failure_message", "You fail to get anything useful from skinning the {monster_name}.")
                                            player.add_message(skinning_failure_msg.format(monster_name=corpse_name_skin), "feedback_neutral")
                                            obj_data["skinned"] = True; obj_data["description"] = f"The mangled remains of {obj_data.get('original_name', 'a creature')} after a failed skinning attempt."
                                    else: 
                                        player.add_message(f"The {corpse_name_skin} is not something you can skin.", "error")
                            else: player.add_message(f"You don't see '{target_arg}' (a skinnable corpse) here.", "error")
                    
                    elif verb in ["get", "take"]:
                        action_taken = True 
                        rt_get_default = getattr(config, 'GET_BASE_ROUNDTIME', 0.5); player.next_action_time = time.time() + rt_get_default
                        if not target_arg: player.add_message(f"{verb.capitalize()} what?", "error")
                        elif not current_room_data: player.add_message("There's nothing here to get.", "error")
                        else:
                            item_name_query_get = target_arg; obj_id_to_get, obj_data_to_get = find_object_in_room(player, item_name_query_get, current_room_data)
                            if obj_data_to_get:
                                item_id_for_inventory = None; item_name_for_message = obj_data_to_get.get('name', 'item'); can_take = False
                                if obj_data_to_get.get("is_ground_item"):
                                    item_id_for_inventory = obj_data_to_get.get("item_template_id")
                                    if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20): player.add_message("Your inventory is full.", "error"); can_take = False
                                    else: can_take = True;                                     
                                    if obj_id_to_get in current_room_data.get("objects", {}): del current_room_data["objects"][obj_id_to_get]
                                    else: 
                                        if config.DEBUG_MODE: print(f"DEBUG GET: Dynamic object {obj_id_to_get} not found in room objects during removal.")
                                        can_take = False 
                                elif obj_data_to_get.get("is_static_item"):
                                    item_id_for_inventory = obj_data_to_get.get("item_template_id") 
                                    if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20): player.add_message("Your inventory is full.", "error"); can_take = False
                                    else: can_take = True;                                     
                                    if item_id_for_inventory in current_room_data.get("items", []): current_room_data["items"].remove(item_id_for_inventory)
                                    else: 
                                        if config.DEBUG_MODE: print(f"DEBUG GET: Static item {item_id_for_inventory} not found in room items during removal.")
                                        can_take = False 
                                else: player.add_message(f"You can't {verb} the {item_name_for_message}.", "error")
                                if can_take and item_id_for_inventory:
                                    player.inventory.append(item_id_for_inventory); player.add_message(f"You pick up the {item_name_for_message}.", "feedback_get_item")
                                    broadcast_to_room(player.current_room_id, f"{player.name} picks up {item_name_for_message}.", "ambient_other_player", [sid])
                                elif can_take and not item_id_for_inventory: player.add_message("Error: Item ID missing for pickup.", "error_critical")
                            else: player.add_message(f"You don't see '{item_name_query_get}' here to {verb}.", "error")

                    elif verb == "equip" or verb == "wear":
                        action_taken = True 
                        rt_equip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0); player.next_action_time = time.time() + rt_equip
                        if not target_arg: player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword mainhand)", "error")
                        else:
                            target_arg_parts = target_arg.split(); item_name_or_id_query_equip = ""; slot_to_equip_to_query = None
                            if len(target_arg_parts) > 1:
                                potential_slot_query = target_arg_parts[-1].lower()
                                if potential_slot_query in config.EQUIPMENT_SLOTS.keys(): slot_to_equip_to_query = potential_slot_query; item_name_or_id_query_equip = " ".join(target_arg_parts[:-1]).lower()
                                else: item_name_or_id_query_equip = target_arg.lower()
                            else: item_name_or_id_query_equip = target_arg.lower()
                            if config.DEBUG_MODE: print(f"DEBUG EQUIP PARSED: Item Query='{item_name_or_id_query_equip}', Slot Query='{slot_to_equip_to_query}'")
                            actual_item_id_to_equip = None
                            if item_name_or_id_query_equip in player.inventory and GAME_ITEMS.get(item_name_or_id_query_equip): actual_item_id_to_equip = item_name_or_id_query_equip
                            if not actual_item_id_to_equip:
                                for item_id_in_inv in player.inventory:
                                    item_template = GAME_ITEMS.get(item_id_in_inv)
                                    if item_template:
                                        item_name_lower = item_template.get("name", "").lower(); item_keywords_lower = [k.lower() for k in item_template.get("keywords", [])]
                                        if item_name_lower == item_name_or_id_query_equip: actual_item_id_to_equip = item_id_in_inv; break
                                        if item_name_or_id_query_equip in item_keywords_lower: actual_item_id_to_equip = item_id_in_inv; break
                                        if item_name_or_id_query_equip in item_name_lower: actual_item_id_to_equip = item_id_in_inv; break
                            if not actual_item_id_to_equip: player.add_message(f"You don't have '{item_name_or_id_query_equip}' in your inventory.", "error")
                            else:
                                final_slot_to_equip = slot_to_equip_to_query
                                if not final_slot_to_equip: 
                                    item_template_for_slot = GAME_ITEMS.get(actual_item_id_to_equip)
                                    if item_template_for_slot:
                                        preferred_slots = item_template_for_slot.get("slot", [])
                                        if not isinstance(preferred_slots, list): preferred_slots = [preferred_slots]
                                        if preferred_slots and preferred_slots[0] in config.EQUIPMENT_SLOTS:
                                            final_slot_to_equip = preferred_slots[0]; player.add_message(f"(Equipping to {config.EQUIPMENT_SLOTS.get(final_slot_to_equip, final_slot_to_equip).replace('_', ' ').title()})", "feedback_neutral")
                                        else: player.add_message(f"{verb.capitalize()} the {GAME_ITEMS.get(actual_item_id_to_equip, {}).get('name', item_name_or_id_query_equip)} where? (e.g., {verb} {item_name_or_id_query_equip} mainhand).", "error")
                                    else: player.add_message("Item error while determining slot.", "error_critical")
                                if final_slot_to_equip:
                                    if final_slot_to_equip not in config.EQUIPMENT_SLOTS: player.add_message(f"'{final_slot_to_equip}' is not a valid equipment slot. Valid slots are: {', '.join(config.EQUIPMENT_SLOTS.keys())}", "error")
                                    elif hasattr(player, 'equip_item'):
                                        success = player.equip_item(actual_item_id_to_equip, final_slot_to_equip, GAME_ITEMS, GAME_RACES)
                                        if success: broadcast_to_room(player.current_room_id, f"{player.name} equips a {GAME_ITEMS.get(actual_item_id_to_equip,{}).get('name','piece of equipment')}.", "ambient_other_player", [sid])
                                    else: player.add_message("Equipment system error.", "error_critical")

                    elif verb == "unequip" or verb == "remove":
                        action_taken = True
                        rt_unequip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                        player.next_action_time = time.time() + rt_unequip
                        if not target_arg:
                            player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword or {verb} mainhand)", "error")
                        else:
                            item_or_slot_query = target_arg.lower()
                            slot_to_unequip_from = None
                            if item_or_slot_query in config.EQUIPMENT_SLOTS.keys():
                                slot_to_unequip_from = item_or_slot_query
                            else: 
                                for slot_key, item_id_val in player.equipped_items.items(): 
                                    if item_id_val: 
                                        item_template = GAME_ITEMS.get(item_id_val)
                                        if item_template:
                                            if item_template.get("name","").lower() == item_or_slot_query or \
                                               item_or_slot_query in [k.lower() for k in item_template.get("keywords",[])] or \
                                               item_id_val.lower() == item_or_slot_query:
                                                slot_to_unequip_from = slot_key
                                                break
                            if slot_to_unequip_from:
                                success = player.unequip_item(slot_to_unequip_from, GAME_ITEMS, GAME_RACES)
                                if success: 
                                    broadcast_to_room(player.current_room_id, f"{player.name} unequips an item.", "ambient_other_player", [sid])
                            else:
                                player.add_message(f"You don't have '{target_arg}' equipped or it's not a valid slot.", "error")
                    
                    elif verb == "inventory" or verb == "i": 
                        action_taken = True 
                        if player.inventory:
                            player.add_message("--- Your Inventory ---", "header_info_block"); item_counts = {}; 
                            for item_id_inv in player.inventory: item_counts[item_id_inv] = item_counts.get(item_id_inv, 0) + 1
                            for item_id_counted, count in sorted(item_counts.items()): 
                                item_template_inv = GAME_ITEMS.get(item_id_counted)
                                display_name = item_template_inv.get("name", item_id_counted) if item_template_inv else item_id_counted
                                player.add_message(f"- {display_name}{f' (x{count})' if count > 1 else ''}", "info_block_content")
                        else: player.add_message("Your inventory is empty.", "feedback_neutral")
                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.1)


                    # --- NO ACTION TAKEN (unknown command for logged-in player) ---
                    if not action_taken:
                        player.add_message(f"You can't seem to '{command_input}' here. (Type 'help' for commands)", "error")
                        player.next_action_time = time.time() + 0.1 # Minimal RT

            # Send all accumulated messages for the player and update their stats on client
            all_msgs = player.get_queued_messages()
            if all_msgs:
                socketio.emit('game_messages', {'messages': all_msgs}, room=sid)
            send_player_stats_update(player)

        elif session: # Player is in character creation or login process
            player_shell = session.get("player_shell")
            current_phase = session.get("phase")

            def send_creation_messages(s_id, sess, p_shell_optional):
                messages_to_client = []
                if "messages_queue" in sess and sess["messages_queue"]:
                    messages_to_client.extend(sess["messages_queue"])
                    sess["messages_queue"] = []
                if p_shell_optional and hasattr(p_shell_optional, "get_queued_messages"):
                    messages_to_client.extend(p_shell_optional.get_queued_messages())
                if messages_to_client:
                    socketio.emit('game_messages', {'messages': messages_to_client}, room=s_id)

            if not player_shell and current_phase == "awaiting_login_name":
                parts_initial = command_input.split(" ", 1)
                verb_initial = parts_initial[0].lower()
                name_arg_initial = parts_initial[1].strip().title() if len(parts_initial) > 1 and parts_initial[1].strip() else ""

                if verb_initial == "create" and name_arg_initial:
                    min_len = getattr(config, 'MIN_CHAR_NAME_LENGTH', 3)
                    max_len = getattr(config, 'MAX_CHAR_NAME_LENGTH', 20)
                    is_valid_name_format = all(c.isalpha() or c.isspace() for c in name_arg_initial) and any(c.isalpha() for c in name_arg_initial.replace(" ",""))
                    if player_handler and player_handler.player_exists(name_arg_initial):
                        session["messages_queue"].append({"text": f"The name '{name_arg_initial}' is already taken.", "type": "error"})
                    elif not (min_len <= len(name_arg_initial) <= max_len and is_valid_name_format):
                        session["messages_queue"].append({"text": f"Name must be {min_len}-{max_len} letters/spaces.", "type": "error"})
                    else:
                        player_shell = player_class.Player(sid, name_arg_initial)
                        session["player_shell"] = player_shell
                        character_creation.start_character_creation(player_shell)
                        session["phase"] = player_shell.creation_phase
                elif verb_initial == "login" and name_arg_initial:
                    if player_handler:
                        loaded_player = player_handler.load_player(name_arg_initial.lower(), sid, GAME_RACES, GAME_ITEMS)
                        if loaded_player:
                            active_players[sid] = loaded_player
                            if sid in player_creation_sessions: player_creation_sessions.pop(sid, None) # Critical: remove from creation
                            loaded_player.add_message(f"Welcome back, {loaded_player.name}!", "event_highlight")
                            broadcast_to_room(loaded_player.current_room_id, f"{loaded_player.name} has reconnected.", "ambient_player_arrival", [sid])
                            send_room_description(loaded_player)
                            all_login_msgs = loaded_player.get_queued_messages() # Get all messages after login success
                            if all_login_msgs: socketio.emit('game_messages', {'messages': all_login_msgs}, room=sid)
                            send_player_stats_update(loaded_player)
                            return # Player is now active, exit this handler for this command
                        else:
                            session["messages_queue"].append({"text": f"Character '{name_arg_initial}' not found.", "type": "error"})
                    else:
                        session["messages_queue"].append({"text": "Login system unavailable.", "type": "error_critical"})
                else:
                    session["messages_queue"].append({"text": "Use 'login <name>' or 'create <name>'.", "type": "prompt"})
                send_creation_messages(sid, session, player_shell)

            elif player_shell: # Creation is in progress (past initial create/login command)
                character_creation.handle_creation_input(player_shell, command_input, player_handler, GAME_RACES)
                if session.get("phase") != player_shell.creation_phase: # Update session phase if changed by handler
                    session["phase"] = player_shell.creation_phase

                if player_shell.creation_phase == "completed":
                    finalize_character_creation(sid, player_shell, GAME_RACES, GAME_ITEMS)
                    # finalize_character_creation handles adding to active_players and removing from sessions
                    return # Creation is complete for this command
                
                send_creation_messages(sid, session, player_shell) # Send updates from this step
            else: # Should not happen: session exists but no player_shell and not awaiting_login_name
                 session["messages_queue"].append({"text": "An unexpected error occurred in character creation. Please reconnect.", "type": "error_critical"})
                 send_creation_messages(sid, session, None)

        else: # No active player and no creation session for this SID (should be rare if connect is robust)
            if config.DEBUG_MODE:
                print(f"DEBUG ERROR: SID {sid} sent command but has no active player or creation session.")
            emit('game_messages', {'messages': [{"text": "Connection error. Please reconnect.", "type": "error_critical"}]}, room=sid)

    except Exception as e:
        print(f"!!! UNHANDLED EXCEPTION IN handle_player_command for SID {sid}, Command: '{command_input}' !!!")
        traceback.print_exc()
        try:
            socketio.emit('game_messages', {'messages': [{"text": "A critical server error occurred processing your command.", "type": "error_critical"}]}, room=sid)
        except Exception as e_emit_critical:
            print(f"CRITICAL: Error emitting critical error message to client {sid}: {e_emit_critical}")


# --- Flask Routes ---
@app.route('/')
def index_page():
    return render_template('index.html')

# --- Game Tick Loop Definition ---
def game_tick_loop():
    global game_tick_counter, game_loop_active, ENTITY_COMBAT_PARTICIPANTS # Ensure globals are accessible

    local_tz = pytz.utc # Default
    try:
        import tzlocal
        local_tz = tzlocal.get_localzone()
    except ImportError:
        if config.DEBUG_MODE: print("WARNING: tzlocal not installed. Falling back to UTC for tick logs.")

    if config.DEBUG_MODE and game_tick_counter == 0:
        print(f"Game tick loop started at {datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')} (UTC: {datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')})")

    while game_loop_active:
        current_tick_start_time = time.monotonic()
        game_time_utc_now = time.time()
        datetime_utc_now_for_log = datetime.datetime.fromtimestamp(game_time_utc_now, tz=pytz.utc)
        datetime_local_now_for_log = datetime_utc_now_for_log.astimezone(local_tz)
        log_time_prefix = f"[{datetime_local_now_for_log.strftime('%Y-%m-%d %H:%M:%S %Z')}] (UTC: {datetime_utc_now_for_log.strftime('%H:%M:%S')}) TICK {game_tick_counter}"

        try: # Wrap major tick operations in try-except
            # Environment Update (Time, Weather)
            environment_system.update_environment_state(game_tick_counter, active_players, GAME_ROOMS, log_time_prefix, broadcast_to_room)

            # Monster/NPC Respawns
            respawn_check_interval = getattr(config, 'MONSTER_RESPAWN_TICK_INTERVAL', 6)
            if game_tick_counter > 0 and game_tick_counter % respawn_check_interval == 0:
                respawn_system.process_respawns(log_time_prefix, game_time_utc_now, TRACKED_DEFEATED_ENTITIES, GAME_ROOMS, GAME_NPCS, GAME_MONSTER_TEMPLATES, broadcast_to_room, combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM, GAME_EQUIPMENT_TABLES, GAME_ITEMS)

            # Corpse Decay
            corpse_decay_interval = getattr(config, 'CORPSE_DECAY_TICK_INTERVAL', 10)
            if game_tick_counter > 0 and game_tick_counter % corpse_decay_interval == 0:
                decay_messages_by_room = loot_handler.process_corpse_decay(GAME_ROOMS, log_time_prefix)
                for room_id_decay, messages_list in decay_messages_by_room.items():
                    for msg_text in messages_list:
                        broadcast_to_room(room_id_decay, msg_text, "ambient_neutral")
            
            # Entity (NPC/Monster) Combat AI Tick
            current_entities_in_combat = list(ENTITY_COMBAT_PARTICIPANTS.keys())
            for entity_runtime_id in current_entities_in_combat:
                combat_state = ENTITY_COMBAT_PARTICIPANTS.get(entity_runtime_id)
                if not combat_state or combat_state.get("target_sid") is None:
                    if config.DEBUG_MODE and combat_state: print(f"DEBUG TICK AI: {entity_runtime_id} in participants but no target_sid. Removing.");
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                    continue

                player_target = active_players.get(combat_state["target_sid"])
                if not player_target or player_target.hp <= 0:
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: Target {combat_state['target_sid']} for {entity_runtime_id} gone/defeated. Removing.");
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                    continue
                
                entity_data = None; entity_type = None; entity_room_id = None
                if entity_runtime_id in GAME_NPCS: # Assuming NPC runtime_id is its key
                    entity_data = GAME_NPCS.get(entity_runtime_id)
                    entity_type = "npc"
                    entity_room_id = player_target.current_room_id # NPCs attack players in their room
                else: # Monster
                    # This part needs to correctly derive monster_template_key and original_index from entity_runtime_id
                    # Example: if entity_runtime_id is "roomID_templateKey_index"
                    try:
                        parts = entity_runtime_id.split('_')
                        m_room_id, m_template_key = parts[0], parts[1] # Simplified, adjust if ID format is different
                        entity_data = GAME_MONSTER_TEMPLATES.get(m_template_key)
                        entity_type = "monster"
                        entity_room_id = int(m_room_id)
                    except (IndexError, ValueError) as e_parse:
                        if config.DEBUG_MODE: print(f"DEBUG TICK AI: Error parsing monster runtime_id '{entity_runtime_id}': {e_parse}");
                        ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                        continue
                
                if not entity_data:
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: Could not find entity_data for {entity_runtime_id}. Removing.");
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                    continue

                if entity_room_id != player_target.current_room_id:
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} no longer in same room as target {player_target.name}. Disengaging.");
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                    continue
                
                if combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(entity_runtime_id):
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} is recently defeated. Removing from combat.");
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                    continue

                if time.time() >= combat_state.get("next_attack_time", 0):
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} ({entity_data.get('name')}) attacking {player_target.name}")
                    attack_results = combat.handle_entity_attack(entity_data, entity_type, entity_runtime_id, player_target, GAME_ITEMS)
                    
                    if attack_results.get("defender_message"):
                        player_target.add_message(attack_results["defender_message"]["text"], attack_results["defender_message"]["type"])
                    if attack_results.get("broadcast_message"):
                        broadcast_to_room(player_target.current_room_id, attack_results["broadcast_message"]["text"], attack_results["broadcast_message"]["type"], [player_target.sid])

                    if attack_results.get("defender_defeated", False):
                        # Player death logic handled by handle_entity_attack or here
                        if config.DEBUG_MODE: print(f"DEBUG TICK AI: Player {player_target.name} defeated by {entity_runtime_id}.")
                        ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                        # Potentially move player, etc.
                    else:
                        base_delay = entity_data.get("attack_delay", 3.0)
                        combat_state["next_attack_time"] = time.time() + random.uniform(base_delay * 0.8, base_delay * 1.2)


            # Player-specific ticks (XP absorption, regeneration, status effects, etc.)
            current_player_sids_for_processing = list(active_players.keys())
            for sid_player_process in current_player_sids_for_processing:
                player_obj_process = active_players.get(sid_player_process)
                if not player_obj_process: continue # Player might have disconnected

                # XP Absorption
                xp_absorption_interval_ticks = getattr(config, 'XP_ABSORPTION_TICKS', 5)
                if game_tick_counter > 0 and game_tick_counter % xp_absorption_interval_ticks == 0:
                    if hasattr(player_obj_process, 'unabsorbed_xp') and player_obj_process.unabsorbed_xp > 0:
                        current_player_room_id = player_obj_process.current_room_id
                        current_player_room_data = GAME_ROOMS.get(current_player_room_id, {})
                        xp_to_absorb_this_event = getattr(config, 'MIN_XP_ABSORBED_PER_EVENT', 1)
                        if hasattr(player_obj_process, 'get_xp_absorption_amount_per_event'):
                            xp_to_absorb_this_event = player_obj_process.get_xp_absorption_amount_per_event(current_player_room_data, GAME_RACES)
                        
                        amount_to_absorb = min(player_obj_process.unabsorbed_xp, xp_to_absorb_this_event)
                        if amount_to_absorb > 0:
                            player_obj_process.xp = getattr(player_obj_process, 'xp', 0) + amount_to_absorb
                            player_obj_process.unabsorbed_xp -= amount_to_absorb
                            player_obj_process.add_message(f"You feel more experienced as knowledge settles in your mind (+{amount_to_absorb} XP).", "xp_absorb")
                            if hasattr(player_obj_process, '_check_and_send_mind_status'):
                                player_obj_process._check_and_send_mind_status(GAME_RACES) # Pass GAME_RACES
                            
                            # Level Up Check
                            xp_needed_config = getattr(config, 'XP_LEVEL_THRESHOLDS', {})
                            xp_needed_for_next_level = xp_needed_config.get(player_obj_process.level + 1, (player_obj_process.level ** 2) * 100 + 100) # Fallback formula
                            if player_obj_process.xp >= xp_needed_for_next_level:
                                player_obj_process.level += 1
                                player_obj_process.add_message(f"**Congratulations! You have reached level {player_obj_process.level}!**", "level_up_major")
                                if hasattr(player_obj_process, 'calculate_derived_stats'):
                                    player_obj_process.calculate_derived_stats(GAME_RACES, GAME_ITEMS)
                                if hasattr(player_obj_process, 'calculate_training_points'):
                                    player_obj_process.calculate_training_points(GAME_RACES)
                                # Refill HP/MP/SP on level up
                                player_obj_process.hp = player_obj_process.max_hp
                                player_obj_process.mp = player_obj_process.max_mp
                                player_obj_process.sp = player_obj_process.max_sp
                                send_player_stats_update(player_obj_process) # Send updated stats
                                if config.DEBUG_MODE: print(f"{log_time_prefix} - LEVEL_UP: Player {player_obj_process.name} reached level {player_obj_process.level}.")

                # Client Tick Markers
                if getattr(config, 'SEND_CLIENT_TICK_MARKERS', False):
                    client_tick_marker_interval = getattr(config, 'CLIENT_TICK_MARKER_INTERVAL', getattr(config, 'XP_ABSORPTION_TICKS', 5))
                    if client_tick_marker_interval > 0 and game_tick_counter > 0 and game_tick_counter % client_tick_marker_interval == 0:
                        player_obj_process.add_message(">", "system_tick_marker")

                # Send queued messages for this player
                messages_to_send = player_obj_process.get_queued_messages()
                if messages_to_send:
                    socketio.emit('game_messages', {'messages': messages_to_send}, room=sid_player_process)

        except Exception as e_tick_processing:
            print(f"!!! ERROR during game tick {game_tick_counter} processing: {e_tick_processing}")
            traceback.print_exc()


        # Calculate sleep time for the tick
        processing_time = time.monotonic() - current_tick_start_time
        tick_interval_from_config = getattr(config, 'TICK_INTERVAL_SECONDS', 6.0)
        sleep_time = tick_interval_from_config - processing_time

        if sleep_time > 0:
            socketio.sleep(sleep_time) # Use socketio.sleep for compatibility with eventlet/gevent
        else:
            if config.DEBUG_MODE and game_tick_counter > 1: # Avoid warning on first tick if setup takes time
                print(f"{log_time_prefix} - WARNING: Tick processing ({processing_time:.3f}s) exceeded interval ({tick_interval_from_config}s).")
            socketio.sleep(0.001) # Minimal sleep to yield control if overrun

        game_tick_counter += 1 # Increment at the end of the loop

    if config.DEBUG_MODE: print(f"Game tick loop stopped at {datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")


# --- Main Execution Block ---
if __name__ == '__main__':
    # Ensure templates directory exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # Create a fallback index.html if it doesn't exist
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write(getattr(config, 'FALLBACK_INDEX_HTML', ""))
        print("WARNING: templates/index.html not found. Created a basic placeholder.")

    mud_name = getattr(config, 'MUD_NAME', 'MUD Server')
    print(f"Starting {mud_name}...")

    # Database connection and initialization
    db_connection.connect_to_mongo()
    print("Initializing DB with defaults if needed...")
    data_loader.initialize_database_with_defaults() # This will check if collections are empty

    # Load all game data into memory
    print("Loading game data into memory...")
    all_loaded_data = data_loader.load_all_game_data()
    GAME_ITEMS = all_loaded_data.get("items", {})
    GAME_LOOT_TABLES = all_loaded_data.get("loot_tables", {})
    GAME_RACES = all_loaded_data.get("races", {})
    GAME_EQUIPMENT_TABLES = all_loaded_data.get("equipment_tables", {})
    GAME_NPCS = all_loaded_data.get("npc_templates", {}) # Already processed with equipment
    GAME_MONSTER_TEMPLATES = all_loaded_data.get("monster_templates", {}) # Already processed
    GAME_ROOMS = all_loaded_data.get("rooms", {})

    # Make loot tables available to the loot_handler module (if it needs direct access)
    loot_handler.GAME_LOOT_TABLES = GAME_LOOT_TABLES

    if config.DEBUG_MODE:
        print(f"DEBUG STARTUP: Loaded {len(GAME_RACES)} races into GAME_RACES.")
        if not GAME_RACES: print("WARNING: GAME_RACES is empty after loading.")
        print(f"DEBUG STARTUP: Loaded {len(GAME_EQUIPMENT_TABLES)} equipment tables.")
    print(f"Loaded: {len(GAME_ROOMS)} Rooms, {len(GAME_ITEMS)} Items, {len(GAME_NPCS)} NPCs, {len(GAME_MONSTER_TEMPLATES)} Monsters, {len(GAME_RACES)} Races, {len(GAME_LOOT_TABLES)} Loot Tables, {len(GAME_EQUIPMENT_TABLES)} Equip Tables.")

    # Start the game tick loop in a separate thread
    print("Starting game tick loop thread...")
    game_tick_thread = threading.Thread(target=game_tick_loop, name="GameTickLoop")
    game_tick_thread.daemon = True # Allow main program to exit even if thread is running
    game_tick_thread.start()

    # Server configuration for Flask/SocketIO
    host_ip = getattr(config, 'HOST', '0.0.0.0')
    port_num = int(getattr(config, 'PORT', 8024))
    debug_flask = getattr(config, 'DEBUG_MODE_FLASK', False) # Separate debug for Flask if needed
    use_reloader_flask = getattr(config, 'FLASK_USE_RELOADER', False) and debug_flask
    
    print(f"MUD server on http://{host_ip}:{port_num} (Flask Debug: {'ON' if debug_flask else 'OFF'}, Reloader: {'ON' if use_reloader_flask else 'OFF'})")

    try:
        # allow_unsafe_werkzeug=True is often needed if use_reloader is True with threading
        socketio.run(app, host=host_ip, port=port_num, debug=debug_flask, use_reloader=use_reloader_flask, allow_unsafe_werkzeug=True if use_reloader_flask else False)
    except KeyboardInterrupt:
        print("\nServer shutting down (KeyboardInterrupt)...")
    except Exception as e:
        print(f"Failed to start server: {e}")
        traceback.print_exc()
    finally:
        print("Attempting graceful shutdown...")
        game_loop_active = False # Signal game loop to stop
        if 'game_tick_thread' in locals() and game_tick_thread.is_alive():
            print("Waiting for game tick loop to stop...")
            # Wait for the tick loop to finish its current tick, plus a small buffer
            game_tick_thread.join(timeout=float(getattr(config, 'TICK_INTERVAL_SECONDS', 6.0)) + 2.0)
            if game_tick_thread.is_alive():
                print("Warning: Game tick loop did not terminate cleanly.")

        # Save active players
        if active_players:
            print(f"Saving data for {len(active_players)} active player(s)...")
            for sid_s, player_s in list(active_players.items()): # Iterate a copy
                if player_handler and hasattr(player_handler, 'save_player'):
                    if player_handler.save_player(player_s):
                        if config.DEBUG_MODE: print(f"DEBUG MAIN_SHUTDOWN: Saved {player_s.name}.")
                    else:
                        print(f"ERROR MAIN_SHUTDOWN: Failed to save {player_s.name}.")
                else:
                     print(f"ERROR MAIN_SHUTDOWN: player_handler or save_player not available for {player_s.name}.")

        # Close database connection
        if db_connection and hasattr(db_connection, 'close_mongo_connection'):
            db_connection.close_mongo_connection()
        else:
            print("WARNING: db_connection or close_mongo_connection not available for graceful shutdown.")
            
        print(f"{mud_name} has shut down gracefully.")


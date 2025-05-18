# main.py
import os
import sys
import time
import threading
import random
import traceback
import datetime
import pytz
import math 
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

try:
    import config
    from database import connection as db_connection
    from database import player_handler
    from classes import player as player_class
    from database import data_loader
    from game_logic import character_creation
    from game_logic import combat # Make sure combat is imported
    from game_logic import environment as environment_system
    from game_logic import monster_respawn as respawn_system
    from game_logic import loot_handler
except ImportError as e:
    print(f"ERROR: Critical module import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, async_mode='threading')

# --- Global Game State Variables ---
active_players = {}
player_creation_sessions = {}

GAME_ROOMS = {}
GAME_ITEMS = {}
GAME_NPCS = {} 
GAME_MONSTER_TEMPLATES = {} 
GAME_RACES = {}
GAME_LOOT_TABLES = {}
GAME_EQUIPMENT_TABLES = {} 

TRACKED_DEFEATED_ENTITIES = {}
# --- NEW: Initialize ENTITY_COMBAT_PARTICIPANTS globally ---
ENTITY_COMBAT_PARTICIPANTS = {} 
# --- END NEW ---

game_tick_counter = 0
game_loop_active = True


# --- game_tick_loop function ---
# (This function was provided in the previous turn with ID: main_py_game_tick_loop_combat_ai)
# Ensure that ENTITY_COMBAT_PARTICIPANTS is correctly used within it.
# The NameError occurred because it was referenced before being assigned globally.
# The definition above this comment block fixes that.
def game_tick_loop():
    global game_tick_counter, active_players, GAME_ROOMS, GAME_ITEMS, GAME_NPCS, \
           GAME_MONSTER_TEMPLATES, GAME_RACES, GAME_LOOT_TABLES, GAME_EQUIPMENT_TABLES, \
           TRACKED_DEFEATED_ENTITIES, ENTITY_COMBAT_PARTICIPANTS, game_loop_active

    local_tz = pytz.utc
    try: import tzlocal; local_tz = tzlocal.get_localzone()
    except ImportError: print("WARNING: tzlocal not installed. Falling back to UTC for logs.")

    if config.DEBUG_MODE and game_tick_counter == 0:
        print(f"Game tick loop started at {datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')} (UTC: {datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')})")

    while game_loop_active:
        current_tick_start_time = time.monotonic()
        game_time_utc_now = time.time()
        datetime_utc_now_for_log = datetime.datetime.fromtimestamp(game_time_utc_now, tz=pytz.utc)
        datetime_local_now_for_log = datetime_utc_now_for_log.astimezone(local_tz)
        log_time_prefix = f"[{datetime_local_now_for_log.strftime('%Y-%m-%d %H:%M:%S %Z')}] (UTC: {datetime_utc_now_for_log.strftime('%H:%M:%S')}) TICK {game_tick_counter}"
        game_tick_counter += 1

        environment_system.update_environment_state(game_tick_counter, active_players, GAME_ROOMS, log_time_prefix, broadcast_to_room)
        respawn_check_interval = getattr(config, 'MONSTER_RESPAWN_TICK_INTERVAL', 6)
        if game_tick_counter > 0 and game_tick_counter % respawn_check_interval == 0:
            respawn_system.process_respawns(log_time_prefix, game_time_utc_now, TRACKED_DEFEATED_ENTITIES, GAME_ROOMS, GAME_NPCS, GAME_MONSTER_TEMPLATES, broadcast_to_room, combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM, GAME_EQUIPMENT_TABLES, GAME_ITEMS)
        
        corpse_decay_interval = getattr(config, 'CORPSE_DECAY_TICK_INTERVAL', 10)
        if game_tick_counter > 0 and game_tick_counter % corpse_decay_interval == 0:
            decay_messages_by_room = loot_handler.process_corpse_decay(GAME_ROOMS, log_time_prefix)
            for room_id_decay, messages_list in decay_messages_by_room.items():
                for msg_text in messages_list: broadcast_to_room(room_id_decay, msg_text, "ambient_neutral")

        # --- Entity (NPC/Monster) Combat AI Tick ---
        current_entities_in_combat = list(ENTITY_COMBAT_PARTICIPANTS.keys()) 
        for entity_runtime_id in current_entities_in_combat:
            combat_state = ENTITY_COMBAT_PARTICIPANTS.get(entity_runtime_id)
            if not combat_state or combat_state.get("target_sid") is None:
                if config.DEBUG_MODE and combat_state: print(f"DEBUG TICK AI: {entity_runtime_id} in combat participants but no target_sid. Removing."); 
                ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                continue

            player_target = active_players.get(combat_state["target_sid"])
            if not player_target or player_target.hp <= 0: 
                if config.DEBUG_MODE: print(f"DEBUG TICK AI: Target {combat_state['target_sid']} for {entity_runtime_id} is gone or defeated. Removing from combat."); 
                ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                continue
            
            entity_data = None; entity_type = None; entity_room_id = None
            
            if entity_runtime_id in GAME_NPCS:
                entity_data = GAME_NPCS.get(entity_runtime_id)
                entity_type = "npc"
                # For NPCs, their current room needs to be tracked if they can move.
                # If they are static, their home_room_id or the room they were spawned in.
                # For now, assume they are in the player's room if they are targeting them.
                entity_room_id = player_target.current_room_id 
            else: 
                # Attempt to find as a monster instance in a room
                # This requires a robust way to map runtime_id to a monster in a room
                # The current method in send_room_description uses room_id + template_key + index
                # We need to ensure consistency or a better lookup method.
                found_monster = False
                for room_id_iter, room_data_iter in GAME_ROOMS.items():
                    for i, mon_key_in_room in enumerate(room_data_iter.get("monsters", [])):
                        # This conceptual_mon_runtime_id must match how it's created when combat starts
                        conceptual_mon_runtime_id = f"{room_id_iter}_{mon_key_in_room}_{i}"
                        if conceptual_mon_runtime_id == entity_runtime_id:
                            entity_data = GAME_MONSTER_TEMPLATES.get(mon_key_in_room)
                            entity_type = "monster"
                            entity_room_id = room_id_iter
                            found_monster = True
                            break
                    if found_monster: break
            
            if not entity_data:
                if config.DEBUG_MODE: print(f"DEBUG TICK AI: Could not find entity_data for {entity_runtime_id}. Removing from combat."); 
                ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                continue

            if entity_room_id != player_target.current_room_id:
                if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} is no longer in the same room as target {player_target.name}. Disengaging."); 
                ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                continue
            
            if combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(entity_runtime_id):
                if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} is recently defeated. Removing from combat."); 
                ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None)
                continue

            if time.time() >= combat_state.get("next_attack_time", 0):
                if config.DEBUG_MODE: print(f"DEBUG TICK AI: {entity_runtime_id} ({entity_data.get('name')}) attacking {player_target.name} (SID: {player_target.sid})")
                
                attack_results = combat.handle_entity_attack(entity_data, entity_type, entity_runtime_id, player_target, GAME_ITEMS)
                
                if attack_results.get("attacker_message") and config.DEBUG_MODE: 
                    print(f"DEBUG ENTITY ATTACK (Self): {entity_runtime_id} - {attack_results['attacker_message']['text']}") # Log entity's own roll
                
                if attack_results.get("defender_message"): 
                    player_target.add_message(attack_results["defender_message"]["text"], attack_results["defender_message"]["type"])
                
                if attack_results.get("broadcast_message"): 
                    broadcast_to_room(player_target.current_room_id, attack_results["broadcast_message"], "ambient_combat", [player_target.sid])

                if attack_results.get("defender_defeated", False):
                    player_target.add_message("You have been struck down!", "event_defeat_major")
                    if config.DEBUG_MODE: print(f"DEBUG TICK AI: Player {player_target.name} defeated by {entity_runtime_id}.")
                    ENTITY_COMBAT_PARTICIPANTS.pop(entity_runtime_id, None) 
                    # TODO: Implement player death (move to death room, XP loss, etc.)
                    # player_target.current_room_id = getattr(config, 'PLAYER_DEATH_ROOM_ID', 1)
                    # player_target.hp = 1 # Or some other logic
                    # send_room_description(player_target)
                    # send_player_stats_update(player_target)

                else:
                    base_delay = entity_data.get("attack_delay", 3.0)
                    combat_state["next_attack_time"] = time.time() + random.uniform(base_delay * 0.8, base_delay * 1.2)
            
        # --- Player-Specific Tick Updates ---
        current_player_sids_for_processing = list(active_players.keys())
        for sid_player_process in current_player_sids_for_processing:
            player_obj_process = active_players.get(sid_player_process)
            if not player_obj_process: continue

            xp_absorption_interval_ticks = getattr(config, 'XP_ABSORPTION_TICKS', 5)
            if game_tick_counter > 0 and game_tick_counter % xp_absorption_interval_ticks == 0:
                if hasattr(player_obj_process, 'unabsorbed_xp') and player_obj_process.unabsorbed_xp > 0:
                    # ... (XP absorption logic - remains the same) ...
                    current_player_room_id = player_obj_process.current_room_id
                    current_player_room_data = GAME_ROOMS.get(current_player_room_id, {})
                    xp_to_absorb_this_event = getattr(config, 'MIN_XP_ABSORBED_PER_EVENT', 1)
                    if hasattr(player_obj_process, 'get_xp_absorption_amount_per_event'):
                        xp_to_absorb_this_event = player_obj_process.get_xp_absorption_amount_per_event(current_player_room_data, GAME_RACES)
                    if config.DEBUG_MODE: print(f"{log_time_prefix} - XP_ABSORB_ATTEMPT: Player {player_obj_process.name} (RoomID: {current_player_room_id}) has {player_obj_process.unabsorbed_xp} UXPs. Attempting to absorb: {xp_to_absorb_this_event} UXPs.")
                    amount_to_absorb = min(player_obj_process.unabsorbed_xp, xp_to_absorb_this_event)
                    if amount_to_absorb > 0:
                        player_obj_process.xp = getattr(player_obj_process, 'xp', 0) + amount_to_absorb
                        player_obj_process.unabsorbed_xp -= amount_to_absorb
                        player_obj_process.add_message(f"You feel more experienced as knowledge settles in your mind (+{amount_to_absorb} XP).", "xp_absorb")
                        if hasattr(player_obj_process, '_check_and_send_mind_status'): player_obj_process._check_and_send_mind_status(GAME_RACES)
                        if config.DEBUG_MODE: print(f"{log_time_prefix} - XP_ABSORBED: Player {player_obj_process.name} absorbed {amount_to_absorb} XP. Total XP: {player_obj_process.xp}, UXPs Pool: {player_obj_process.unabsorbed_xp}")
                        xp_needed_config = getattr(config, 'XP_LEVEL_THRESHOLDS', {})
                        xp_needed_for_next_level = xp_needed_config.get(player_obj_process.level + 1, (player_obj_process.level ** 2) * 100 + 100)
                        if player_obj_process.xp >= xp_needed_for_next_level:
                            player_obj_process.level += 1
                            player_obj_process.add_message(f"**Congratulations! You have reached level {player_obj_process.level}!**", "level_up_major")
                            if hasattr(player_obj_process, 'calculate_derived_stats'): player_obj_process.calculate_derived_stats(GAME_RACES, GAME_ITEMS)
                            if hasattr(player_obj_process, 'calculate_training_points'): player_obj_process.calculate_training_points(GAME_RACES)
                            if hasattr(player_obj_process, 'hp') and hasattr(player_obj_process, 'max_hp'): player_obj_process.hp = player_obj_process.max_hp
                            if hasattr(player_obj_process, 'mp') and hasattr(player_obj_process, 'max_mp'): player_obj_process.mp = player_obj_process.max_mp
                            if hasattr(player_obj_process, 'sp') and hasattr(player_obj_process, 'max_sp'): player_obj_process.sp = player_obj_process.max_sp
                            send_player_stats_update(player_obj_process)
                            if config.DEBUG_MODE: print(f"{log_time_prefix} - LEVEL_UP: Player {player_obj_process.name} reached level {player_obj_process.level}.")


            if getattr(config, 'SEND_CLIENT_TICK_MARKERS', False):
                client_tick_marker_interval = getattr(config, 'CLIENT_TICK_MARKER_INTERVAL', getattr(config, 'XP_ABSORPTION_TICKS', 5))
                if client_tick_marker_interval > 0 and game_tick_counter > 0 and game_tick_counter % client_tick_marker_interval == 0:
                    player_obj_process.add_message(">", "system_tick_marker") 

            messages_to_send = player_obj_process.get_queued_messages()
            if messages_to_send:
                socketio.emit('game_messages', {'messages': messages_to_send}, room=sid_player_process)

        processing_time = time.monotonic() - current_tick_start_time
        tick_interval_from_config = getattr(config, 'TICK_INTERVAL_SECONDS', 6.0)
        sleep_time = tick_interval_from_config - processing_time
        if sleep_time > 0: socketio.sleep(sleep_time)
        else:
            if config.DEBUG_MODE and game_tick_counter > 1: print(f"{log_time_prefix} - WARNING: Tick processing ({processing_time:.3f}s) exceeded interval ({tick_interval_from_config}s).")
            socketio.sleep(0.001)

    if config.DEBUG_MODE: print(f"Game tick loop stopped at {datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")


# --- send_room_description function ---
# (This function was provided in the previous turn with ID: main_py_send_room_description_monster_display)
# Ensure it's correctly implemented to avoid monster numbering.
def send_room_description(player_object: player_class.Player):
    if not player_object or not hasattr(player_object, 'sid'): return
    current_room_id = getattr(player_object, 'current_room_id', config.DEFAULT_START_ROOM_ID)
    if not isinstance(current_room_id, int):
        try: current_room_id = int(current_room_id)
        except ValueError: current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        player_object.current_room_id = current_room_id
    
    room_data = GAME_ROOMS.get(current_room_id)
    if not room_data:
        player_object.add_message(f"Error: You are in an unknown room (ID: {current_room_id})! Moving to safety...", "error_critical")
        player_object.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        if player_handler: player_handler.save_player(player_object)
        room_data = GAME_ROOMS.get(player_object.current_room_id)
        if not room_data:
            player_object.add_message({"name": "Lost", "description": "You are utterly lost. Contact an admin.", "type": "error_critical"})
            return

    final_room_description = environment_system.get_description_for_room(room_data)
    all_present_names = []

    for sid, p in active_players.items():
        if hasattr(p, 'current_room_id') and p.current_room_id == current_room_id and sid != player_object.sid:
            all_present_names.append(p.name)

    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template and not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key):
            all_present_names.append(npc_template.get("name", npc_key))

    monster_names_list_for_room_desc = []
    for i, monster_template_key_or_runtime_id in enumerate(room_data.get("monsters", [])):
        monster_template_key = monster_template_key_or_runtime_id
        monster_template = GAME_MONSTER_TEMPLATES.get(monster_template_key)
        if monster_template:
            conceptual_runtime_id_for_check = f"{current_room_id}_{monster_template_key}_{i}"
            if not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(conceptual_runtime_id_for_check):
                monster_names_list_for_room_desc.append(monster_template.get("name", "a creature"))
    
    if monster_names_list_for_room_desc:
        all_present_names.extend(monster_names_list_for_room_desc)

    all_present_names.sort()
    present_entities_str = "ALSO HERE: " + ", ".join(all_present_names) + "." if all_present_names else ""

    visible_item_names = []
    # ... (debug message setup for send_room_desc) ...
    if config.DEBUG_MODE:
        debug_msg = f"--- DEBUG SEND_ROOM_DESC (Room ID: {current_room_id}) ---\n"
        debug_msg += f"  Static items in room_data['items']: {room_data.get('items', [])}\n"
        debug_msg += f"  Dynamic objects in room_data['objects'] (keys): {list(room_data.get('objects', {}).keys())}\n"

    for item_id_static in room_data.get("items", []):
        item_tpl_static = GAME_ITEMS.get(item_id_static)
        if item_tpl_static:
            visible_item_names.append(item_tpl_static.get("name", item_id_static))
            if config.DEBUG_MODE: debug_msg += f"  Added static item to visible: '{item_tpl_static.get('name', item_id_static)}'\n"

    for obj_id_dyn, obj_data_dynamic in room_data.get("objects", {}).items():
        if config.DEBUG_MODE:
            debug_msg += f"  Checking dynamic object ID '{obj_id_dyn}': Name='{obj_data_dynamic.get('name', 'N/A')}', is_corpse={obj_data_dynamic.get('is_corpse', False)}, is_ground_item={obj_data_dynamic.get('is_ground_item', False)}\n"
        if obj_data_dynamic.get("is_corpse") or obj_data_dynamic.get("is_ground_item"):
            visible_item_names.append(obj_data_dynamic.get("name", "an object"))
            if config.DEBUG_MODE:
                debug_msg += f"    Added dynamic object to visible: '{obj_data_dynamic.get('name', 'an object')}' (Corpse: {obj_data_dynamic.get('is_corpse', False)}, GroundItem: {obj_data_dynamic.get('is_ground_item', False)})\n"

    items_on_ground_str = ""
    if visible_item_names:
        sorted_unique_items = sorted(list(set(visible_item_names))) 
        items_on_ground_str = "YOU ALSO SEE: " + ", ".join(sorted_unique_items) + "."
    else: 
        items_on_ground_str = "YOU ALSO SEE: (nothing)" 
    
    if config.DEBUG_MODE:
        debug_msg += f"  Final 'YOU ALSO SEE' string: {items_on_ground_str}\n" 
        debug_msg += "--- END DEBUG SEND_ROOM_DESC ---"
        print(debug_msg)

    room_data_payload = {
        "name": room_data.get("name", "Nowhere Special"), "description": final_room_description,
        "presence_summary": present_entities_str, "items_summary": items_on_ground_str, 
        "exits": ", ".join(k.upper() for k in room_data.get("exits", {}).keys()) or "None",
        "type": "room_data_update"
    }
    player_object.add_message(room_data_payload)

@socketio.on('connect')
def handle_connect(*args): # Accepts potential arguments from SocketIO
    sid = request.sid
    if config.DEBUG_MODE:
        print(f"DEBUG: Client connected: SID {sid}")
        if args and args[0] is not None : # Check if any actual auth data was passed
            print(f"DEBUG: handle_connect received args: {args}")

    # Initialize session for character creation/login prompt phase
    player_creation_sessions[sid] = {
        "phase": "awaiting_login_name", # Player needs to send "login <name>" or "create <name>"
        "sid": sid,
        "messages_queue": [], # For accumulating messages during creation steps
        "player_shell": None  # This will hold the temporary Player object during creation
    }

    # Send initial prompts to the client
    # It's good practice to wrap emits in try-except if there's any doubt,
    # but for this initial emit, it's usually straightforward.
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
        # Log if emit fails, though this is rare if the connection is established
        print(f"ERROR: Failed to emit initial messages to SID {sid}. Error: {e_emit}")
        # Optionally, you might want to clean up player_creation_sessions[sid] here
        # or handle the disconnect more explicitly if the client can't receive crucial info.

    # NO command_input parsing here.
    # NO parts_initial, verb_initial, name_arg_initial here.
    # NO logic checking for "create" or "login" verbs here.
    # Any try-except blocks here should only reference variables available in this scope (e.g., sid).


# --- handle_player_command function ---
# (This is the function from the previous turn, ID: main_py_handle_command_update_v6)
# Ensure this is fully integrated here.
@socketio.on('player_command')
def handle_player_command(data):
    sid = request.sid
    command_input = data.get('command', '').strip() # command_input IS DEFINED HERE from client data

    if config.DEBUG_MODE:
        print(f"\nDEBUG CMD: SID={sid}, Command='{command_input}'")
    if not command_input:
        return

    try:
        player = active_players.get(sid)
        session = player_creation_sessions.get(sid)

        if player: # Player is already logged in and active
            player.add_message(f"> {command_input}", "echo") # Echo the command

            if hasattr(player, 'next_action_time') and time.time() < player.next_action_time:
                player.add_message(f"Wait {max(0.0, round(player.next_action_time - time.time(), 1))}s.", "error_rt")
            else:
                room_id_before_move = player.current_room_id
                current_room_data = GAME_ROOMS.get(room_id_before_move)
                action_taken = False # Flag to see if any command was processed
                command_lower = command_input.lower()

                if not current_room_data:
                    player.add_message(f"Error: You are in an unknown room (ID: {room_id_before_move})! Moving to safety...", "error_critical")
                    player.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
                    if player_handler: player_handler.save_player(player) # Save before moving
                    current_room_data = GAME_ROOMS.get(player.current_room_id)
                    if not current_room_data: # Should not happen if default room is valid
                        player.add_message("PANIC: Default room is also invalid. Contact admin.", "error_critical")
                        all_msgs_panic = player.get_queued_messages()
                        if all_msgs_panic: socketio.emit('game_messages', {'messages': all_msgs_panic}, room=sid)
                        return # Critical error, stop processing for this player
                    send_room_description(player) # Send new room desc
                    # Fall through to allow next command, or just return if preferred

                # --- Custom Object Actions ---
                if current_room_data and not action_taken:
                    for obj_id, obj_data in current_room_data.get("objects", {}).items():
                        if obj_data.get("interactable") and isinstance(obj_data.get("actions"), dict):
                            for action_phrase, action_result in obj_data["actions"].items():
                                if command_lower == action_phrase.lower():
                                    action_taken = True
                                    if isinstance(action_result, int): # Assumes action_result is a room_id for movement
                                        player.add_message(f"You {action_phrase}...", "feedback_action")
                                        broadcast_to_room(room_id_before_move, f"{player.name} {action_phrase}.", "ambient_other_player", [sid])
                                        player.current_room_id = action_result
                                        send_room_description(player)
                                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_move', 1.0)
                                    elif isinstance(action_result, str): # Assumes action_result is a script/event key
                                        # Placeholder for more complex object interactions
                                        player.add_message(f"You attempt to {action_phrase}. (Action: {action_result} - not fully implemented).", "system_info")
                                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                                    else:
                                        player.add_message(f"You try to {action_phrase}, but nothing specific happens.", "feedback_neutral")
                                    break # Exit inner loop once action is found
                        if action_taken: break # Exit outer loop if action was taken

                # --- Standard Command Parsing (if no custom object action was taken) ---
                if not action_taken:
                    parts = command_input.split(" ", 1)
                    verb = parts[0].lower()
                    raw_target_arg = parts[1].strip() if len(parts) > 1 else None
                    target_arg = None # Initialize target_arg

                    if raw_target_arg:
                        if verb == "say": # "say" takes the whole rest of the string
                            target_arg = raw_target_arg
                        else: # For other commands, handle "at" for look/examine
                            look_verbs = ["look", "l", "examine", "ex", "exa"]
                            if verb in look_verbs and raw_target_arg.lower().startswith("at ") and len(raw_target_arg) > 3:
                                target_arg = raw_target_arg[3:].strip()
                            else:
                                target_arg = raw_target_arg

                    if config.DEBUG_MODE:
                        print(f"DEBUG CMD PARSED (Fallback): Verb='{verb}', TargetArg='{target_arg}' (RawInputTarget='{raw_target_arg}')")

                    # --- MOVEMENT ---
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
                            send_room_description(player) # Send new room description
                        else: # Invalid exit or room, move player back
                            player.add_message("You try to move, but the way is blocked or leads nowhere.", "error_move")
                            player.current_room_id = room_id_before_move # Revert to original room
                            send_room_description(player) # Resend original room description

                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_move', 0.5)

                    # --- LOOK ---
                    elif verb == "look" or verb == "l" or verb == "examine" or verb == "ex" or verb == "exa":
                        action_taken = True
                        rt_look_cmd = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                        if target_arg and current_room_data:
                            # Try to find a combat target first
                            target_entity_data_look, entity_type_look, _, _ = find_combat_target_in_room(player, target_arg, current_room_data)
                            if target_entity_data_look:
                                look_desc_entity = target_entity_data_look.get("look_description", target_entity_data_look.get("description", f"You see {target_entity_data_look.get('name', target_arg)}."))
                                # Add equipped items to description if NPC/Monster
                                if entity_type_look in ["npc", "monster"] and target_entity_data_look.get("equipped"):
                                    equipped_str_parts_look = []
                                    for slot_key_look, item_id_look in target_entity_data_look.get("equipped", {}).items():
                                        if item_id_look and GAME_ITEMS.get(item_id_look):
                                            slot_display_name = config.EQUIPMENT_SLOTS.get(slot_key_look, slot_key_look).replace('_', ' ').title()
                                            item_name_display = GAME_ITEMS.get(item_id_look,{}).get('name',item_id_look)
                                            equipped_str_parts_look.append(f"<{slot_display_name}> {item_name_display}")
                                    if equipped_str_parts_look:
                                        look_desc_entity += "\nThey are equipped with:\n" + "\n".join(equipped_str_parts_look)
                                player.add_message(look_desc_entity, "feedback_look_target")
                            else: # If not a combat target, try to find an object
                                obj_id_look, obj_data_look = find_object_in_room(player, target_arg, current_room_data)
                                if obj_data_look:
                                    look_desc_obj = obj_data_look.get("description", "You see nothing special about it.")
                                    if obj_data_look.get("is_corpse") and obj_data_look.get("inventory") and not obj_data_look.get("searched_and_emptied", False):
                                        look_desc_obj += " It looks like it might have something on it."
                                    elif obj_data_look.get("is_container") and obj_data_look.get("inventory"): # General containers
                                        container_items_str = "".join([f"  - {GAME_ITEMS.get(item_id_in_cont, {}).get('name', item_id_in_cont)}\n" for item_id_in_cont in obj_data_look.get("inventory", [])])
                                        if container_items_str:
                                            look_desc_obj += " It contains:\n" + container_items_str
                                        else:
                                            look_desc_obj += " It appears to be empty."
                                    player.add_message(look_desc_obj, "feedback_look_target")
                                else: # Neither combat target nor object found
                                    player.add_message(f"You don't see '{target_arg}' here.", "error")
                        else: # No target_arg, just "look"
                            send_room_description(player)
                        player.next_action_time = time.time() + rt_look_cmd

                    # --- ATTACK ---
                    elif verb == "attack":
                        action_taken = True
                        rt_look = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2) # For error messages
                        rt_attack = config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)

                        if not target_arg:
                            player.add_message("Attack whom or what?", "error")
                            player.next_action_time = time.time() + rt_look
                        elif not current_room_data: # Should have been caught earlier
                            player.add_message("You can't attack in the void.", "error")
                            player.next_action_time = time.time() + rt_look
                        else:
                            target_data, target_type, target_id_or_key, target_full_match_data = find_combat_target_in_room(player, target_arg, current_room_data)
                            if target_data:
                                if target_type == "player":
                                    if not current_room_data.get("pvp", getattr(config, "PVP_ENABLED_ROOM_TAG", False)):
                                        player.add_message("PvP is not allowed here.", "error_pvp")
                                    else:
                                        # Placeholder for PvP combat call
                                        player.add_message("PvP combat is not fully implemented.", "system_info")
                                    player.next_action_time = time.time() + rt_attack # Still apply RT
                                elif target_type in ["monster", "npc"]:
                                    monster_runtime_id_for_combat = target_id_or_key # For NPCs, key is runtime ID
                                    if target_type == "monster" and target_full_match_data:
                                        monster_runtime_id_for_combat = target_full_match_data.get("runtime_id", target_id_or_key)

                                    combat_results = combat.handle_player_attack(player, target_data, target_type, target_arg, GAME_ITEMS, monster_runtime_id=monster_runtime_id_for_combat)

                                    # Messages from combat.handle_player_attack are added to player directly
                                    if combat_results.get('broadcast_message'):
                                        broadcast_to_room(player.current_room_id, combat_results['broadcast_message'], "ambient_combat", [player.sid])

                                    if combat_results.get('defeated') and not combat_results.get('already_defeated'):
                                        defeated_runtime_id = combat_results.get('target_runtime_id')
                                        defeated_name = combat_results.get('target_name', 'creature')

                                        if config.DEBUG_MODE:
                                            print(f"DEBUG MAIN_DEFEAT: {player.name} def. {defeated_name} (Key:{target_id_or_key}, RuntimeID: {defeated_runtime_id})")

                                        xp_val = target_data.get("xp_value", 0)
                                        if xp_val > 0 and hasattr(player, 'add_xp_to_pool'):
                                            player.add_xp_to_pool(xp_val, GAME_RACES) # Pass GAME_RACES

                                        faction_hits = target_data.get("faction_hits_on_kill", [])
                                        if faction_hits and hasattr(player, 'update_faction'):
                                            for hit in faction_hits:
                                                player.update_faction(hit["faction_id"], hit["amount"])

                                        # Respawn tracking
                                        resp_time = target_data.get("respawn_time_seconds", getattr(config, 'MONSTER_DEFAULT_RESPAWN_SECONDS', 300))
                                        if "spawn_config" in target_data: # More specific config from monster/npc template
                                            resp_time = target_data["spawn_config"].get("respawn_time_seconds", resp_time)

                                        # Ensure defeated_runtime_id is correctly determined
                                        TRACKED_DEFEATED_ENTITIES[defeated_runtime_id] = {
                                            "template_key": target_id_or_key, # Store the original template key
                                            "type": target_type,
                                            "room_id": player.current_room_id,
                                            "defeated_at": time.time(),
                                            "eligible_at": time.time() + resp_time,
                                            "chance": target_data.get("respawn_chance", getattr(config, 'MONSTER_DEFAULT_RESPAWN_CHANCE', 0.5)),
                                            "is_unique": target_data.get("is_unique", False),
                                            "original_instance_index": target_full_match_data.get("original_index_in_room_list") if target_full_match_data else None
                                        }
                                        if config.DEBUG_MODE:
                                            print(f"DEBUG RESPAWN_TRACK: Added {defeated_runtime_id}. Eligible at {time.time() + resp_time:.0f}")

                                        # Corpse creation
                                        if target_data.get("leaves_corpse", True):
                                            corpse_obj = loot_handler.create_corpse_object_data(target_data, defeated_runtime_id, GAME_ITEMS, GAME_EQUIPMENT_TABLES)
                                            if corpse_obj and current_room_data:
                                                current_room_data.setdefault("objects", {})[corpse_obj["id"]] = corpse_obj
                                                player.add_message(f"The {defeated_name} slumps, leaving a corpse.", "event_defeat_corpse")
                                    player.next_action_time = time.time() + rt_attack
                                else: # Can't attack target type
                                    player.add_message("You can't attack that!", "error")
                                    player.next_action_time = time.time() + rt_look
                            else: # Target not found
                                player.add_message(f"You don't see '{target_arg}' to attack.", "error")
                                player.next_action_time = time.time() + rt_look

                    # --- SEARCH ---
                    elif verb == "search":
                        action_taken = True
                        rt_search_default = getattr(config, 'SEARCH_BASE_ROUNDTIME', 1.5)
                        perception_stat = player.stats.get(getattr(config, 'STAT_FOR_SEARCH_TIME_REDUCTION', 'perception'), 0)
                        reduction_per_10_points = getattr(config, 'SEARCH_PERCEPTION_REDUCTION_PER_10POINTS', 0.5)
                        time_reduction = (perception_stat // 10) * reduction_per_10_points
                        final_search_rt = max(getattr(config, 'SEARCH_MIN_ROUNDTIME_SECONDS', 0.5), rt_search_default - time_reduction)
                        final_search_rt = min(final_search_rt, getattr(config, 'SEARCH_MAX_ROUNDTIME_SECONDS', 5.0))

                        if not target_arg: player.add_message("Search what?", "error")
                        elif not current_room_data: player.add_message("You can't search here.", "error")
                        else:
                            obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data:
                                target_display_name_search = obj_data.get("name", target_arg)
                                if obj_data.get("is_corpse"):
                                    if obj_data.get("searched_and_emptied"):
                                        player.add_message(f"The {target_display_name_search} has already been searched.", "feedback_neutral")
                                    else:
                                        corpse_inventory_ids = obj_data.get("inventory", [])
                                        if config.DEBUG_MODE: print(f"DEBUG SEARCH: Corpse inventory IDs: {corpse_inventory_ids}")

                                        items_moved_to_ground_names = []
                                        if corpse_inventory_ids:
                                            player.add_message(f"You search the {target_display_name_search}...", "feedback_search_corpse")
                                            for item_id_on_corpse in list(corpse_inventory_ids): # Iterate a copy if modifying
                                                item_object_placed = add_item_object_to_room(current_room_data, item_id_on_corpse, GAME_ITEMS)
                                                if item_object_placed:
                                                    items_moved_to_ground_names.append(item_object_placed.get("name", item_id_on_corpse))
                                        obj_data["inventory"] = [] # Clear corpse inventory after moving items

                                        if items_moved_to_ground_names:
                                            player.add_message("...and its contents spill onto the ground:", "event_highlight")
                                            for name_loot in items_moved_to_ground_names:
                                                player.add_message(f"- A {name_loot}", "feedback_loot_drop")
                                        elif corpse_inventory_ids and not items_moved_to_ground_names: # Had items, but none made it to ground
                                            player.add_message("...but find nothing you can retrieve from it.", "feedback_search_empty")
                                        else: # Corpse inventory was initially empty or nothing successfully spilled
                                            player.add_message(f"You search the {target_display_name_search} but find nothing of value.", "feedback_search_empty")

                                        obj_data["searched_and_emptied"] = True
                                        obj_data["description"] = f"The searched remains of {obj_data.get('original_name', 'a creature')}."
                                        # Optionally, remove the empty corpse object after search or let it decay naturally
                                        if obj_id in current_room_data.get("objects", {}):
                                            del current_room_data["objects"][obj_id] # Remove corpse after searching
                                            broadcast_to_room(player.current_room_id, f"The {target_display_name_search} crumbles to dust after being searched.", "ambient_neutral", [sid])
                                elif obj_data.get("is_container") and not obj_data.get("is_ground_item"): # Search a static container in the room
                                    if obj_data.get("searched_and_emptied"):
                                        player.add_message(f"The {target_display_name_search} appears empty.", "feedback_neutral")
                                    else:
                                        container_inv = obj_data.get("inventory", [])
                                        items_moved = []
                                        if container_inv:
                                            player.add_message(f"You search the {target_display_name_search}...", "feedback_search_corpse")
                                        for item_id_cont in list(container_inv):
                                            item_obj_placed = add_item_object_to_room(current_room_data, item_id_cont, GAME_ITEMS)
                                            if item_obj_placed:
                                                items_moved.append(item_obj_placed.get("name", item_id_cont))
                                        obj_data["inventory"] = [] # Empty the container

                                        if items_moved:
                                            player.add_message("...revealing its contents on the ground:", "event_highlight")
                                            for name_loot in items_moved:
                                                player.add_message(f"- A {name_loot}", "feedback_loot_drop")
                                        else:
                                            player.add_message("...but find nothing retrievable.", "feedback_search_empty")
                                        obj_data["searched_and_emptied"] = True # Mark as searched
                                else: # Not a corpse or searchable static container
                                    player.add_message(f"You find nothing special by searching the {target_display_name_search}.", "feedback_search_empty")
                            else: # Target not found
                                player.add_message(f"You don't see '{target_arg}' to search here.", "error")
                        player.next_action_time = time.time() + final_search_rt

                    # --- SKIN ---
                    elif verb == "skin":
                        action_taken = True
                        rt_skin = getattr(config, 'SKIN_BASE_ROUNDTIME', 2.0)
                        player.next_action_time = time.time() + rt_skin
                        if not target_arg: player.add_message("Skin what?", "error")
                        elif not current_room_data: player.add_message("There's nothing here to skin.", "error")
                        else:
                            obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data and obj_data.get("is_corpse"):
                                corpse_name_skin = obj_data.get("name", "corpse")
                                if obj_data.get("skinned"):
                                    player.add_message(f"The {corpse_name_skin} has already been skinned.", "feedback_neutral")
                                else:
                                    original_template_key = obj_data.get("original_template_key")
                                    monster_template = None
                                    if original_template_key:
                                        # Determine if it was an NPC or Monster to look up in correct dict
                                        # This requires knowing the type or trying both, or storing type on corpse.
                                        # Assuming monster for now as NPCs might not be typically "skinned"
                                        monster_template = GAME_MONSTER_TEMPLATES.get(original_template_key)
                                        if not monster_template: # Try NPC if not found in monsters
                                            monster_template = GAME_NPCS.get(original_template_key)


                                    if not monster_template:
                                        player.add_message(f"Error: Could not identify original creature for {corpse_name_skin}.", "error_critical")
                                    elif monster_template.get("skinnable"):
                                        player_skill_value = player.skills.get(monster_template.get("skinning", {}).get("skill_required", "survival"), 0)
                                        skinned_item_ids = loot_handler.generate_skinning_loot(monster_template, player_skill_value, GAME_ITEMS)

                                        if skinned_item_ids:
                                            player.add_message(f"You attempt to skin the {corpse_name_skin}...", "feedback_action")
                                            for item_id_skinned in skinned_item_ids:
                                                item_object_placed_skin = add_item_object_to_room(current_room_data, item_id_skinned, GAME_ITEMS)
                                                if item_object_placed_skin:
                                                    player.add_message(f"You successfully skin a {item_object_placed_skin.get('name', item_id_skinned)} from the corpse. It falls to the ground.", "feedback_get_item")
                                                else:
                                                    player.add_message(f"You skin something, but it vanishes before you can grab it.", "error")
                                            obj_data["skinned"] = True
                                            obj_data["description"] = f"The skinned remains of {obj_data.get('original_name', 'a creature')}."
                                        else:
                                            skinning_failure_msg = monster_template.get("skinning",{}).get("failure_message", "You fail to get anything useful from skinning the {monster_name}.")
                                            player.add_message(skinning_failure_msg.format(monster_name=corpse_name_skin), "feedback_neutral")
                                            obj_data["skinned"] = True # Mark as attempted even on failure if desired
                                            obj_data["description"] = f"The mangled remains of {obj_data.get('original_name', 'a creature')} after a failed skinning attempt."
                                    else: # Not skinnable template
                                        player.add_message(f"The {corpse_name_skin} is not something you can skin.", "error")
                            else: # Target not a corpse or not found
                                player.add_message(f"You don't see '{target_arg}' (a skinnable corpse) here.", "error")

                    # --- GET/TAKE ---
                    elif verb in ["get", "take"]:
                        action_taken = True
                        rt_get_default = getattr(config, 'GET_BASE_ROUNDTIME', 0.5)
                        player.next_action_time = time.time() + rt_get_default
                        if not target_arg: player.add_message(f"{verb.capitalize()} what?", "error")
                        elif not current_room_data: player.add_message("There's nothing here to get.", "error")
                        else:
                            item_name_query_get = target_arg
                            obj_id_to_get, obj_data_to_get = find_object_in_room(player, item_name_query_get, current_room_data)

                            if obj_data_to_get:
                                item_id_for_inventory = None
                                item_name_for_message = obj_data_to_get.get('name', 'item')
                                can_take = False

                                if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20):
                                    player.add_message("Your inventory is full.", "error")
                                else:
                                    if obj_data_to_get.get("is_ground_item"): # Dynamic item on ground
                                        item_id_for_inventory = obj_data_to_get.get("item_template_id")
                                        if obj_id_to_get in current_room_data.get("objects", {}):
                                            del current_room_data["objects"][obj_id_to_get]
                                            can_take = True
                                        else:
                                            if config.DEBUG_MODE: print(f"DEBUG GET: Dynamic object {obj_id_to_get} not found in room objects for removal.")
                                    elif obj_data_to_get.get("is_static_item"): # Static item listed in room template
                                        item_id_for_inventory = obj_data_to_get.get("item_template_id") # which is its key
                                        if item_id_for_inventory in current_room_data.get("items", []):
                                            current_room_data["items"].remove(item_id_for_inventory)
                                            can_take = True
                                        else:
                                            if config.DEBUG_MODE: print(f"DEBUG GET: Static item {item_id_for_inventory} not found in room items for removal.")
                                    else: # Not a takeable type of object
                                        player.add_message(f"You can't {verb} the {item_name_for_message}.", "error")

                                if can_take and item_id_for_inventory:
                                    player.inventory.append(item_id_for_inventory)
                                    player.add_message(f"You pick up the {item_name_for_message}.", "feedback_get_item")
                                    broadcast_to_room(player.current_room_id, f"{player.name} picks up {item_name_for_message}.", "ambient_other_player", [sid])
                                elif can_take and not item_id_for_inventory: # Should not happen if can_take is true
                                    player.add_message("Error: Item ID missing for pickup.", "error_critical")
                            else: # Object not found
                                player.add_message(f"You don't see '{item_name_query_get}' here to {verb}.", "error")

                    # --- EQUIP/WEAR ---
                    elif verb == "equip" or verb == "wear":
                        action_taken = True
                        rt_equip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                        player.next_action_time = time.time() + rt_equip
                        if not target_arg:
                            player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword mainhand)", "error")
                        else:
                            target_arg_parts = target_arg.split()
                            item_name_or_id_query_equip = ""
                            slot_to_equip_to_query = None

                            if len(target_arg_parts) > 1:
                                potential_slot_query = target_arg_parts[-1].lower()
                                if potential_slot_query in config.EQUIPMENT_SLOTS.keys():
                                    slot_to_equip_to_query = potential_slot_query
                                    item_name_or_id_query_equip = " ".join(target_arg_parts[:-1]).lower()
                                else: # Assume whole thing is item name if last word isn't a slot
                                    item_name_or_id_query_equip = target_arg.lower()
                            else: # Only one word provided, assume it's item name
                                item_name_or_id_query_equip = target_arg.lower()

                            if config.DEBUG_MODE: print(f"DEBUG EQUIP PARSED: Item Query='{item_name_or_id_query_equip}', Slot Query='{slot_to_equip_to_query}'")

                            actual_item_id_to_equip = None
                            # First, check if the query is a direct item_id in inventory
                            if item_name_or_id_query_equip in player.inventory and GAME_ITEMS.get(item_name_or_id_query_equip):
                                actual_item_id_to_equip = item_name_or_id_query_equip
                            
                            # If not found as ID, search by name/keyword in inventory
                            if not actual_item_id_to_equip:
                                for item_id_in_inv in player.inventory:
                                    item_template = GAME_ITEMS.get(item_id_in_inv)
                                    if item_template:
                                        item_name_lower = item_template.get("name", "").lower()
                                        item_keywords_lower = [k.lower() for k in item_template.get("keywords", [])]
                                        if item_name_lower == item_name_or_id_query_equip or \
                                           item_name_or_id_query_equip in item_keywords_lower:
                                            actual_item_id_to_equip = item_id_in_inv
                                            break
                                        # Optional: Allow partial name match
                                        if item_name_or_id_query_equip in item_name_lower:
                                            actual_item_id_to_equip = item_id_in_inv
                                            break # Take first partial match

                            if not actual_item_id_to_equip:
                                player.add_message(f"You don't have '{item_name_or_id_query_equip}' in your inventory.", "error")
                            else:
                                final_slot_to_equip = slot_to_equip_to_query
                                item_template_for_slot = GAME_ITEMS.get(actual_item_id_to_equip)

                                if not final_slot_to_equip and item_template_for_slot: # Slot not specified, try item's default
                                    preferred_slots = item_template_for_slot.get("slot", [])
                                    if not isinstance(preferred_slots, list): preferred_slots = [preferred_slots]
                                    if preferred_slots and preferred_slots[0] in config.EQUIPMENT_SLOTS:
                                        final_slot_to_equip = preferred_slots[0]
                                        player.add_message(f"(Equipping to {config.EQUIPMENT_SLOTS.get(final_slot_to_equip, final_slot_to_equip).replace('_', ' ').title()})", "feedback_neutral")
                                    else:
                                        player.add_message(f"{verb.capitalize()} the {item_template_for_slot.get('name', item_name_or_id_query_equip)} where? (Valid slots: {', '.join(config.EQUIPMENT_SLOTS.keys())}).", "error")
                                elif not item_template_for_slot: # Should not happen if actual_item_id_to_equip was found
                                     player.add_message("Item error while determining slot.", "error_critical")


                                if final_slot_to_equip: # Slot is now determined (either user-specified or default)
                                    if final_slot_to_equip not in config.EQUIPMENT_SLOTS: # Should be caught earlier but double check
                                        player.add_message(f"'{final_slot_to_equip}' is not a valid equipment slot.", "error")
                                    elif hasattr(player, 'equip_item'):
                                        success = player.equip_item(actual_item_id_to_equip, final_slot_to_equip, GAME_ITEMS, GAME_RACES)
                                        if success: # Message handled by player.equip_item
                                            broadcast_to_room(player.current_room_id, f"{player.name} equips a {GAME_ITEMS.get(actual_item_id_to_equip,{}).get('name','piece of equipment')}.", "ambient_other_player", [sid])
                                        # No 'else' here, equip_item should add its own error messages
                                    else: # Player object missing method
                                        player.add_message("Equipment system error (player object).", "error_critical")

                    # --- UNEQUIP/REMOVE ---
                    elif verb == "unequip" or verb == "remove":
                        action_taken = True
                        rt_unequip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                        player.next_action_time = time.time() + rt_unequip
                        if not target_arg:
                            player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword or {verb} mainhand)", "error")
                        else:
                            item_or_slot_query = target_arg.lower()
                            slot_to_unequip_from = None

                            # Check if query is a slot key first
                            if item_or_slot_query in config.EQUIPMENT_SLOTS.keys():
                                slot_to_unequip_from = item_or_slot_query
                            else: # If not a slot key, search by item name/id in equipped items
                                for slot_key, item_id_val in player.equipped_items.items():
                                    if item_id_val: # If something is equipped in this slot
                                        item_template = GAME_ITEMS.get(item_id_val)
                                        if item_template:
                                            if item_template.get("name","").lower() == item_or_slot_query or \
                                               item_or_slot_query in [k.lower() for k in item_template.get("keywords",[])] or \
                                               item_id_val.lower() == item_or_slot_query:
                                                slot_to_unequip_from = slot_key
                                                break
                            if slot_to_unequip_from:
                                success = player.unequip_item(slot_to_unequip_from, GAME_ITEMS, GAME_RACES)
                                if success: # Message handled by player.unequip_item
                                    broadcast_to_room(player.current_room_id, f"{player.name} unequips an item.", "ambient_other_player", [sid])
                                # No 'else' here, unequip_item should add its own error messages
                            else:
                                player.add_message(f"You don't have '{target_arg}' equipped or it's not a valid slot.", "error")

                    # --- INVENTORY ---
                    elif verb == "inventory" or verb == "i":
                        action_taken = True
                        if player.inventory:
                            player.add_message("--- Your Inventory ---", "header_info_block")
                            item_counts = {}
                            for item_id_inv in player.inventory:
                                item_counts[item_id_inv] = item_counts.get(item_id_inv, 0) + 1
                            for item_id_counted, count in sorted(item_counts.items()):
                                item_template_inv = GAME_ITEMS.get(item_id_counted)
                                display_name = item_template_inv.get("name", item_id_counted) if item_template_inv else item_id_counted
                                player.add_message(f"- {display_name}{f' (x{count})' if count > 1 else ''}", "info_block_content")
                        else:
                            player.add_message("Your inventory is empty.", "feedback_neutral")
                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.1) # Very short RT

                    # --- NO ACTION TAKEN / UNKNOWN COMMAND ---
                    if not action_taken: # If no verb matched or no custom action was taken
                        player.add_message(f"You can't seem to '{command_input}' here. (Type 'help' for commands)", "error")
                        player.next_action_time = time.time() + 0.1 # Minimal RT for unknown command

            # --- After processing player command for logged-in player ---
            all_msgs = player.get_queued_messages()
            if all_msgs:
                socketio.emit('game_messages', {'messages': all_msgs}, room=sid)
            send_player_stats_update(player) # Always send stats after any action

        elif session: # Player is in character creation or login process
            player_shell = session.get("player_shell")
            current_phase = session.get("phase")

            # Helper function to send accumulated messages during creation
            def send_creation_messages(s_id, sess, p_shell_optional):
                messages_to_client = []
                if "messages_queue" in sess and sess["messages_queue"]:
                    messages_to_client.extend(sess["messages_queue"])
                    sess["messages_queue"] = [] # Clear queue after getting
                if p_shell_optional and hasattr(p_shell_optional, "get_queued_messages"):
                    messages_to_client.extend(p_shell_optional.get_queued_messages())
                if messages_to_client:
                    socketio.emit('game_messages', {'messages': messages_to_client}, room=s_id)

            # --- Initial command handling: "login <name>" or "create <name>" ---
            if not player_shell and current_phase == "awaiting_login_name":
                parts_initial = command_input.split(" ", 1)
                verb_initial = parts_initial[0].lower()
                name_arg_initial = parts_initial[1].strip().title() if len(parts_initial) > 1 and parts_initial[1].strip() else ""

                if verb_initial == "create" and name_arg_initial:
                    min_len = getattr(config, 'MIN_CHAR_NAME_LENGTH', 3)
                    max_len = getattr(config, 'MAX_CHAR_NAME_LENGTH', 20) # Ensure this is defined in config
                    is_valid_name_format = all(c.isalpha() or c.isspace() for c in name_arg_initial) and any(c.isalpha() for c in name_arg_initial.replace(" ",""))

                    if player_handler and player_handler.player_exists(name_arg_initial):
                        session["messages_queue"].append({"text": f"The name '{name_arg_initial}' is already whispered. Choose another.", "type": "error", "prompt":True})
                    elif not (min_len <= len(name_arg_initial) <= max_len and is_valid_name_format):
                        session["messages_queue"].append({"text": f"A name must be {min_len}-{max_len} characters, letters/spaces only.", "type": "error", "prompt":True})
                    else:
                        player_shell = player_class.Player(sid, name_arg_initial) # Create shell
                        session["player_shell"] = player_shell
                        character_creation.start_character_creation(player_shell) # Start creation logic
                        session["phase"] = player_shell.creation_phase # Update session phase from player_shell
                elif verb_initial == "login" and name_arg_initial:
                    if player_handler:
                        loaded_player = player_handler.load_player(name_arg_initial.lower(), sid, GAME_RACES, GAME_ITEMS)
                        if loaded_player:
                            active_players[sid] = loaded_player
                            session_login_msgs = list(session.get("messages_queue", [])) # Get any pending messages
                            player_creation_sessions.pop(sid, None) # Remove from creation sessions

                            if session_login_msgs: # Send any previously queued messages
                                emit('game_messages', {'messages': session_login_msgs}, room=sid)

                            loaded_player.add_message(f"Welcome back to {config.MUD_NAME}, {loaded_player.name}!", "event_highlight")
                            broadcast_to_room(loaded_player.current_room_id, f"{loaded_player.name} has reconnected.", "ambient_player_arrival", [sid])
                            send_room_description(loaded_player)
                            final_login_messages = loaded_player.get_queued_messages() # Get messages added by send_room_description etc.
                            if final_login_messages:
                                emit('game_messages', {'messages': final_login_messages}, room=sid)
                            send_player_stats_update(loaded_player)
                            return # Exit handler as player is now active
                        else: # Player not found
                            session["messages_queue"].append({"text": f"Character '{name_arg_initial}' not found.", "type": "error", "prompt":True})
                    else: # player_handler not available
                        session["messages_queue"].append({"text": "Login system unavailable.", "type": "error_critical", "prompt":True})
                else: # Invalid command at this stage
                     if current_phase == "awaiting_login_name": # Only if still in this phase
                        session["messages_queue"].append({"text": "Please use 'login <name>' or 'create <name>'.", "type": "prompt"})
                
                send_creation_messages(sid, session, player_shell) # Send any accumulated messages

            # --- Subsequent character creation input handling ---
            elif player_shell: # player_shell exists, so creation is in progress
                # Pass GAME_RACES to character_creation.handle_creation_input
                character_creation.handle_creation_input(player_shell, command_input, player_handler, GAME_RACES)
                if session.get("phase") != player_shell.creation_phase: # Update session phase if changed by handler
                    session["phase"] = player_shell.creation_phase

                if player_shell.creation_phase == "completed":
                    # Pass GAME_RACES and GAME_ITEMS to finalize_character_creation
                    finalize_character_creation(sid, player_shell, GAME_RACES, GAME_ITEMS)
                    # finalize_character_creation will pop from player_creation_sessions
                    # and add to active_players, so no further send_creation_messages needed here
                    return # Exit as creation is complete
                
                send_creation_messages(sid, session, player_shell) # Send updates from this step

            # --- Error case for session state ---
            elif not player_shell and current_phase != "awaiting_login_name":
                 # This means session exists but player_shell is gone, and not at the first step.
                 # Could indicate an internal error.
                 session["messages_queue"].append({"text": "Your connection wavers. Reconnecting might help.", "type": "error_critical", "prompt":True})
                 send_creation_messages(sid, session, None) # Send error and prompt
        
        else: # No active player and no creation session for this SID
            if config.DEBUG_MODE:
                print(f"DEBUG ERROR: SID {sid} has no active player or creation session for command: '{command_input}'")
            # This client is in a weird state, tell them to reconnect
            emit('game_messages', {'messages': [{"text": "Connection error. Please try reconnecting.", "type": "error_critical"}]}, room=sid)

    except Exception as e:
        # Generic exception handler for handle_player_command
        print(f"!!! UNHANDLED EXCEPTION IN handle_player_command for SID {sid}, Command: '{command_input}' !!!")
        traceback.print_exc()
        try:
            # Try to inform the client, but this might also fail if the connection is broken
            socketio.emit('game_messages', {'messages': [{"text": "A critical server error occurred processing your command. Please try again or reconnect.", "type": "error_critical"}]}, room=sid)
        except Exception as e_emit_critical:
            print(f"CRITICAL: Error emitting critical error message to client {sid} after command processing exception: {e_emit_critical}")
            
# --- Flask Routes & Main Execution ---
@app.route('/')
def index_page():
    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists('templates'): os.makedirs('templates')
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f: f.write(getattr(config, 'FALLBACK_INDEX_HTML', "HTML Fallback: Client not found."))
        print("WARNING: templates/index.html not found. Created a basic placeholder.")

    mud_name = getattr(config, 'MUD_NAME', 'MUD Server'); print(f"Starting {mud_name}...")
    db_connection.connect_to_mongo()
    print("Initializing DB with defaults if needed..."); data_loader.initialize_database_with_defaults()
    print("Loading game data into memory..."); all_loaded_data = data_loader.load_all_game_data()
    GAME_ITEMS = all_loaded_data.get("items", {}); GAME_LOOT_TABLES = all_loaded_data.get("loot_tables", {})
    GAME_RACES = all_loaded_data.get("races", {}); GAME_EQUIPMENT_TABLES = all_loaded_data.get("equipment_tables", {})
    GAME_NPCS = all_loaded_data.get("npc_templates", {}); GAME_MONSTER_TEMPLATES = all_loaded_data.get("monster_templates", {})
    GAME_ROOMS = all_loaded_data.get("rooms", {})
    loot_handler.GAME_LOOT_TABLES = GAME_LOOT_TABLES 
    if config.DEBUG_MODE:
        print(f"DEBUG STARTUP: Loaded {len(GAME_RACES)} races into GAME_RACES.")
        if not GAME_RACES: print("WARNING: GAME_RACES is empty after loading.")
        print(f"DEBUG STARTUP: Loaded {len(GAME_EQUIPMENT_TABLES)} equipment tables.")
    print(f"Loaded: {len(GAME_ROOMS)} Rooms, {len(GAME_ITEMS)} Items, {len(GAME_NPCS)} NPCs, {len(GAME_MONSTER_TEMPLATES)} Monsters, {len(GAME_RACES)} Races, {len(GAME_LOOT_TABLES)} Loot Tables, {len(GAME_EQUIPMENT_TABLES)} Equip Tables.")
    print("Starting game tick loop...");
    game_tick_thread = threading.Thread(target=game_tick_loop, name="GameTickLoop"); game_tick_thread.daemon = True; game_tick_thread.start()
    host_ip = getattr(config, 'HOST', '0.0.0.0'); port_num = int(getattr(config, 'PORT', 8024))
    debug_flask = getattr(config, 'DEBUG_MODE_FLASK', False); use_reloader_flask = getattr(config, 'FLASK_USE_RELOADER', False) and debug_flask
    print(f"MUD server on http://{host_ip}:{port_num} (Flask Debug: {'ON' if debug_flask else 'OFF'}, Reloader: {'ON' if use_reloader_flask else 'OFF'})")
    try:
        socketio.run(app, host=host_ip, port=port_num, debug=debug_flask, use_reloader=use_reloader_flask, allow_unsafe_werkzeug=True if use_reloader_flask else False)
    except KeyboardInterrupt: print("\nServer shutting down (KeyboardInterrupt)...")
    except Exception as e: print(f"Failed to start server: {e}"); traceback.print_exc()
    finally:
        print("Attempting graceful shutdown..."); game_loop_active = False
        if 'game_tick_thread' in locals() and game_tick_thread.is_alive():
            print("Waiting for game tick loop..."); game_tick_thread.join(timeout=float(getattr(config,'TICK_INTERVAL_SECONDS', 6.0)) + 2.0)
            if game_tick_thread.is_alive(): print("Warning: Game tick loop did not terminate cleanly.")
        if active_players:
            print(f"Saving data for {len(active_players)} active player(s)...")
            for sid_s, player_s in list(active_players.items()):
                if player_handler.save_player(player_s):
                    if config.DEBUG_MODE: print(f"DEBUG MAIN_SHUTDOWN: Saved {player_s.name}.")
                else: print(f"ERROR MAIN_SHUTDOWN: Failed to save {player_s.name}.")
        db_connection.close_mongo_connection(); print(f"{mud_name} has shut down gracefully.")


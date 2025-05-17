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
    from game_logic import combat
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

active_players = {}
player_creation_sessions = {}

GAME_ROOMS = {}
GAME_ITEMS = {}
GAME_NPCS = {} # Will store processed NPC templates, including their 'equipped' dict
GAME_MONSTER_TEMPLATES = {} # Will store processed Monster templates, including their 'equipped' dict
GAME_RACES = {}
GAME_LOOT_TABLES = {}
GAME_EQUIPMENT_TABLES = {} # For storing equipment sets

TRACKED_DEFEATED_ENTITIES = {}

game_tick_counter = 0
game_loop_active = True

def game_tick_loop():
    # Ensure all necessary globals are available
    global game_tick_counter, active_players, GAME_ROOMS, GAME_ITEMS, GAME_NPCS, \
           GAME_MONSTER_TEMPLATES, GAME_RACES, GAME_LOOT_TABLES, GAME_EQUIPMENT_TABLES, \
           TRACKED_DEFEATED_ENTITIES

    local_tz = pytz.utc
    try:
        import tzlocal
        local_tz = tzlocal.get_localzone()
    except ImportError:
        print("WARNING: tzlocal not installed. Falling back to UTC for logs.")

    if config.DEBUG_MODE and game_tick_counter == 0:
        print(f"Game tick loop started at {datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')} (UTC: {datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')})")

    while game_loop_active:
        current_tick_start_time = time.monotonic()
        game_time_utc_now = time.time()
        datetime_utc_now_for_log = datetime.datetime.fromtimestamp(game_time_utc_now, tz=pytz.utc)
        datetime_local_now_for_log = datetime_utc_now_for_log.astimezone(local_tz)
        log_time_prefix = f"[{datetime_local_now_for_log.strftime('%Y-%m-%d %H:%M:%S %Z')}] (UTC: {datetime_utc_now_for_log.strftime('%H:%M:%S')}) TICK {game_tick_counter}"
        game_tick_counter += 1

        # --- System-Wide Updates ---
        environment_system.update_environment_state(
            game_tick_counter, active_players, GAME_ROOMS, log_time_prefix, broadcast_to_room
        )
        respawn_check_interval = getattr(config, 'MONSTER_RESPAWN_TICK_INTERVAL', 6)
        if game_tick_counter > 0 and game_tick_counter % respawn_check_interval == 0:
            # Call process_respawns with all required arguments
            respawn_system.process_respawns(
                log_time_prefix, game_time_utc_now, TRACKED_DEFEATED_ENTITIES,
                GAME_ROOMS, GAME_NPCS, GAME_MONSTER_TEMPLATES,
                broadcast_to_room,
                combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM, # From combat.py
                GAME_EQUIPMENT_TABLES,
                GAME_ITEMS
            )
        corpse_decay_interval = getattr(config, 'CORPSE_DECAY_TICK_INTERVAL', 10)
        if game_tick_counter > 0 and game_tick_counter % corpse_decay_interval == 0:
            decay_messages_by_room = loot_handler.process_corpse_decay(GAME_ROOMS, log_time_prefix)
            for room_id_decay, messages_list in decay_messages_by_room.items():
                for msg_text in messages_list:
                    broadcast_to_room(room_id_decay, msg_text, "ambient_neutral")

        # --- Player-Specific Tick Updates ---
        current_player_sids_for_processing = list(active_players.keys())
        for sid_player_process in current_player_sids_for_processing:
            player_obj_process = active_players.get(sid_player_process)
            if not player_obj_process:
                continue

            # --- XP ABSORPTION PHASE ---
            xp_absorption_interval_ticks = getattr(config, 'XP_ABSORPTION_TICKS', 5)
            if game_tick_counter > 0 and game_tick_counter % xp_absorption_interval_ticks == 0:
                if hasattr(player_obj_process, 'unabsorbed_xp') and player_obj_process.unabsorbed_xp > 0:
                    current_player_room_id = player_obj_process.current_room_id
                    current_player_room_data = GAME_ROOMS.get(current_player_room_id, {})
                    xp_to_absorb_this_event = getattr(config, 'MIN_XP_ABSORBED_PER_EVENT', 1)
                    if hasattr(player_obj_process, 'get_xp_absorption_amount_per_event'):
                        xp_to_absorb_this_event = player_obj_process.get_xp_absorption_amount_per_event(
                            current_player_room_data, GAME_RACES
                        )
                    if config.DEBUG_MODE:
                         print(f"{log_time_prefix} - XP_ABSORB_ATTEMPT: Player {player_obj_process.name} (RoomID: {current_player_room_id}) "
                               f"has {player_obj_process.unabsorbed_xp} UXPs. Attempting to absorb: {xp_to_absorb_this_event} UXPs.")
                    amount_to_absorb = min(player_obj_process.unabsorbed_xp, xp_to_absorb_this_event)
                    if amount_to_absorb > 0:
                        player_obj_process.xp = getattr(player_obj_process, 'xp', 0) + amount_to_absorb
                        player_obj_process.unabsorbed_xp -= amount_to_absorb
                        player_obj_process.add_message(f"You feel more experienced as knowledge settles in your mind (+{amount_to_absorb} XP).", "xp_absorb")
                        if hasattr(player_obj_process, '_check_and_send_mind_status'):
                             player_obj_process._check_and_send_mind_status(GAME_RACES)
                        if config.DEBUG_MODE:
                            print(f"{log_time_prefix} - XP_ABSORBED: Player {player_obj_process.name} absorbed {amount_to_absorb} XP. "
                                  f"Total XP: {player_obj_process.xp}, UXPs Pool: {player_obj_process.unabsorbed_xp}")
                        xp_needed_config = getattr(config, 'XP_LEVEL_THRESHOLDS', {})
                        xp_needed_for_next_level = xp_needed_config.get(player_obj_process.level + 1, (player_obj_process.level ** 2) * 100 + 100)
                        if player_obj_process.xp >= xp_needed_for_next_level:
                            player_obj_process.level += 1
                            player_obj_process.add_message(f"**Congratulations! You have reached level {player_obj_process.level}!**", "level_up_major")
                            if hasattr(player_obj_process, 'calculate_derived_stats'):
                                player_obj_process.calculate_derived_stats(GAME_RACES, GAME_ITEMS) # Pass GAME_ITEMS
                            if hasattr(player_obj_process, 'calculate_training_points'):
                                player_obj_process.calculate_training_points(GAME_RACES)
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

def broadcast_to_room(room_id, message_text, message_type="ambient_other_player", exclude_sids=None):
    if exclude_sids is None: exclude_sids = []
    try: room_id_int = int(room_id)
    except ValueError:
        if config.DEBUG_MODE: print(f"DEBUG BROADCAST_TO_ROOM: Invalid room_id format '{room_id}'.")
        return
    for sid_broadcast, player_obj_broadcast in active_players.items():
        if hasattr(player_obj_broadcast, 'current_room_id') and player_obj_broadcast.current_room_id == room_id_int and sid_broadcast not in exclude_sids:
            player_obj_broadcast.add_message(message_text, message_type)

def get_opposite_direction(direction: str) -> str:
    direction_lower = str(direction).lower()
    opposites = {"north": "the south", "south": "the north", "east": "the west", "west": "the east", "up": "below", "down": "above", "northeast": "the southwest", "northwest": "the southeast", "southeast": "the northwest", "southwest": "the northeast", "in": "out", "out": "in"}
    return opposites.get(direction_lower, f"another direction ({direction_lower})")

def send_player_stats_update(player_object: player_class.Player):
    if player_object and hasattr(player_object, 'sid') and player_object.sid:
        try:
            client_data = {"raw_stats": player_object.get_client_data(GAME_RACES, GAME_ITEMS)} # Pass GAME_ITEMS
            socketio.emit('stats_update', client_data, room=player_object.sid)
        except Exception as e:
            print(f"Error sending stats update for SID {player_object.sid}: {e}")

def send_room_description(player_object: player_class.Player):
    if not player_object or not hasattr(player_object, 'sid'): return
    current_room_id = getattr(player_object, 'current_room_id', config.DEFAULT_START_ROOM_ID)
    if not isinstance(current_room_id, int):
        try: current_room_id = int(current_room_id)
        except ValueError: current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        player_object.current_room_id = current_room_id
    
    room_data = GAME_ROOMS.get(current_room_id) # Get the current state of the room
    if not room_data:
        player_object.add_message(f"Error: You are in an unknown room (ID: {current_room_id})! Moving to safety...", "error_critical")
        player_object.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        if player_handler: player_handler.save_player(player_object)
        room_data = GAME_ROOMS.get(player_object.current_room_id)
        if not room_data:
            player_object.add_message({"name": "Lost", "description": "You are utterly lost. Contact an admin.", "type": "error_critical"})
            return

    final_room_description = environment_system.get_description_for_room(room_data)
    all_present_names = [p.name for sid, p in active_players.items() if hasattr(p, 'current_room_id') and p.current_room_id == current_room_id and sid != player_object.sid]

    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template and not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key):
            all_present_names.append(npc_template.get("name", npc_key))
    # Display Monsters
    alive_monster_counts = {}
    monster_names_list_for_room_desc = []
    # This assumes room_data.get("monsters") contains runtime IDs or keys of *active* monsters in the room.
    # If it's just template keys for *potential* spawns, this logic needs to check an active instance list.
    # Let's assume for now your respawn logic correctly populates room_data["monsters"] with active monster IDs or templates.
    # The following logic is more for when room_data["monsters"] is a list of template keys and needs disambiguation.
    # A better approach is if room_data["monsters"] contains actual monster instances or unique runtime IDs.
    # For now, sticking to a slightly modified version of your existing logic:

    active_monsters_in_room = []
    for i, monster_tpl_key_or_runtime_id in enumerate(room_data.get("monsters", [])):
        # This part needs to be robust whether monster_tpl_key_or_runtime_id is a template key or a unique runtime ID
        # Let's assume it's a template key for now, and we derive a runtime_id for defeat tracking.
        # A better system would have monster instances in the room object itself.
        monster_template = GAME_MONSTER_TEMPLATES.get(monster_tpl_key_or_runtime_id) # Try as template key first
        is_runtime_id_style = False
        if not monster_template: # Maybe it's already a runtime ID that implies its template
            # TODO: If monster_tpl_key_or_runtime_id is a runtime ID, you'd need to parse it to get the template key.
            # For now, this part is simplified.
            pass

        if monster_template:
            # Construct a conceptual runtime_id for checking defeat, this might differ from your actual runtime_id scheme
            # Your combat system should populate RECENTLY_DEFEATED_TARGETS_IN_ROOM with consistent runtime IDs.
            # If room_data.get("monsters") holds runtime_ids of active monsters:
            #   monster_runtime_id_to_check = monster_tpl_key_or_runtime_id
            # If room_data.get("monsters") holds template_keys of monsters supposed to be there:
            monster_runtime_id_to_check = f"{current_room_id}_{monster_tpl_key_or_runtime_id}_{i}" # Example runtime_id

            if not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(monster_runtime_id_to_check):
                active_monsters_in_room.append(monster_template) # Add template for now
                base_name = monster_template.get("name", monster_tpl_key_or_runtime_id)
                alive_monster_counts[base_name] = alive_monster_counts.get(base_name, 0) + 1


    processed_for_display_in_room_desc = {} # To count "goblin 1", "goblin 2"
    for monster_template_active in active_monsters_in_room: # Iterate the filtered list
        base_name = monster_template_active.get("name", "a creature")
        if alive_monster_counts.get(base_name, 0) > 1:
            num = processed_for_display_in_room_desc.get(base_name, 0) + 1
            monster_names_list_for_room_desc.append(f"{base_name} ({num})")
            processed_for_display_in_room_desc[base_name] = num
        else:
            monster_names_list_for_room_desc.append(base_name)

    if monster_names_list_for_room_desc:
        all_present_names.extend(monster_names_list_for_room_desc)

    all_present_names.sort()
    present_entities_str = "ALSO HERE: " + ", ".join(all_present_names) + "." if all_present_names else ""

    # --- DETAILED DEBUG FOR ITEMS/OBJECTS ---
    if config.DEBUG_MODE:
        print(f"--- DEBUG SEND_ROOM_DESC (Room ID: {current_room_id}) ---")
        print(f"  Static items in room_data['items']: {room_data.get('items', [])}")
        print(f"  Dynamic objects in room_data['objects'] (keys): {list(room_data.get('objects', {}).keys())}")

    visible_item_names = []
    # 1. Static items
    for item_id_static in room_data.get("items", []):
        item_tpl_static = GAME_ITEMS.get(item_id_static)
        if item_tpl_static:
            item_name_log = item_tpl_static.get("name", item_id_static)
            visible_item_names.append(item_name_log)
            if config.DEBUG_MODE: print(f"  Added static item to visible: '{item_name_log}'")

    # 2. Dynamic objects (corpses, items on ground)
    for obj_id, obj_data_dynamic in room_data.get("objects", {}).items():
        obj_name_log = obj_data_dynamic.get("name", "unnamed object")
        is_corpse_log = obj_data_dynamic.get("is_corpse", False)
        is_ground_item_log = obj_data_dynamic.get("is_ground_item", False)
        if config.DEBUG_MODE:
            print(f"  Checking dynamic object ID '{obj_id}': Name='{obj_name_log}', is_corpse={is_corpse_log}, is_ground_item={is_ground_item_log}")
        
        if is_corpse_log or is_ground_item_log:
            visible_item_names.append(obj_name_log)
            if config.DEBUG_MODE: print(f"    Added dynamic object to visible: '{obj_name_log}' (Corpse: {is_corpse_log}, GroundItem: {is_ground_item_log})")

    # 3. Defined Room Features
    for feature_key, feature_data in room_data.get("defined_objects", {}).items():
        feature_name_log = feature_data.get("name", "unnamed feature")
        visible_item_names.append(feature_name_log)
        if config.DEBUG_MODE: print(f"  Added feature to visible: '{feature_name_log}'")
    # --- END DETAILED DEBUG ---

    items_on_ground_str = ""
    if visible_item_names:
        unique_sorted_names = sorted(list(set(visible_item_names)))
        items_on_ground_str = "YOU ALSO SEE: " + ", ".join(unique_sorted_names) + "."
        if config.DEBUG_MODE: print(f"  Final 'YOU ALSO SEE' string: {items_on_ground_str}")
    elif config.DEBUG_MODE:
        print("  No items/objects for 'YOU ALSO SEE'.")
        
    room_data_payload = {
        "name": room_data.get("name", "Nowhere Special"),
        "description": final_room_description,
        "presence_summary": present_entities_str,
        "items_summary": items_on_ground_str,
        "exits": ", ".join(k.upper() for k in room_data.get("exits", {}).keys()) or "None",
        "type": "room_data_update"
    }
    player_object.add_message(room_data_payload)
    if config.DEBUG_MODE: print(f"--- END DEBUG SEND_ROOM_DESC ---")

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    if config.DEBUG_MODE: print(f"DEBUG: Client connected: SID {sid}")
    player_creation_sessions[sid] = { "phase": "awaiting_login_name", "sid": sid, "messages_queue": [], "player_shell": None }
    emit('game_messages', { 'messages': [{"text": getattr(config, 'WELCOME_MESSAGE', "Welcome!"), "type": "system_highlight"}, {"text": "Enter 'login <name>' or 'create <name>'", "type": "prompt"}] }, room=sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid; player = active_players.get(sid)
    if player:
        last_room_id = player.current_room_id
        if player_handler and not player_handler.save_player(player): print(f"ERROR: Save failed for {player.name} ({sid}) on disconnect.")
        else:
            if config.DEBUG_MODE: print(f"DEBUG: Player {player.name} ({sid}) data saved on disconnect.")
        active_players.pop(sid, None)
        if config.DEBUG_MODE: print(f"DEBUG: Player '{player.name}' ({sid}) removed from active players.")
        broadcast_to_room(last_room_id, f"{player.name} vanished.", "ambient_player_departure", exclude_sids=[sid])
    if sid in player_creation_sessions: player_creation_sessions.pop(sid, None)
    if config.DEBUG_MODE: print(f"DEBUG: Client SID {sid} session fully closed after disconnect.")

def finalize_character_creation(sid, player_shell: player_class.Player, game_races_data: dict, game_items_data: dict):
    session = player_creation_sessions.get(sid)
    if not player_shell:
        if sid: emit('game_messages', {'messages': [{"text": "Error finalizing character.", "type": "error_critical"}]}, room=sid)
        if session: player_creation_sessions.pop(sid, None)
        return

    race_key = player_shell.race
    race_data = game_races_data.get(race_key)
    if race_data:
        if not hasattr(player_shell, 'skills'): player_shell.skills = getattr(config, 'INITIAL_SKILLS', {}).copy()
        for skill, bonus in race_data.get("skill_bonuses", {}).items():
            player_shell.skills[skill] = player_shell.skills.get(skill, 0) + bonus
        if not hasattr(player_shell, 'inventory'): player_shell.inventory = []
        for item_key_inv in race_data.get("bonus_inventory", []):
            if item_key_inv in game_items_data: player_shell.inventory.append(item_key_inv)

        start_zone_id_from_race = race_data.get("starting_zone_id")
        default_start_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        final_start_room = default_start_room_id
        if start_zone_id_from_race is not None:
            try:
                start_zone_id_int = int(start_zone_id_from_race)
                if start_zone_id_int in GAME_ROOMS: final_start_room = start_zone_id_int
                else: player_shell.add_message(f"Race starting area '{start_zone_id_from_race}' unknown; using default.", "system_warning")
            except ValueError: player_shell.add_message(f"Race starting area config invalid; using default.", "system_warning")
        player_shell.current_room_id = final_start_room
    else: player_shell.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)

    if hasattr(player_shell, 'calculate_derived_stats'):
        player_shell.calculate_derived_stats(game_races_data, game_items_data)

    player_shell.hp = getattr(player_shell, 'max_hp', 10)
    player_shell.mp = getattr(player_shell, 'max_mp', 0)
    player_shell.sp = getattr(player_shell, 'max_sp', 0)

    if hasattr(player_shell, 'calculate_training_points'):
        player_shell.calculate_training_points(game_races_data)

    player_shell.creation_phase = None

    if player_handler.save_player(player_shell):
        active_players[sid] = player_shell
        if session: player_creation_sessions.pop(sid, None)
        player_shell.add_message(f"Character {player_shell.name} created successfully!", "event_highlight")
        broadcast_to_room(player_shell.current_room_id, f"{player_shell.name} appears.", "ambient_player_arrival", exclude_sids=[sid])
        send_room_description(player_shell)
        final_messages = player_shell.get_queued_messages()
        if final_messages: emit('game_messages', {'messages': final_messages}, room=sid)
        send_player_stats_update(player_shell)
    else:
        error_msg = "A critical error occurred saving your character."
        player_shell.add_message(error_msg, "error_critical")
        emit('game_messages', {'messages': player_shell.get_queued_messages()}, room=sid)


# Helper function to add an item object to the room (if not already there)
def add_item_object_to_room(room_data, item_id, game_items_data):
    item_template = game_items_data.get(item_id)
    if not item_template:
        if config.DEBUG_MODE: print(f"DEBUG ADD_ITEM_TO_ROOM: Item template for '{item_id}' not found.")
        return None

    ground_item_instance_id = f"ground_{item_id}_{int(time.time())}_{random.randint(1000,9999)}"
    
    item_object_data = {
        "id": ground_item_instance_id,
        "item_template_id": item_id,
        "name": item_template.get("name", item_id),
        "description": item_template.get("look_description_ground", item_template.get("description", "An item lies here.")),
        "keywords": item_template.get("keywords", []) + [item_template.get("name", item_id).lower()],
        "is_ground_item": True,
        "is_container": item_template.get("is_container", False),
        "inventory": list(item_template.get("inventory", [])) if item_template.get("is_container") else [],
        "created_at": time.time()
    }
    
    room_data.setdefault("objects", {})[ground_item_instance_id] = item_object_data
    if config.DEBUG_MODE:
        print(f"DEBUG ADD_ITEM_TO_ROOM: Added '{item_object_data['name']}' (ID: {ground_item_instance_id}) to room {room_data.get('id')}.")
    return item_object_data

def find_combat_target_in_room(player_object: player_class.Player, target_name_query: str, room_data: dict):
    # ... (This function was updated in my previous response to include player targeting - ensure those changes are present) ...
    if not target_name_query: return None, None, None, None
    target_name_lower = target_name_query.lower()
    current_room_id = player_object.current_room_id
    if not isinstance(current_room_id, int):
        try: current_room_id = int(current_room_id)
        except ValueError: current_room_id = 0

    # Priority 1: Find other players
    for other_sid, other_player_obj in active_players.items():
        if other_sid != player_object.sid and \
           hasattr(other_player_obj, 'current_room_id') and other_player_obj.current_room_id == current_room_id and \
           hasattr(other_player_obj, 'name') and other_player_obj.name.lower() == target_name_lower:
            return other_player_obj, "player", other_player_obj.sid, None

    # Priority 2: Find NPCs
    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template:
            name_lower = npc_template.get("name", "").lower()
            keywords = [k.lower() for k in npc_template.get("keywords", [])]
            if name_lower == target_name_lower or target_name_lower in keywords or npc_key.lower() == target_name_lower:
                if combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key): continue
                return npc_template, "npc", npc_key, None

    # Priority 3: Find Monsters (Needs robust runtime ID handling)
    query_base_name = target_name_lower
    query_instance_num = None
    parts = target_name_lower.split()
    if len(parts) > 1 and parts[-1].isdigit():
        try:
            num_part = int(parts[-1])
            if num_part > 0:
                query_instance_num = num_part
                query_base_name = " ".join(parts[:-1])
        except ValueError: pass

    living_monster_matches = []
    # This part needs to iterate actual monster instances in the room, not just templates.
    # Assuming for now, GAME_ROOMS[current_room_id]["monsters_present"] holds dicts of active monsters {runtime_id: monster_object}
    # This is a conceptual change from just listing template keys in room_data.get("monsters", [])
    
    # Simplified version if room_data["monsters"] is list of template keys (less ideal for multiple same-type monsters)
    # This will need to align with how your respawn and monster management works.
    active_monster_instances_in_room = [] # This should ideally be populated by your game state / respawn system.
                                          # For now, we'll conceptually work with room_data.get("monsters", [])
                                          # if they are supposed to be runtime instances.

    # Let's assume for now you store runtime_ids of monsters in current_room_data.get("monsters_active_runtime_ids", [])
    # and each of those runtime_ids can be used to fetch the monster's current state and template.
    # This part is highly dependent on your monster instancing and tracking.
    # The version from your file uses enumerate on room_data.get("monsters", [])
    
    for i, m_tpl_key in enumerate(room_data.get("monsters", [])): # From your file
        m_template = GAME_MONSTER_TEMPLATES.get(m_tpl_key)
        if not m_template: continue
        m_name_lower = m_template.get("name", "").lower()
        m_keywords = [k.lower() for k in m_template.get("keywords", [])]
        # This runtime_id needs to be the one used by combat and respawn tracking
        runtime_id = f"{current_room_id}_{m_tpl_key}_{i}" # Example, ensure it matches your system

        if not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(runtime_id):
            if m_name_lower == query_base_name or query_base_name in m_keywords or m_tpl_key.lower() == query_base_name:
                living_monster_matches.append({
                    "template": m_template, "type": "monster", "key": m_tpl_key,
                    "runtime_id": runtime_id, "instance_index_in_room_list": i
                })

    if not living_monster_matches: return None, None, None, None
    if query_instance_num is not None:
        count = 0
        for m_match in living_monster_matches:
            # Match against the base name for numbered targets
            if m_match["template"].get("name","").lower() == query_base_name or \
               query_base_name in [k.lower() for k in m_match["template"].get("keywords",[])]:
                count += 1
                if count == query_instance_num:
                    return m_match["template"], m_match["type"], m_match["key"], m_match
        return None, None, None, None
    else:
        m_match = living_monster_matches[0]
        return m_match["template"], m_match["type"], m_match["key"], m_match

    return None, None, None, None


def find_object_in_room(player_obj, target_name_query: str, room_data_dict: dict):
    # ... (This function seems mostly fine from your file, ensure it supports is_ground_item) ...
    if not target_name_query or not room_data_dict: return None, None
    target_lower = target_name_query.lower()

    # Priority 1: Dynamic Room Objects (corpses, items on ground)
    for obj_id, obj_data in room_data_dict.get("objects", {}).items():
        obj_name_lower = obj_data.get("name", "").lower()
        name_match = obj_name_lower == target_lower
        keywords = [k.lower() for k in obj_data.get("keywords", [])]
        keyword_match = target_lower in keywords
        id_match = obj_id.lower() == target_lower # If obj_id is used for targeting

        # Match for "corpse" or original name of corpse
        original_name_or_generic_corpse_match = False
        if obj_data.get("is_corpse"):
            original_name = obj_data.get("original_name", "").lower()
            if target_lower == "corpse" or target_lower == original_name or target_lower in original_name.split():
                original_name_or_generic_corpse_match = True
        
        # Match for items on ground by their name or template_id
        # This might be redundant if ground items also have good keywords.
        is_ground_item_name_match = False
        if obj_data.get("is_ground_item"):
            item_template_id = obj_data.get("item_template_id", "")
            if target_lower == item_template_id.lower(): # Match by template ID
                 is_ground_item_name_match = True


        if name_match or keyword_match or id_match or original_name_or_generic_corpse_match or is_ground_item_name_match:
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
                    "is_static_item": True, "keywords": item_keywords
                }

    # Priority 3: Defined Room Features (room_data["defined_objects"])
    for feature_key, feature_data in room_data_dict.get("defined_objects", {}).items():
        feature_name_lower = feature_data.get("name", "").lower()
        feature_keywords = [k.lower() for k in feature_data.get("keywords", [])]
        if feature_key.lower() == target_lower or feature_name_lower == target_lower or target_lower in feature_keywords:
            return feature_key, feature_data
            
    return None, None

@socketio.on('player_command')
def handle_player_command(data):
    sid = request.sid
    command_input = data.get('command', '').strip()
    if config.DEBUG_MODE: print(f"\nDEBUG CMD: SID={sid}, Command='{command_input}'")
    if not command_input: return

    try:
        player = active_players.get(sid)
        session = player_creation_sessions.get(sid)

        if player: # Player is active and logged in
            player.add_message(f"> {command_input}", "echo")
            if hasattr(player, 'next_action_time') and time.time() < player.next_action_time:
                player.add_message(f"Wait {max(0.0, round(player.next_action_time - time.time(), 1))}s.", "error_rt")
            else:
                parts = command_input.lower().split(" ", 1)
                verb = parts[0]
                raw_target_arg = parts[1].strip() if len(parts) > 1 else None
                target_arg = None

                if raw_target_arg:
                    if verb == "say":
                        target_arg = parts[1].strip()
                    else:
                        look_verbs = ["look", "l", "examine", "ex", "exa"]
                        action_verbs_with_target = [
                            "search", "attack", "get", "take", "drop", "talk", "give",
                            "open", "close", "enter", "use", "read", "cast", "climb",
                            "skin", "equip", "unequip", "wear", "remove"
                        ]
                        if verb in look_verbs and raw_target_arg.startswith("at ") and len(raw_target_arg) > 3:
                            target_arg = raw_target_arg[3:].strip()
                        elif verb in action_verbs_with_target or verb in look_verbs:
                            target_arg = raw_target_arg
                        elif raw_target_arg:
                             target_arg = raw_target_arg

                if config.DEBUG_MODE: print(f"DEBUG CMD PARSED: Verb='{verb}', TargetArg='{target_arg}' (RawTarget='{raw_target_arg}')")

                room_id_before_move = player.current_room_id
                current_room_data = GAME_ROOMS.get(room_id_before_move)
                action_taken = False

                if not current_room_data:
                    player.add_message(f"Error: You are in an unknown room (ID: {room_id_before_move})! Moving to safety...", "error_critical")
                    player.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
                    if player_handler: player_handler.save_player(player)
                    current_room_data = GAME_ROOMS.get(player.current_room_id)
                    if not current_room_data:
                        player.add_message("PANIC: Default room is also invalid. Please contact an administrator.", "error_critical")
                        all_msgs_panic = player.get_queued_messages()
                        if all_msgs_panic: socketio.emit('game_messages', {'messages': all_msgs_panic}, room=sid)
                        return
                    send_room_description(player)
                    all_msgs_after_move = player.get_queued_messages() # Get messages from send_room_description
                    if all_msgs_after_move: socketio.emit('game_messages', {'messages': all_msgs_after_move}, room=sid)
                    send_player_stats_update(player) # Update stats too
                    return # End processing for this command after critical room error and move

                # --- START OF PLAYER-COMMAND IF/ELIF CHAIN ---
                if verb == "attack":
                    action_taken = True
                    rt_look = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                    rt_attack = config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
                    if not target_arg:
                        player.add_message("Attack whom or what?", "error")
                        player.next_action_time = time.time() + rt_look
                    else:
                        target_data, target_type, target_id_or_key, target_full_match_data = find_combat_target_in_room(player, target_arg, current_room_data)
                        if target_data:
                            if target_type == "player":
                                target_player_object = target_data
                                if not current_room_data.get("pvp", False):
                                    player.add_message("You cannot engage in combat with other adventurers here.", "error_pvp")
                                    player.next_action_time = time.time() + rt_look
                                elif target_player_object.sid == player.sid:
                                     player.add_message("Attacking yourself seems unproductive.", "feedback_neutral")
                                     player.next_action_time = time.time() + rt_look
                                else:
                                    if config.DEBUG_MODE: print(f"DEBUG PVP: {player.name} initiating attack on {target_player_object.name}")
                                    combat_results = {}
                                    try: # TODO: Implement combat.handle_pvp_attack
                                        player.add_message("PvP combat is not yet fully implemented.", "error_dev") # Placeholder
                                        # combat_results = combat.handle_pvp_attack(player, target_player_object, GAME_ITEMS)
                                    except AttributeError:
                                        player.add_message("PvP combat system is not yet fully implemented.", "error_dev")
                                        if config.DEBUG_MODE: print("DEBUG PVP: combat.handle_pvp_attack is not yet implemented.")
                                    except Exception as pvp_e:
                                        player.add_message("An error occurred during PvP combat.", "error_critical")
                                        if config.DEBUG_MODE: print(f"ERROR PVP combat: {pvp_e}"); traceback.print_exc()
                                    player.next_action_time = time.time() + rt_attack # Always set RT for attack attempt
                            elif target_type == "monster" or target_type == "npc":
                                monster_runtime_id_for_combat = target_id_or_key
                                if target_type == "monster" and target_full_match_data:
                                    monster_runtime_id_for_combat = target_full_match_data.get("runtime_id", target_id_or_key)
                                combat_results = combat.handle_player_attack(
                                    player, target_data, target_type, target_arg, GAME_ITEMS,
                                    monster_runtime_id=monster_runtime_id_for_combat
                                )
                                if combat_results.get('broadcast_message'): broadcast_to_room(player.current_room_id, combat_results['broadcast_message'], "ambient_combat", [player.sid])
                                if combat_results.get('defeated') and not combat_results.get('already_defeated'):
                                    defeated_runtime_id_from_combat = combat_results.get('target_runtime_id')
                                    target_display_name_from_combat = combat_results.get('target_name', 'the creature')
                                    defeated_entity_template = target_data
                                    if config.DEBUG_MODE: print(f"DEBUG MAIN_DEFEAT: {player.name} def. {target_display_name_from_combat} (Key:{target_id_or_key}, RuntimeID: {defeated_runtime_id_from_combat})")
                                    if defeated_entity_template:
                                        xp_to_award = defeated_entity_template.get("xp_value", defeated_entity_template.get("xp_on_kill", 0))
                                        if xp_to_award > 0 and hasattr(player, 'add_xp_to_pool'): player.add_xp_to_pool(xp_to_award, GAME_RACES)
                                        for hit_faction in defeated_entity_template.get("faction_hits_on_kill", []):
                                            if isinstance(hit_faction, dict) and hit_faction.get("faction_id") and isinstance(hit_faction.get("amount"), int):
                                                if hasattr(player, 'update_faction'): player.update_faction(hit_faction["faction_id"], hit_faction["amount"])
                                        if defeated_entity_template.get("leaves_corpse", True):
                                            corpse_data = loot_handler.create_corpse_object_data(
                                                defeated_entity_template, defeated_runtime_id_from_combat, GAME_ITEMS
                                            )
                                            if corpse_data and current_room_data:
                                                current_room_data.setdefault("objects", {})[corpse_data["id"]] = corpse_data
                                                player.add_message(f"The {target_display_name_from_combat} slumps, leaving a corpse.", "event_defeat_corpse")
                                        else: player.add_message(f"The {target_display_name_from_combat} collapses into nothingness!", "event_defeat")
                                    else: player.add_message(f"You defeated {target_display_name_from_combat}, but its essence fades.", "event_defeat_major")
                                    if defeated_runtime_id_from_combat and defeated_entity_template:
                                        spawn_cfg = defeated_entity_template.get("spawn_config", {})
                                        if not spawn_cfg and target_type == "monster":
                                            spawn_cfg = {"respawn_time_seconds": defeated_entity_template.get("respawn_time_seconds"),
                                                         "spawn_chance": defeated_entity_template.get("respawn_chance"), "home_room_id": defeated_entity_template.get("home_room_id")}
                                        respawn_time_val = spawn_cfg.get("respawn_time_seconds")
                                        if respawn_time_val is not None:
                                            home_room_id_for_respawn = spawn_cfg.get("home_room_id", player.current_room_id)
                                            TRACKED_DEFEATED_ENTITIES[defeated_runtime_id_from_combat] = {
                                                "eligible_at": time.time() + float(respawn_time_val), "room_id": home_room_id_for_respawn,
                                                "template_key": target_id_or_key, "type": target_type,
                                                "is_unique": defeated_entity_template.get("is_unique", False),
                                                "chance": float(spawn_cfg.get("spawn_chance", getattr(config, 'DEFAULT_RESPAWN_CHANCE', 0.2))),
                                            }
                                            if config.DEBUG_MODE: print(f"DEBUG MAIN_RESPAWN: Added '{defeated_runtime_id_from_combat}' to TRACKED_DEFEATED_ENTITIES.")
                                player.next_action_time = time.time() + rt_attack
                            else:
                                player.add_message("You can't attack that!", "error")
                                player.next_action_time = time.time() + rt_look
                        else:
                            player.add_message(f"You don't see '{target_arg}' to attack.", "error")
                            player.next_action_time = time.time() + rt_look
                
                elif verb == "equip" or verb == "wear":
                    action_taken = True
                    rt_equip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                    player.next_action_time = time.time() + rt_equip
                    if not target_arg:
                        player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword mainhand)", "error")
                    else:
                        parts_equip = target_arg.split(" ", 1)
                        item_query_from_player = parts_equip[0]
                        item_query_lower = item_query_from_player.lower()
                        slot_to_equip_player_input = parts_equip[1].lower().strip() if len(parts_equip) > 1 else None
                        actual_item_id_to_equip = None

                        if item_query_lower in player.inventory and GAME_ITEMS.get(item_query_lower):
                            actual_item_id_to_equip = item_query_lower
                        if not actual_item_id_to_equip:
                            for item_id_in_inv in player.inventory:
                                item_template_inv = GAME_ITEMS.get(item_id_in_inv)
                                if item_template_inv and item_template_inv.get("name", "").lower() == item_query_lower:
                                    actual_item_id_to_equip = item_id_in_inv; break
                        if not actual_item_id_to_equip:
                            for item_id_in_inv in player.inventory:
                                item_template_inv = GAME_ITEMS.get(item_id_in_inv)
                                if item_template_inv:
                                    keywords = [k.lower() for k in item_template_inv.get("keywords", [])]
                                    if item_query_lower in keywords:
                                        actual_item_id_to_equip = item_id_in_inv; break
                        
                        if not actual_item_id_to_equip:
                            player.add_message(f"You don't have a '{item_query_from_player}'.", "error")
                        else:
                            final_slot_to_use = None
                            if slot_to_equip_player_input:
                                if slot_to_equip_player_input in config.EQUIPMENT_SLOTS.keys():
                                    final_slot_to_use = slot_to_equip_player_input
                                else:
                                    player.add_message(f"'{parts_equip[1]}' is not a valid slot. Valid: {', '.join(config.EQUIPMENT_SLOTS.keys())}", "error")
                            else:
                                item_template_for_inference = GAME_ITEMS.get(actual_item_id_to_equip)
                                if item_template_for_inference:
                                    preferred_item_slots = item_template_for_inference.get("slot", [])
                                    if not isinstance(preferred_item_slots, list): preferred_item_slots = [preferred_item_slots]
                                    if preferred_item_slots and preferred_item_slots[0] in config.EQUIPMENT_SLOTS.keys():
                                        final_slot_to_use = preferred_item_slots[0]
                                    else:
                                        player.add_message(f"{verb.capitalize()} the {item_template_for_inference.get('name',item_query_from_player)} where?", "error")
                                else:
                                    player.add_message(f"Error with '{item_query_from_player}' for slot inference.", "error_critical")
                            
                            if actual_item_id_to_equip and final_slot_to_use:
                                if hasattr(player, 'equip_item'):
                                    player.equip_item(actual_item_id_to_equip, final_slot_to_use, GAME_ITEMS, GAME_RACES)
                                else:
                                    player.add_message("Player equipment system error.", "error_critical")
                
                elif verb == "unequip" or verb == "remove":
                    action_taken = True
                    # ... (Your full unequip logic from previous successful iteration) ...
                    player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)

                elif verb == "loot": 
                    action_taken = True 
                    if not target_arg: 
                        player.add_message("Loot what? (e.g., loot corpse, loot rat corpse)", "error")
                        player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                    else: 
                        verb = "search" # Redirect, search block will handle the rest
                
                if verb == "search": # Handles direct "search" AND redirected "loot <target>"
                    action_taken = True 
                    rt_search_default = getattr(config, 'SEARCH_BASE_ROUNDTIME', 1.5); # ... (rest of RT calc) ...
                    player.next_action_time = time.time() + rt_search_default # Placeholder, use final_search_rt

                    if not target_arg: 
                        player.add_message("Search what?", "error") # Should be caught by loot alias if original was 'loot'
                    elif not current_room_data: 
                        player.add_message("You can't search anything here.", "error")
                    else:
                        # ... (Your full search logic, including calling send_room_description if items spill) ...
                        obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                        if obj_data:
                            target_display_name_search = obj_data.get("name", target_arg)
                            if obj_data.get("is_corpse"):
                                # ... (full corpse search logic as previously provided, including gold and item spilling messages)
                                # ... DONT FORGET to call send_room_description(player) if items_moved_to_ground_names is true
                                pass # Placeholder for your detailed search logic here
                            # ... (else for other searchable objects)
                        else:
                            player.add_message(f"You don't see '{target_arg}' to search.", "error")
                
                elif verb in ["get", "take"]:
                    action_taken = True
                    # ... (your get/take logic, ensure player.next_action_time is set) ...
                    player.next_action_time = time.time() + getattr(config, 'GET_BASE_ROUNDTIME', 0.5)

                elif verb in ["look", "l", "examine", "exa", "look at"]: # Added "look at"
                    action_taken = True
                    rt_look_cmd = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                    player.next_action_time = time.time() + rt_look_cmd

                    # Handle "look at me", "look at self", "look at <player.name>"
                    if target_arg and (target_arg.lower() == "me" or target_arg.lower() == "self" or target_arg.lower() == player.name.lower()):
                        player.add_message(f"You look at yourself, {player.name}.", "feedback_look_self")
                        # Get player's race name for display
                        race_name_display = player.race.title()
                        if hasattr(player, 'race_data') and player.race_data and player.race_data.get('name'):
                            race_name_display = player.race_data.get('name')
                        elif GAME_RACES.get(player.race): # Fallback to global GAME_RACES
                            race_name_display = GAME_RACES[player.race].get('name', player.race.title())
                        player.add_message(f"You are a {race_name_display}.", "info")
                        
                        equipped_items_display = []
                        for slot_key_disp, item_id_disp in player.equipped_items.items():
                            if item_id_disp:
                                item_template_disp = GAME_ITEMS.get(item_id_disp)
                                item_name_disp = item_template_disp.get("name", item_id_disp) if item_template_disp else item_id_disp
                                slot_display_name = config.EQUIPMENT_SLOTS.get(slot_key_disp, slot_key_disp).split(" (")[0] # Cleaner slot name
                                equipped_items_display.append(f"  <{slot_display_name.lower()}> {item_name_disp}")
                        
                        if equipped_items_display:
                            player.add_message("You are wearing:", "header_info_block")
                            for line in sorted(equipped_items_display): player.add_message(line, "info_block_content")
                        else:
                            player.add_message("You are not wearing anything of note.", "info_block_content")
                    elif target_arg and current_room_data: # Original logic for looking at other things
                        target_entity_data_look, entity_type_look, _, _ = find_combat_target_in_room(player, target_arg, current_room_data)
                        if target_entity_data_look:
                            look_desc_entity = target_entity_data_look.get("look_description", target_entity_data_look.get("description"))
                            if not look_desc_entity: look_desc_entity = f"You see {target_entity_data_look.get('name', target_arg)}."
                            if entity_type_look in ["npc", "monster"] and target_entity_data_look.get("equipped"):
                                equipped_str_parts_look = []
                                for slot_key_look, item_id_look in target_entity_data_look.get("equipped",{}).items():
                                    if item_id_look:
                                        item_data_look = GAME_ITEMS.get(item_id_look)
                                        if item_data_look:
                                            slot_name_look = config.EQUIPMENT_SLOTS.get(slot_key_look, slot_key_look).split(" (")[0]
                                            equipped_str_parts_look.append(f"<{slot_name_look.lower()}> {item_data_look.get('name',item_id_look)}")
                                if equipped_str_parts_look:
                                    look_desc_entity += "\nThey are equipped with:\n" + "\n".join(sorted(equipped_str_parts_look))
                            player.add_message(look_desc_entity, "feedback_look_target")
                        else: 
                            obj_id_look, obj_data_look = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data_look:
                                look_desc_obj = obj_data_look.get("description", "You see nothing special about it.")
                                if obj_data_look.get("is_corpse") and obj_data_look.get("inventory") and not obj_data_look.get("searched_and_emptied", False):
                                    look_desc_obj += " It looks like it might have something on it."
                                elif obj_data_look.get("is_container") and obj_data_look.get("inventory"):
                                    look_desc_obj += " It contains:\n"
                                    for item_id_in_cont in obj_data_look["inventory"]:
                                        item_tpl_in_cont = GAME_ITEMS.get(item_id_in_cont)
                                        look_desc_obj += f"  - {item_tpl_in_cont.get('name', item_id_in_cont) if item_tpl_in_cont else item_id_in_cont}\n"
                                player.add_message(look_desc_obj, "feedback_look_target")
                            else: player.add_message(f"You don't see '{target_arg}' here.", "error")
                    else: 
                        send_room_description(player)
                
                elif verb == "climb": # Specific "climb" verb for object interaction
                    action_taken = True
                    rt_climb = config.ROUNDTIME_DEFAULTS.get('roundtime_action_medium', 1.5) # Example RT
                    player.next_action_time = time.time() + rt_climb

                    if not target_arg:
                        player.add_message("Climb what?", "error")
                    elif not current_room_data:
                        player.add_message("There's nothing to climb here.", "error")
                    else:
                        # Try to find the object based on target_arg (e.g., "rope", "ladder")
                        obj_id_climb, obj_data_climb = find_object_in_room(player, target_arg, current_room_data)
                        
                        # More specific check for "climb rope down"
                        # command_input is the original full command from player
                        full_action_key = command_input.lower() # e.g., "climb rope down"

                        if obj_data_climb and obj_data_climb.get("interactable") and obj_data_climb.get("actions"):
                            action_to_perform = None
                            if full_action_key in obj_data_climb["actions"]: # Exact match for "climb rope down"
                                action_to_perform = full_action_key
                            elif target_arg and verb + " " + target_arg.split(" ")[0] in obj_data_climb["actions"]: # For "climb rope"
                                action_to_perform = verb + " " + target_arg.split(" ")[0]

                            if action_to_perform:
                                action_result = obj_data_climb["actions"][action_to_perform]
                                if isinstance(action_result, int): # If it's a room ID for movement
                                    destination_room_id = action_result
                                    player.add_message(f"You {action_to_perform}.", "feedback_move") 
                                    broadcast_to_room(room_id_before_move, f"{player.name} {action_to_perform}.", "ambient_player_action", [sid])
                                    player.current_room_id = destination_room_id
                                    new_room_data_check = GAME_ROOMS.get(destination_room_id)
                                    if new_room_data_check:
                                        arrival_message = f"{player.name} arrives." 
                                        if "down" in action_to_perform: arrival_message = f"{player.name} climbs down."
                                        elif "up" in action_to_perform: arrival_message = f"{player.name} climbs up."
                                        broadcast_to_room(destination_room_id, arrival_message, "ambient_player_arrival", [sid])
                                        send_room_description(player)
                                    else:
                                        player.add_message("The way seems to lead nowhere...", "error_move")
                                        player.current_room_id = room_id_before_move 
                                elif isinstance(action_result, str):
                                    player.add_message(f"You interact with the {obj_data_climb.get('name', 'object')}... (Event: '{action_result}' - not handled).", "feedback_neutral")
                                else:
                                    player.add_message(f"You try to {action_to_perform} the {obj_data_climb.get('name', 'object')}, but nothing happens.", "feedback_neutral")
                            else: # No specific "climb <detail>" action found on the object
                                player.add_message(f"You can't seem to '{command_input}' the {obj_data_climb.get('name', 'object') if obj_data_climb else target_arg}.", "error")
                        else: # Object not found or not interactable for climbing
                            player.add_message(f"You don't see '{target_arg}' to climb here, or cannot interact with it that way.", "error")
                
                elif verb == "drop":
                    action_taken = True
                    rt_drop = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 0.5)
                    player.next_action_time = time.time() + rt_drop
                    if not target_arg:
                        player.add_message("Drop what?", "error")
                    elif not current_room_data:
                        player.add_message("You can't drop items in the void!", "error")
                    else:
                        item_id_to_drop = None
                        item_query_lower_drop = target_arg.lower()
                        # Check inventory for the item by ID, then by name, then by keyword
                        if item_query_lower_drop in player.inventory and GAME_ITEMS.get(item_query_lower_drop):
                            item_id_to_drop = item_query_lower_drop
                        if not item_id_to_drop:
                            for item_id_inv in player.inventory:
                                item_tpl = GAME_ITEMS.get(item_id_inv)
                                if item_tpl and item_tpl.get("name", "").lower() == item_query_lower_drop:
                                    item_id_to_drop = item_id_inv; break
                        if not item_id_to_drop:
                            for item_id_inv in player.inventory:
                                item_tpl = GAME_ITEMS.get(item_id_inv)
                                if item_tpl and item_query_lower_drop in [k.lower() for k in item_tpl.get("keywords", [])]:
                                    item_id_to_drop = item_id_inv; break
                        
                        if item_id_to_drop:
                            item_template_dropped = GAME_ITEMS.get(item_id_to_drop)
                            item_name_dropped = item_template_dropped.get("name", item_id_to_drop) if item_template_dropped else item_id_to_drop
                            
                            dropped_item_obj_data = add_item_object_to_room(current_room_data, item_id_to_drop, GAME_ITEMS)
                            if dropped_item_obj_data:
                                player.inventory.remove(item_id_to_drop)
                                player.add_message(f"You drop the {item_name_dropped}.", "feedback_drop_item")
                                broadcast_to_room(player.current_room_id, f"{player.name} drops a {item_name_dropped}.", "ambient_other_player", [sid])
                                send_player_stats_update(player) # Update inventory count on client
                                send_room_description(player) # Update room view
                            else:
                                player.add_message(f"You try to drop the {item_name_dropped}, but it seems stuck to you!", "error") # Should not happen if add_item_object_to_room works
                        else:
                            player.add_message(f"You don't have a '{target_arg}' to drop.", "error")

                elif verb == "say":
                    action_taken = True
                    # ... (your say logic as before) ...
                elif verb == "quit":
                    action_taken = True
                    # ... (your quit logic as before) ...
                    return

                elif verb == "inventory" or verb == "i" or verb == "inv":
                    action_taken = True
                    # ... (your inventory logic as before) ...
                elif verb == "help" or verb == "commands":
                    action_taken = True
                    # ... (your help logic as before) ...
                elif verb == "experience" or verb == "xp":
                    action_taken = True
                    # ... (your experience logic as before) ...
                elif verb == "health" or verb == "hp":
                    action_taken = True
                    # ... (your health logic as before) ...
                elif verb == "mana" or verb == "mp":
                    action_taken = True
                    # ... (your mana logic as before) ...
                elif verb == "stats" or verb == "score" or verb == "character" or verb == "info":
                    action_taken = True
                    # ... (your stats logic as before) ...
                elif verb == "factions" or verb == "faction":
                    action_taken = True
                    # ... (your factions logic as before) ...
                elif verb == "exits":
                    action_taken = True
                    # ... (your exits logic as before) ...

                # --- MOVEMENT HANDLING (MUST BE LATE in the chain) ---
                elif current_room_data and verb in current_room_data.get("exits", {}): 
                    action_taken = True
                    # ... (your movement logic as before) ...
                
                if not action_taken:
                    player.add_message(f"You can't seem to '{command_input}' here. (Type 'help' for commands)", "error")
                    player.next_action_time = time.time() + 0.1 
            
            all_msgs = player.get_queued_messages()
            if all_msgs: socketio.emit('game_messages', {'messages': all_msgs}, room=sid)
            send_player_stats_update(player) 

        elif session: 
            # ... (Your existing and correct session/character creation logic - NO CHANGES NEEDED INSIDE THIS BLOCK for these verb fixes)
            player_shell = session.get("player_shell")
            current_phase = session.get("phase")

            def send_creation_messages(s_id, sess, p_shell):
                messages_to_client = []
                if "messages_queue" in sess and sess["messages_queue"]:
                    messages_to_client.extend(sess["messages_queue"])
                    sess["messages_queue"] = []
                if p_shell and hasattr(p_shell, "get_queued_messages"):
                    messages_to_client.extend(p_shell.get_queued_messages())
                if messages_to_client:
                    socketio.emit('game_messages', {'messages': messages_to_client}, room=s_id)

            if not player_shell and current_phase == "awaiting_login_name":
                parts_initial = command_input.split(" ", 1); verb_initial = parts_initial[0].lower()
                name_arg_initial = parts_initial[1].strip().title() if len(parts_initial) > 1 and parts_initial[1].strip() else ""

                if verb_initial == "create" and name_arg_initial:
                    min_len = getattr(config, 'MIN_CHAR_NAME_LENGTH', 3)
                    max_len = getattr(config, 'MAX_CHAR_NAME_LENGTH', 20)
                    is_valid_name_format = all(c.isalpha() or c.isspace() for c in name_arg_initial) and any(c.isalpha() for c in name_arg_initial)

                    if player_handler and player_handler.player_exists(name_arg_initial):
                        session["messages_queue"].append({"text": f"The name '{name_arg_initial}' is already whispered. Choose another.", "type": "error", "prompt":True})
                    elif not (min_len <= len(name_arg_initial) <= max_len and is_valid_name_format):
                        session["messages_queue"].append({"text": f"A name must be {min_len}-{max_len} letters/spaces.", "type": "error", "prompt":True})
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
                            session_login_msgs = list(session.get("messages_queue", [])) 
                            player_creation_sessions.pop(sid, None) 
                            
                            if session_login_msgs: 
                                socketio.emit('game_messages', {'messages': session_login_msgs}, room=sid)
                            
                            loaded_player.add_message(f"Welcome back to {config.MUD_NAME}, {loaded_player.name}!", "event_highlight")
                            broadcast_to_room(loaded_player.current_room_id, f"{loaded_player.name} has reconnected.", "ambient_player_arrival", [sid])
                            send_room_description(loaded_player)
                            final_login_messages = loaded_player.get_queued_messages() 
                            if final_login_messages: emit('game_messages', {'messages': final_login_messages}, room=sid)
                            send_player_stats_update(loaded_player)
                            return 
                        else:
                            session["messages_queue"].append({"text": f"Character '{name_arg_initial}' not found.", "type": "error", "prompt":True})
                    else:
                        session["messages_queue"].append({"text": "Login system unavailable.", "type": "error_critical", "prompt":True})
                else: 
                     if current_phase == "awaiting_login_name": 
                        session["messages_queue"].append({"text": "Please use 'login <name>' or 'create <name>'.", "type": "prompt"})
                send_creation_messages(sid, session, player_shell)

            elif player_shell: 
                character_creation.handle_creation_input(player_shell, command_input, player_handler, GAME_RACES)
                if session.get("phase") != player_shell.creation_phase: 
                    session["phase"] = player_shell.creation_phase
                
                if player_shell.creation_phase == "completed":
                    finalize_character_creation(sid, player_shell, GAME_RACES, GAME_ITEMS)
                    return 
                
                send_creation_messages(sid, session, player_shell) 

            elif not player_shell and current_phase != "awaiting_login_name": 
                 session["messages_queue"].append({"text": "Connection unstable. Reconnecting may help.", "type": "error_critical", "prompt":True})
                 send_creation_messages(sid, session, None)
        
        else: 
            if config.DEBUG_MODE: print(f"DEBUG ERROR: SID {sid} has no active player or creation session.")
            emit('game_messages', {'messages': [{"text": "Reality flickers. Try reconnecting.", "type": "error_critical"}]}, room=sid)

    except Exception as e:
        print(f"!!! UNHANDLED EXCEPTION IN handle_player_command for SID {sid}, Command: '{command_input}' !!!")
        traceback.print_exc()
        try: 
            socketio.emit('game_messages', {'messages': [{"text": "Critical server error. Command may not have processed.", "type": "error_critical"}]}, room=sid)
        except Exception as e_emit:
            print(f"CRITICAL: Error emitting critical error message to client {sid}: {e_emit}")




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
    GAME_ITEMS = all_loaded_data.get("items", {})
    GAME_LOOT_TABLES = all_loaded_data.get("loot_tables", {})
    GAME_RACES = all_loaded_data.get("races", {})
    GAME_EQUIPMENT_TABLES = all_loaded_data.get("equipment_tables", {})
    GAME_NPCS = all_loaded_data.get("npc_templates", {})
    GAME_MONSTER_TEMPLATES = all_loaded_data.get("monster_templates", {})
    GAME_ROOMS = all_loaded_data.get("rooms", {})

    loot_handler.GAME_LOOT_TABLES = GAME_LOOT_TABLES # Make loot tables available to the handler

    if config.DEBUG_MODE:
        print(f"DEBUG STARTUP: Loaded {len(GAME_RACES)} races into GAME_RACES.")
        if not GAME_RACES: print("WARNING: GAME_RACES is empty after loading.")
        print(f"DEBUG STARTUP: Loaded {len(GAME_EQUIPMENT_TABLES)} equipment tables.")
    print(f"Loaded: {len(GAME_ROOMS)} Rooms, {len(GAME_ITEMS)} Items, {len(GAME_NPCS)} NPCs, {len(GAME_MONSTER_TEMPLATES)} Monsters, {len(GAME_RACES)} Races, {len(GAME_LOOT_TABLES)} Loot Tables, {len(GAME_EQUIPMENT_TABLES)} Equip Tables.")

    print("Starting game tick loop...");
    game_tick_thread = threading.Thread(target=game_tick_loop, name="GameTickLoop");
    game_tick_thread.daemon = True;
    game_tick_thread.start()

    host_ip = getattr(config, 'HOST', '0.0.0.0');
    port_num = int(getattr(config, 'PORT', 8024))
    debug_flask = getattr(config, 'DEBUG_MODE_FLASK', False)
    use_reloader_flask = getattr(config, 'FLASK_USE_RELOADER', False) and debug_flask
    print(f"MUD server on http://{host_ip}:{port_num} (Flask Debug: {'ON' if debug_flask else 'OFF'}, Reloader: {'ON' if use_reloader_flask else 'OFF'})")

    try:
        socketio.run(app, host=host_ip, port=port_num, debug=debug_flask, use_reloader=use_reloader_flask, allow_unsafe_werkzeug=True if use_reloader_flask else False)
    except KeyboardInterrupt:
        print("\nServer shutting down (KeyboardInterrupt)...")
    except Exception as e:
        print(f"Failed to start server: {e}")
        traceback.print_exc()
    finally:
        print("Attempting graceful shutdown...");
        game_loop_active = False
        if 'game_tick_thread' in locals() and game_tick_thread.is_alive():
            print("Waiting for game tick loop...");
            game_tick_thread.join(timeout=float(getattr(config,'TICK_INTERVAL_SECONDS', 6.0)) + 2.0)
            if game_tick_thread.is_alive():
                print("Warning: Game tick loop did not terminate cleanly.")

        if active_players:
            print(f"Saving data for {len(active_players)} active player(s)...")
            for sid_s, player_s in list(active_players.items()):
                if player_handler.save_player(player_s):
                    if config.DEBUG_MODE: print(f"DEBUG MAIN_SHUTDOWN: Saved {player_s.name}.")
                else:
                    print(f"ERROR MAIN_SHUTDOWN: Failed to save {player_s.name}.")

        db_connection.close_mongo_connection();
        print(f"{mud_name} has shut down gracefully.")
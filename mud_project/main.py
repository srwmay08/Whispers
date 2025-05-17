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
        except ValueError: current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1) # Ensure fallback
        player_object.current_room_id = current_room_id
    room_data = GAME_ROOMS.get(current_room_id)
    if not room_data:
        player_object.add_message(f"Error: You are in an unknown room (ID: {current_room_id})! Moving to safety...", "error_critical")
        player_object.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1) # Ensure fallback
        if player_handler: player_handler.save_player(player_object)
        room_data = GAME_ROOMS.get(player_object.current_room_id)
        if not room_data:
            player_object.add_message({"name": "Lost", "description": "You are utterly lost. Contact an admin.", "type": "error_critical"})
            return

    final_room_description = environment_system.get_description_for_room(room_data)
    all_present_names = [p.name for sid, p in active_players.items() if hasattr(p, 'current_room_id') and p.current_room_id == current_room_id and sid != player_object.sid]

    # Display NPCs
    for npc_key in room_data.get("npcs", []):
        npc_template = GAME_NPCS.get(npc_key)
        if npc_template and not combat.RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(npc_key): # Check if recently defeated
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

    # Display items and dynamic objects
    visible_item_names = []
    for item_id_static in room_data.get("items", []): # Static items
        item_tpl_static = GAME_ITEMS.get(item_id_static)
        if item_tpl_static:
            visible_item_names.append(item_tpl_static.get("name", item_id_static))

    for obj_data_dynamic in room_data.get("objects", {}).values(): # Dynamic objects like corpses, ground items
        if obj_data_dynamic.get("is_corpse") or obj_data_dynamic.get("is_ground_item"):
            visible_item_names.append(obj_data_dynamic.get("name", "an object"))

    # Display room features (defined_objects)
    for feature_data in room_data.get("defined_objects", {}).values():
        visible_item_names.append(feature_data.get("name", "a feature")) # Or handle features differently

    items_on_ground_str = "YOU ALSO SEE: " + ", ".join(sorted(list(set(visible_item_names)))) + "." if visible_item_names else ""

    room_data_payload = {
        "name": room_data.get("name", "Nowhere Special"),
        "description": final_room_description,
        "presence_summary": present_entities_str,
        "items_summary": items_on_ground_str, # Changed key for clarity
        "exits": ", ".join(k.upper() for k in room_data.get("exits", {}).keys()) or "None",
        "type": "room_data_update"
    }
    player_object.add_message(room_data_payload)


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

        if player:
            player.add_message(f"> {command_input}", "echo")
            if hasattr(player, 'next_action_time') and time.time() < player.next_action_time:
                player.add_message(f"Wait {max(0.0, round(player.next_action_time - time.time(), 1))}s.", "error_rt")
            else:
                parts = command_input.lower().split(" ", 1)
                verb = parts[0]
                raw_target_arg = parts[1].strip() if len(parts) > 1 else None
                target_arg = None
                if raw_target_arg:
                    look_verbs = ["look", "l", "examine", "ex", "exa"]
                    action_verbs_with_target = [
                        "search", "attack", "get", "take", "drop", "talk", "give",
                        "open", "close", "enter", "use", "read", "cast", "climb",
                        "skin", "equip", "unequip", "wear", "remove" # Added wear, remove
                    ]
                    if verb in look_verbs and raw_target_arg.startswith("at ") and len(raw_target_arg) > 3:
                        target_arg = raw_target_arg[3:].strip()
                    elif verb in action_verbs_with_target or verb in look_verbs:
                        target_arg = raw_target_arg
                    elif raw_target_arg and verb not in look_verbs and verb not in action_verbs_with_target:
                         target_arg = raw_target_arg

                if config.DEBUG_MODE: print(f"DEBUG CMD PARSED: Verb='{verb}', TargetArg='{target_arg}' (RawTarget='{raw_target_arg}')")
                room_id_before_move = player.current_room_id
                current_room_data = GAME_ROOMS.get(room_id_before_move)
                action_taken = False

                # --- START OF COMMAND HANDLING CHAIN ---
                if verb == "attack":
                    action_taken = True
                    rt_look = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                    rt_attack = config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
                    if not target_arg:
                        player.add_message("Attack whom or what?", "error")
                        player.next_action_time = time.time() + rt_look
                    elif not current_room_data:
                        player.add_message("You can't attack anything in the void.", "error")
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
                                    if config.DEBUG_MODE:
                                        print(f"DEBUG PVP: {player.name} initiating attack on {target_player_object.name}")
                                    combat_results = {}
                                    try:
                                        # This will cause an AttributeError if combat.handle_pvp_attack doesn't exist
                                        combat_results = combat.handle_pvp_attack(player, target_player_object, GAME_ITEMS)
                                    except AttributeError:
                                        player.add_message("PvP combat system is not yet fully implemented.", "error_dev")
                                        if config.DEBUG_MODE: print("DEBUG PVP: combat.handle_pvp_attack is not yet implemented.")
                                    except Exception as pvp_e:
                                        player.add_message("An error occurred during PvP combat.", "error_critical")
                                        if config.DEBUG_MODE: print(f"ERROR PVP combat: {pvp_e}"); traceback.print_exc()

                                    if combat_results.get('attacker_messages'):
                                        for msg in combat_results['attacker_messages']: player.add_message(msg['text'], msg['type'])
                                    if combat_results.get('target_messages'):
                                        for msg in combat_results['target_messages']: target_player_object.add_message(msg['text'], msg['type'])
                                    if combat_results.get('room_messages'):
                                        for msg_info in combat_results['room_messages']:
                                            broadcast_to_room(player.current_room_id, msg_info['text'], msg_info['type'], exclude_sids=[player.sid, target_player_object.sid])
                                    if combat_results.get('defeated_player_sid'):
                                        defeated_player = active_players.get(combat_results['defeated_player_sid'])
                                        if defeated_player:
                                            player.add_message(f"You have defeated {defeated_player.name}!", "event_pvp_victory")
                                            defeated_player.add_message(f"You have been defeated by {player.name}!", "event_pvp_defeat_major")
                                            broadcast_to_room(player.current_room_id, f"{defeated_player.name} falls in battle to {player.name}!", "ambient_pvp_defeat", [player.sid, defeated_player.sid])
                                            # TODO: Implement actual player "death" (move to respawn, penalties, etc.)
                                    player.next_action_time = time.time() + rt_attack
                                    if target_player_object and target_player_object.sid in active_players and not combat_results.get('defeated_player_sid'):
                                        target_player_object.next_action_time = time.time() + rt_attack

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
                                        xp_to_award = defeated_entity_template.get("xp_on_kill", 0)
                                        if xp_to_award > 0 and hasattr(player, 'add_xp_to_pool'): player.add_xp_to_pool(xp_to_award, GAME_RACES)
                                        for hit in defeated_entity_template.get("faction_hits_on_kill", []):
                                            if isinstance(hit, dict) and hit.get("faction_id") and isinstance(hit.get("amount"), int):
                                                if hasattr(player, 'update_faction'): player.update_faction(hit["faction_id"], hit["amount"])
                                    if defeated_entity_template.get("leaves_corpse", True):
                                        corpse_data = loot_handler.create_corpse_object_data(
                                            defeated_entity_template,
                                            defeated_runtime_id_from_combat,
                                            GAME_ITEMS
                                        )
                                        if corpse_data:
                                            current_room_data.setdefault("objects", {})[corpse_data["id"]] = corpse_data
                                            player.add_message(f"The {target_display_name_from_combat} slumps, leaving a corpse.", "event_defeat_corpse")
                                        else:
                                            player.add_message(f"The {target_display_name_from_combat} collapses, but no corpse object was formed.", "event_error")
                                    else:
                                        player.add_message(f"The {target_display_name_from_combat} collapses!", "event_defeat")
                                    player.add_message(f"You defeated {target_display_name_from_combat}!", "event_defeat_major")
                                    if defeated_runtime_id_from_combat and defeated_entity_template:
                                        spawn_cfg = defeated_entity_template.get("spawn_config", {})
                                        respawn_time_val = spawn_cfg.get("respawn_time_seconds", defeated_entity_template.get("respawn_time_seconds"))
                                        if respawn_time_val is not None:
                                            home_room_id_for_respawn = spawn_cfg.get("home_room_id", player.current_room_id)
                                            TRACKED_DEFEATED_ENTITIES[defeated_runtime_id_from_combat] = {
                                                "eligible_at": time.time() + float(respawn_time_val),
                                                "room_id": home_room_id_for_respawn,
                                                "template_key": target_id_or_key,
                                                "type": target_type,
                                                "is_unique": defeated_entity_template.get("is_unique", False),
                                                "chance": float(spawn_cfg.get("spawn_chance", getattr(config, 'DEFAULT_RESPAWN_CHANCE', 0.2))),
                                                }
                                            if config.DEBUG_MODE: print(f"DEBUG MAIN_RESPAWN: Added '{defeated_runtime_id_from_combat}' to tracker.")
                                player.next_action_time = time.time() + rt_attack
                            else:
                                player.add_message("You can't attack that!", "error")
                                player.next_action_time = time.time() + rt_look
                        else:
                            player.add_message(f"You don't see '{target_arg}' to attack.", "error")
                            player.next_action_time = time.time() + rt_look

                elif verb == "equip" or verb == "wear": # Added "wear" as alias
                    action_taken = True
                    rt_equip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                    if not target_arg:
                        player.add_message(f"{verb.capitalize()} what? (e.g., {verb} rusty_sword mainhand)", "error")
                    else:
                        parts_equip = target_arg.split(" ", 1)
                        item_query = parts_equip[0] # Can be name or ID
                        slot_to_equip_to = parts_equip[1].lower().strip() if len(parts_equip) > 1 else None

                        actual_item_id_to_equip = None
                        # Try matching by exact ID first (if player typed an ID)
                        if item_query in player.inventory: # Assuming item_query could be an ID
                            item_template_check = GAME_ITEMS.get(item_query)
                            if item_template_check: # If it's a valid item ID
                                actual_item_id_to_equip = item_query

                        # If not found by ID, try by name
                        if not actual_item_id_to_equip:
                            for item_id_in_inv in player.inventory:
                                item_template = GAME_ITEMS.get(item_id_in_inv)
                                if item_template and item_template.get("name", "").lower() == item_query.lower():
                                    actual_item_id_to_equip = item_id_in_inv
                                    break
                        
                        if not actual_item_id_to_equip:
                            player.add_message(f"You don't have a '{item_query}'.", "error")
                        elif not slot_to_equip_to: # If slot not provided, try to infer from item type if possible
                            item_template_for_slot = GAME_ITEMS.get(actual_item_id_to_equip)
                            if item_template_for_slot:
                                preferred_slot = item_template_for_slot.get("slot") # Assuming "slot" is a string or first in a list
                                if isinstance(preferred_slot, list): preferred_slot = preferred_slot[0] if preferred_slot else None
                                
                                if preferred_slot and preferred_slot in config.EQUIPMENT_SLOTS:
                                    slot_to_equip_to = preferred_slot
                                else:
                                    player.add_message(f"{verb.capitalize()} it where? (e.g., {verb} {item_query} mainhand)", "error")
                            else: # Should not happen if actual_item_id_to_equip is valid
                                player.add_message("Item error.", "error_critical")

                        if actual_item_id_to_equip and slot_to_equip_to: # Proceed if we have both
                            if hasattr(player, 'equip_item'):
                                player.equip_item(actual_item_id_to_equip, slot_to_equip_to, GAME_ITEMS, GAME_RACES)
                            else:
                                player.add_message("Equipment system error.", "error_critical")
                    player.next_action_time = time.time() + rt_equip

                elif verb == "unequip" or verb == "remove":
                    action_taken = True
                    rt_unequip = config.ROUNDTIME_DEFAULTS.get('roundtime_action_short', 1.0)
                    if not target_arg:
                        player.add_message(f"{verb.capitalize()} what? (e.g., {verb} mainhand or {verb} old_tunic)", "error")
                    elif hasattr(player, 'unequip_item'):
                        slot_or_item_name = target_arg.lower()
                        unequipped_successfully = False
                        # Try to unequip by item name first
                        for slot_key, item_id in player.equipped_items.items():
                            if item_id:
                                item_template = GAME_ITEMS.get(item_id)
                                if item_template and item_template.get("name", "").lower() == slot_or_item_name:
                                    if player.unequip_item(slot_key, GAME_ITEMS, GAME_RACES):
                                        unequipped_successfully = True
                                    break 
                        if not unequipped_successfully: # If not unequipped by name, try by slot key
                            if slot_or_item_name in config.EQUIPMENT_SLOTS:
                                if player.unequip_item(slot_or_item_name, GAME_ITEMS, GAME_RACES):
                                    unequipped_successfully = True
                        if not unequipped_successfully: # If still not unequipped
                             player.add_message(f"You are not wearing '{target_arg}' or '{target_arg}' is not a valid slot.", "error")
                    else:
                        player.add_message("Equipment system error.", "error_critical")
                    player.next_action_time = time.time() + rt_unequip

                elif verb == "factions" or verb == "faction":
                    action_taken = True  # Indented
                    if hasattr(player, 'get_faction_display_str'): # Indented
                        faction_info = player.get_faction_display_str(getattr(config, 'FACTION_DISPLAY_NAMES', {}))
                        player.add_message(faction_info, "system_info_block")
                    else: # Indented
                        player.add_message("You have no faction information to display.", "system_info")
                    player.next_action_time = time.time() + getattr(config, 'ROUNDTIME_DEFAULTS', {}).get('roundtime_look', 0.2) # Indented
 
                elif verb == "search":
                    action_taken = True
                    rt_search_default = getattr(config, 'SEARCH_BASE_ROUNDTIME', 1.5)
                    player.next_action_time = time.time() + rt_search_default
                    if not target_arg:
                        player.add_message("Search what?", "error")
                    elif not current_room_data:
                        player.add_message("You can't search anything here.", "error")
                    else:
                        obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                        if obj_data:
                            target_display_name = obj_data.get("name", target_arg)
                            if obj_data.get("is_corpse"):
                                corpse_inventory_ids = obj_data.get("inventory", [])
                                if obj_data.get("searched_and_emptied"):
                                    player.add_message(f"The {target_display_name} has already been thoroughly searched and emptied.", "feedback_neutral")
                                elif corpse_inventory_ids:
                                    player.add_message(f"You search the {target_display_name}...", "feedback_search_corpse")
                                    items_moved_to_ground_names = []
                                    for item_id_on_corpse in list(corpse_inventory_ids):
                                        item_object_placed = add_item_object_to_room(current_room_data, item_id_on_corpse, GAME_ITEMS)
                                        if item_object_placed:
                                            items_moved_to_ground_names.append(item_object_placed.get("name", item_id_on_corpse))
                                            if item_id_on_corpse in obj_data["inventory"]:
                                                obj_data["inventory"].remove(item_id_on_corpse)
                                    if items_moved_to_ground_names:
                                        player.add_message("...and its contents spill onto the ground:", "event_highlight")
                                        for name in items_moved_to_ground_names: player.add_message(f"- A {name}", "feedback_loot_drop")
                                    else: player.add_message("...but find nothing of value that wasn't already loose.", "feedback_search_empty")
                                    obj_data["searched_and_emptied"] = True
                                    obj_data["description"] = f"The searched and looted remains of {obj_data.get('original_name', 'a creature')}."
                                else:
                                    player.add_message(f"You search the {target_display_name} but find nothing of value.", "feedback_search_empty")
                                    obj_data["searched_and_emptied"] = True
                            elif obj_data.get("actions") and "search" in obj_data.get("actions", {}):
                                player.add_message(f"You search the {target_display_name}...", "feedback_neutral")
                                # TODO: Implement scripted search results based on obj_data.get("actions")["search"]
                            else: player.add_message(f"You find nothing special by searching the {target_display_name}.", "feedback_search_empty")
                        else: player.add_message(f"You don't see '{target_arg}' to search here.", "error")

                elif verb in ["get", "take"]:
                    action_taken = True
                    rt_get_default = getattr(config, 'GET_BASE_ROUNDTIME', 0.5)
                    player.next_action_time = time.time() + rt_get_default
                    if not target_arg: player.add_message(f"{verb.capitalize()} what?", "error")
                    elif not current_room_data: player.add_message("There's nothing here to get.", "error")
                    else:
                        item_name_query = target_arg
                        container_name_query = None
                        if " from " in target_arg.lower():
                            parts = target_arg.split(" from ", 1) # Keep case for item name, lowercase container later
                            item_name_query = parts[0].strip()
                            container_name_query = parts[1].strip()

                        if container_name_query: # Trying to get item FROM a container
                            container_id, container_data = find_object_in_room(player, container_name_query, current_room_data)
                            if container_data and (container_data.get("is_corpse") or container_data.get("is_container")):
                                container_inventory_ids = container_data.get("inventory", [])
                                item_found_in_container = None; item_id_to_remove_from_container = None
                                for item_id_in_inv in list(container_inventory_ids):
                                    item_tpl_cont = GAME_ITEMS.get(item_id_in_inv)
                                    if item_tpl_cont and (item_tpl_cont.get("name","").lower() == item_name_query.lower() or \
                                                          item_name_query.lower() in [k.lower() for k in item_tpl_cont.get("keywords",[])] or \
                                                          item_id_in_inv.lower() == item_name_query.lower()): # Match by ID too
                                        item_found_in_container = item_tpl_cont
                                        item_id_to_remove_from_container = item_id_in_inv
                                        break
                                if item_found_in_container:
                                    if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20): player.add_message("Your inventory is full.", "error")
                                    else:
                                        player.inventory.append(item_id_to_remove_from_container)
                                        player.add_message(f"You get the {item_found_in_container.get('name', item_name_query)} from the {container_data.get('name', container_name_query)}.", "feedback_get_item")
                                        container_data["inventory"].remove(item_id_to_remove_from_container)
                                        if not container_data["inventory"] and container_data.get("is_corpse"):
                                            container_data["description"] = f"The looted remains of {container_data.get('original_name', 'a creature')}."
                                            # searched_and_emptied should have been set by search, but good to be thorough
                                            container_data["searched_and_emptied"] = True
                                        send_player_stats_update(player)
                                else: player.add_message(f"You don't see a '{item_name_query}' in the {container_data.get('name', container_name_query)}.", "error")
                            else: player.add_message(f"You don't see a '{container_name_query}' to get items from.", "error")
                        else: # Trying to get item from the ground or static room items
                            obj_id_to_get, obj_data_to_get = find_object_in_room(player, item_name_query, current_room_data)
                            if obj_data_to_get:
                                if obj_data_to_get.get("is_ground_item"): # Dynamic item on ground
                                    item_template_id = obj_data_to_get.get("item_template_id")
                                    if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20): player.add_message("Your inventory is full.", "error")
                                    else:
                                        player.inventory.append(item_template_id)
                                        player.add_message(f"You pick up the {obj_data_to_get.get('name', 'item')}.", "feedback_get_item")
                                        if obj_id_to_get in current_room_data.get("objects", {}): del current_room_data["objects"][obj_id_to_get]
                                        if config.DEBUG_MODE: print(f"DEBUG GET: Removed ground item '{obj_id_to_get}' from room {player.current_room_id}.")
                                        send_player_stats_update(player)
                                elif obj_data_to_get.get("is_static_item"): # Static item from room definition
                                    item_id_static_to_get = obj_data_to_get.get("id")
                                    if item_id_static_to_get in current_room_data.get("items", []): # Check if still in room's static list
                                        if len(player.inventory) >= getattr(config, 'MAX_INVENTORY_SIZE', 20): player.add_message("Your inventory is full.", "error")
                                        else:
                                            player.inventory.append(item_id_static_to_get)
                                            current_room_data["items"].remove(item_id_static_to_get)
                                            player.add_message(f"You pick up the {obj_data_to_get.get('name', 'item')}.", "feedback_get_item")
                                            send_player_stats_update(player)
                                    else: player.add_message(f"It seems the {obj_data_to_get.get('name', 'item')} is no longer here.", "error") # Already taken
                                else: # Found an object but it's not gettable (e.g., a corpse, a room feature)
                                    player.add_message(f"You can't {verb} the {obj_data_to_get.get('name', item_name_query)}.", "error")
                            else: player.add_message(f"You don't see '{item_name_query}' here to {verb}.", "error")


                elif verb in ["look", "l", "examine", "exa"]:
                    action_taken = True
                    rt_look_cmd = config.ROUNDTIME_DEFAULTS.get('roundtime_look', 0.2)
                    if target_arg and current_room_data:
                        target_entity_data, entity_type, entity_id_or_key, _ = find_combat_target_in_room(player, target_arg, current_room_data)
                        if target_entity_data:
                            look_desc = target_entity_data.get("look_description", target_entity_data.get("description"))
                            if not look_desc: look_desc = f"You see {target_entity_data.get('name', target_arg)}."
                            if entity_type in ["npc", "monster"] and target_entity_data.get("equipped"):
                                equipped_str_parts = []
                                for slot_key_disp, item_id_disp in target_entity_data["equipped"].items():
                                    if item_id_disp:
                                        item_data_disp = GAME_ITEMS.get(item_id_disp)
                                        if item_data_disp:
                                            slot_name_disp = config.EQUIPMENT_SLOTS.get(slot_key_disp, slot_key_disp).capitalize()
                                            equipped_str_parts.append(f"{slot_name_disp}: {item_data_disp.get('name',item_id_disp)}")
                                if equipped_str_parts:
                                    look_desc += "\nThey are equipped with: " + "; ".join(equipped_str_parts) + "."
                            player.add_message(look_desc, "feedback_look_target")
                        else:
                            obj_id, obj_data = find_object_in_room(player, target_arg, current_room_data)
                            if obj_data:
                                look_desc_obj = obj_data.get("description", "You see nothing special about it.")
                                if obj_data.get("is_corpse") and obj_data.get("inventory") and not obj_data.get("searched_and_emptied"):
                                    look_desc_obj += " It looks like it might have something on it."
                                player.add_message(look_desc_obj, "feedback_look_target")
                            else:
                                player.add_message(f"You don't see '{target_arg}' here.", "error")
                    else:
                        send_room_description(player)
                    player.next_action_time = time.time() + rt_look_cmd

                elif verb in room_data.get("exits", {}):
                    action_taken = True
                    destination_room_id = room_data["exits"][verb]
                    player.add_message(f"You move {verb}.", "feedback_move")
                    broadcast_to_room(room_id_before_move, f"{player.name} leaves heading {verb}.", "ambient_player_departure", [sid])
                    player.current_room_id = destination_room_id
                    broadcast_to_room(destination_room_id, f"{player.name} arrives from {get_opposite_direction(verb)}.", "ambient_player_arrival", [sid])
                    send_room_description(player)
                    player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_move', 0.5)

                elif verb == "say":
                    action_taken = True
                    if target_arg:
                        player.add_message(f"You say, \"{target_arg}\"", "dialogue_self")
                        broadcast_to_room(player.current_room_id, f"{player.name} says, \"{target_arg}\"", "dialogue_other", [sid])
                    else: player.add_message("Say what?", "error")
                    player.next_action_time = time.time() + getattr(config, 'ROUNDTIME_DEFAULTS', {}).get('roundtime_say', 0.1)

                elif verb == "quit":
                    action_taken = True
                    player.add_message("Quitting...", "system_event")
                    socketio.disconnect(sid)
                    return

                if not action_taken:
                    player.add_message(f"You can't seem to '{command_input}' here.", "error")
                    player.next_action_time = time.time() + 0.1

            all_msgs = player.get_queued_messages()
            if all_msgs: socketio.emit('game_messages', {'messages': all_msgs}, room=sid)
            send_player_stats_update(player)

        elif session:
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
                    if player_handler and player_handler.player_exists(name_arg_initial):
                        session["messages_queue"].append({"text": f"The name '{name_arg_initial}' is already whispered in the annals of this world. Choose another.", "type": "error"})
                    elif not (getattr(config, 'MIN_CHAR_NAME_LENGTH', 3) <= len(name_arg_initial) <= getattr(config, 'MAX_CHAR_NAME_LENGTH', 20) and name_arg_initial.replace(" ", "").isalpha()):
                        session["messages_queue"].append({"text": f"A name must be between {min_len} and {max_len} letters, and contain only letters and spaces.", "type": "error"})
                    else:
                        player_shell = player_class.Player(sid, name_arg_initial)
                        session["player_shell"] = player_shell
                        character_creation.start_character_creation(player_shell)
                        session["phase"] = player_shell.creation_phase
                elif verb_initial == "login" and name_arg_initial:
                    if player_handler:
                        loaded_player = player_handler.load_player(name_arg_initial, sid, GAME_RACES, GAME_ITEMS)
                        if loaded_player:
                            active_players[sid] = loaded_player
                            session_login_msgs = list(session.get("messages_queue", []))
                            player_creation_sessions.pop(sid, None)
                            if session_login_msgs: socketio.emit('game_messages', {'messages': session_login_msgs}, room=sid)
                            loaded_player.add_message(f"Welcome back to {config.MUD_NAME}, {loaded_player.name}!", "event_highlight")
                            broadcast_to_room(loaded_player.current_room_id, f"{loaded_player.name} has reconnected.", "ambient_player_arrival", [sid])
                            send_room_description(loaded_player)
                            final_login_messages = loaded_player.get_queued_messages()
                            if final_login_messages: emit('game_messages', {'messages': final_login_messages}, room=sid)
                            send_player_stats_update(loaded_player)
                            return
                        else:
                            session["messages_queue"].append({"text": f"Character '{name_arg_initial}' not found or password incorrect.", "type": "error"})
                    else:
                        session["messages_queue"].append({"text": "The login scrolls are currently indecipherable. (Login system unavailable)", "type": "error_critical"})
                else:
                     if current_phase == "awaiting_login_name":
                        session["messages_queue"].append({"text": "Please use 'login <name>' or 'create <name>'.", "type": "error"})
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
                 session["messages_queue"].append({"text": "Your connection to the ethereal plane wavers. Reconnecting might stabilize your presence.", "type": "error_critical"})
                 send_creation_messages(sid, session, None)
        else:
            if config.DEBUG_MODE: print(f"DEBUG ERROR: SID {sid} has no active player or creation session. This should not happen.")
            emit('game_messages', {'messages': [{"text": "A strange rift in reality prevents your actions. Please try reconnecting.", "type": "error_critical"}]}, room=sid)

    except Exception as e:
        print(f"!!! UNHANDLED EXCEPTION IN handle_player_command for SID {sid}, Command: '{command_input}' !!!")
        traceback.print_exc()
        try:
            socketio.emit('game_messages', {'messages': [{"text": "A critical server error occurred. Your command may not have been processed.", "type": "error_critical"}]}, room=sid)
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
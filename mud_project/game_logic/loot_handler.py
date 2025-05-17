# mud_project/game_logic/loot_handler.py
import random
import time

try:
    import config
except ImportError:
    print("ERROR (loot_handler.py): Failed to import 'config'.")
    class MockConfig:
        DEBUG_MODE = True
        CORPSE_DECAY_TIME_SECONDS = 300
        # Add a default for dropping equipped items if not in actual config
        DEFAULT_DROP_EQUIPPED_CHANCE = 1.0 # 100% chance to drop equipped items
        DEFAULT_DROP_CARRIED_CHANCE = 1.0 # 100% chance to drop carried items
    config = MockConfig()

GAME_LOOT_TABLES = {} # This is populated by main.py

def generate_loot_from_table(loot_table_id, game_items_data):
    # ... (rest of the function remains the same as in combat_py_refactor_v1) ...
    loot_table = GAME_LOOT_TABLES.get(loot_table_id)
    if not loot_table:
        if config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER: Loot table ID '{loot_table_id}' not found.")
        return []

    dropped_items = []
    if config.DEBUG_MODE:
        print(f"DEBUG LOOT_HANDLER: Processing loot_table_id '{loot_table_id}'. game_items_data available: {bool(game_items_data)}")

    for entry in loot_table:
        item_id = entry.get("item_id")
        chance = entry.get("chance", 0.0)
        quantity_data = entry.get("quantity", 1)
        requires_skinning = entry.get("requires_skinning", False)

        if config.DEBUG_MODE:
            item_is_in_game_data = item_id in game_items_data if item_id else False
            print(f"DEBUG LOOT_HANDLER (Pre-Roll): Checking item '{item_id}' from table '{loot_table_id}'. Chance: {chance}. Valid in game_items: {item_is_in_game_data}. Requires skinning: {requires_skinning}")

        if not item_id or not item_is_in_game_data:
            if config.DEBUG_MODE and item_id:
                 print(f"DEBUG LOOT_HANDLER: Invalid or missing item_id '{item_id}' (or not in game_items_data) in loot table '{loot_table_id}'. Skipping.")
            continue
        
        if requires_skinning:
            if config.DEBUG_MODE:
                print(f"DEBUG LOOT_HANDLER: Item '{item_id}' requires skinning. Skipping for general loot generation.")
            continue

        roll_value = random.random()
        if roll_value < chance:
            quantity_to_drop = 0
            if isinstance(quantity_data, int):
                quantity_to_drop = quantity_data
            elif isinstance(quantity_data, list) and len(quantity_data) == 2:
                try:
                    min_qty, max_qty = int(quantity_data[0]), int(quantity_data[1])
                    quantity_to_drop = random.randint(min_qty, max_qty)
                except ValueError:
                    if config.DEBUG_MODE:
                        print(f"DEBUG LOOT_HANDLER: Invalid quantity format for item '{item_id}' in table '{loot_table_id}'. Defaulting to 1.")
                    quantity_to_drop = 1
            else:
                quantity_to_drop = 1
            
            for _ in range(quantity_to_drop):
                dropped_items.append(item_id)
            
            if config.DEBUG_MODE and quantity_to_drop > 0:
                print(f"DEBUG LOOT_HANDLER (Roll Success): Item '{item_id}' (qty: {quantity_to_drop}) dropped from table '{loot_table_id}'. Rolled {roll_value:.2f} vs Chance {chance:.2f}.")
        elif config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER (Roll Fail): Item '{item_id}' from table '{loot_table_id}' did NOT drop. Rolled {roll_value:.2f} vs Chance {chance:.2f}.")
    return dropped_items


def generate_skinning_loot(monster_template, player_skill_value, game_items_data):
    # ... (rest of the function remains the same as in combat_py_refactor_v1) ...
    skinned_items = []
    skinning_info = monster_template.get("skinning", {})
    success_item_id = skinning_info.get("item_yield_success_key")
    failure_item_id = skinning_info.get("item_yield_failed_key") 
    dc = skinning_info.get("base_dc", 10)
    
    if not success_item_id or success_item_id not in game_items_data:
        if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Skinning): Success item_id '{success_item_id}' invalid or not defined in GAME_ITEMS.")
        return []

    if player_skill_value >= dc: 
        skinned_items.append(success_item_id)
        if config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER (Skinning Success): Item '{success_item_id}' obtained. Skill: {player_skill_value} vs DC: {dc}.")
    else:
        if failure_item_id and failure_item_id in game_items_data:
            skinned_items.append(failure_item_id)
            if config.DEBUG_MODE:
                print(f"DEBUG LOOT_HANDLER (Skinning Failure - Yield): Item '{failure_item_id}' obtained. Skill: {player_skill_value} vs DC: {dc}.")
        elif config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER (Skinning Failure): No specific failure item, or '{failure_item_id}' invalid. Skill: {player_skill_value} vs DC: {dc}.")
            
    return skinned_items


def create_corpse_object_data(defeated_entity_template, defeated_entity_runtime_id, game_items_data, game_equipment_tables_data): # Added game_equipment_tables_data
    entity_name = defeated_entity_template.get("name", "Unknown Creature")
    corpse_name = f"corpse of a {entity_name}"
    corpse_id = f"corpse_{defeated_entity_runtime_id}_{int(time.time())}"

    final_loot_on_corpse = []

    # 1. Process 'carried_items' (items the NPC always has, not equipped)
    # You might want a config for drop chance of these too
    drop_carried_chance = getattr(config, 'NPC_DROP_CARRIED_CHANCE', 
                                  getattr(config, 'DEFAULT_DROP_CARRIED_CHANCE', 1.0)) # Default to 100%
    
    for item_key in defeated_entity_template.get("items", []): # Assuming "items" is the key for carried items
        if item_key in game_items_data:
            if random.random() < drop_carried_chance:
                final_loot_on_corpse.append(item_key)
                if config.DEBUG_MODE:
                    print(f"DEBUG LOOT_HANDLER: Carried item '{item_key}' added to loot for {corpse_name}.")
            elif config.DEBUG_MODE:
                print(f"DEBUG LOOT_HANDLER: Carried item '{item_key}' did not drop (chance failed).")
        elif config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER: Carried item_key '{item_key}' not found in GAME_ITEMS. Skipping.")

    # 2. Process Equipped Items
    equipment_table_id = defeated_entity_template.get("equipment_table_id")
    # Use the passed-in game_equipment_tables_data
    equipment_table_definition = game_equipment_tables_data.get(equipment_table_id) if equipment_table_id else None

    always_drop_list = []
    chance_drop_others = getattr(config, 'NPC_DROP_EQUIPPED_CHANCE', 1.0) # Fallback general chance

    if equipment_table_definition: # Check if the table itself was found
        always_drop_list = equipment_table_definition.get("always_drop_equipped", [])
        chance_drop_others = equipment_table_definition.get("chance_drop_other_equipped_percent", chance_drop_others)
        if config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER: Using equip_table '{equipment_table_id}'. Always drop: {always_drop_list}, Chance others: {chance_drop_others}")
    elif equipment_table_id and config.DEBUG_MODE: # Warn if ID was present but table not found
        print(f"DEBUG LOOT_HANDLER: Equipment table ID '{equipment_table_id}' not found in game_equipment_tables_data.")


    for slot, equipped_item_id in defeated_entity_template.get("equipped", {}).items():
        if equipped_item_id and equipped_item_id in game_items_data:
            item_should_drop = False
            if equipped_item_id in always_drop_list:
                item_should_drop = True
                if config.DEBUG_MODE:
                    print(f"DEBUG LOOT_HANDLER: Equipped item '{equipped_item_id}' (slot: {slot}) is in always_drop list.")
            elif random.random() < chance_drop_others:
                item_should_drop = True
                if config.DEBUG_MODE:
                    print(f"DEBUG LOOT_HANDLER: Equipped item '{equipped_item_id}' (slot: {slot}) dropped by chance ({chance_drop_others*100}%).")
            else:
                if config.DEBUG_MODE:
                    print(f"DEBUG LOOT_HANDLER: Equipped item '{equipped_item_id}' (slot: {slot}) did NOT drop (chance failed: {chance_drop_others*100}%).")

            if item_should_drop:
                final_loot_on_corpse.append(equipped_item_id)
                if config.DEBUG_MODE:
                    print(f"DEBUG LOOT_HANDLER: Equipped item '{equipped_item_id}' from slot '{slot}' ADDED to loot for {corpse_name}.")
        elif equipped_item_id and config.DEBUG_MODE:
             print(f"DEBUG LOOT_HANDLER: Equipped item_key '{equipped_item_id}' (slot: {slot}) not found in GAME_ITEMS. Skipping.")

    # 3. Process Loot Table
    loot_table_id = defeated_entity_template.get("loot_table_id")
    if loot_table_id:
        # Pass game_items_data to generate_loot_from_table if it needs it.
        # Your current generate_loot_from_table already accepts game_items_data.
        table_loot = generate_loot_from_table(loot_table_id, game_items_data)
        final_loot_on_corpse.extend(table_loot)
    
    # --- END NEW/IMPROVED LOOT GENERATION ---
    
    # Ensure keywords are lowercase for matching and include generic "corpse"
    # Also add parts of the original name for more flexible searching like "search timothy" for "corpse of timothy"
    keywords_for_corpse = ["corpse", entity_name.lower()] + entity_name.lower().split()
    keywords_for_corpse = list(set(keywords_for_corpse))

    corpse_data = {
        "id": corpse_id,
        "name": corpse_name,
        "original_name": entity_name,
        "description": f"The lifeless body of {entity_name}.",
        "keywords": keywords_for_corpse,
        "inventory": final_loot_on_corpse,
        "is_corpse": True,
        "skinnable": defeated_entity_template.get("skinnable", False),
        "skinned": False,
        "searched_and_emptied": False, # Corrected from "searched_fully" to match 'search' command logic
        "created_at": time.time(),
        "decay_at": time.time() + getattr(config, 'CORPSE_DECAY_TIME_SECONDS', 300)
    }

    if final_loot_on_corpse:
        corpse_data["description"] += " It looks like it might have something of value."
    else:
        corpse_data["description"] += " It appears to have nothing of value on it."
        corpse_data["searched_and_emptied"] = True # If no loot, it's effectively empty

    if config.DEBUG_MODE:
        print(f"DEBUG LOOT_HANDLER: Created corpse data for '{corpse_name}' (ID: {corpse_id}) with inventory: {final_loot_on_corpse}")
    return corpse_data

def process_corpse_decay(game_rooms_dict, log_time_prefix):
    # ... (rest of the function remains the same as in combat_py_refactor_v1) ...
    current_time = time.time()
    decayed_corpse_messages = {} 

    for room_id, room_data in game_rooms_dict.items():
        objects_in_room = room_data.get("objects", {})
        if not objects_in_room:
            continue

        corpse_ids_to_remove = []
        for obj_id, obj_data in objects_in_room.items():
            if obj_data.get("is_corpse") and obj_data.get("decay_at", 0) < current_time:
                corpse_ids_to_remove.append(obj_id)
                if config.DEBUG_MODE:
                    print(f"{log_time_prefix} - CORPSE_DECAY: Corpse '{obj_data.get('name', obj_id)}' in room {room_id} has decayed.")
                
                decay_message = f"The {obj_data.get('name', 'corpse')} decays and disappears."
                if room_id not in decayed_corpse_messages:
                    decayed_corpse_messages[room_id] = []
                decayed_corpse_messages[room_id].append(decay_message)

        for corpse_id_to_remove in corpse_ids_to_remove:
            objects_in_room.pop(corpse_id_to_remove, None)
            
    return decayed_corpse_messages

if config.DEBUG_MODE:
    print("game_logic.loot_handler loaded.")

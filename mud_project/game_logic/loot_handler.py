# mud_project/game_logic/loot_handler.py
import random
import time

try:
    import config
except ImportError:
    # ... (your mock config) ...
    class MockConfig:
        DEBUG_MODE = True; CORPSE_DECAY_TIME_SECONDS = 300
        DEFAULT_DROP_EQUIPPED_CHANCE = 1.0; DEFAULT_DROP_CARRIED_CHANCE = 1.0
    config = MockConfig()

GAME_LOOT_TABLES = {} 

def generate_loot_from_table(loot_table_id, game_items_data):
    loot_table = GAME_LOOT_TABLES.get(loot_table_id)
    if not loot_table:
        if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Loot table ID '{loot_table_id}' not found.")
        return []
    dropped_items = []
    if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Processing loot_table_id '{loot_table_id}'. game_items_data available: {bool(game_items_data)}")
    for entry in loot_table:
        item_id = entry.get("item_id"); chance = entry.get("chance", 0.0)
        quantity_data = entry.get("quantity", 1); requires_skinning = entry.get("requires_skinning", False)
        if config.DEBUG_MODE:
            item_is_in_game_data = item_id in game_items_data if item_id else False
            print(f"DEBUG LOOT_HANDLER (Pre-Roll): Checking item '{item_id}' from table '{loot_table_id}'. Chance: {chance}. Valid: {item_is_in_game_data}. Skinning: {requires_skinning}")
        if not item_id or not item_is_in_game_data:
            if config.DEBUG_MODE and item_id: print(f"DEBUG LOOT_HANDLER: Invalid item_id '{item_id}' in table '{loot_table_id}'. Skipping.")
            continue
        if requires_skinning:
            if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Item '{item_id}' requires skinning. Skipping for general loot.")
            continue
        roll_value = random.random()
        if roll_value < chance:
            quantity_to_drop = 0
            if isinstance(quantity_data, int): quantity_to_drop = quantity_data
            elif isinstance(quantity_data, list) and len(quantity_data) == 2:
                try: quantity_to_drop = random.randint(int(quantity_data[0]), int(quantity_data[1]))
                except ValueError: quantity_to_drop = 1;                         
                if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Invalid quantity for '{item_id}'. Defaulting to 1.")
            else: quantity_to_drop = 1
            for _ in range(quantity_to_drop): dropped_items.append(item_id)
            if config.DEBUG_MODE and quantity_to_drop > 0: print(f"DEBUG LOOT_HANDLER (Roll Success): Item '{item_id}' (qty: {quantity_to_drop}) dropped. Rolled {roll_value:.2f} vs Chance {chance:.2f}.")
        elif config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Roll Fail): Item '{item_id}' did NOT drop. Rolled {roll_value:.2f} vs Chance {chance:.2f}.")
    return dropped_items

def generate_skinning_loot(monster_template, player_skill_value, game_items_data):
    skinned_items = []
    skinning_info = monster_template.get("skinning", {})
    success_item_id = skinning_info.get("item_yield_success_key")
    failure_item_id = skinning_info.get("item_yield_failed_key") 
    dc = skinning_info.get("base_dc", 10)
    if not success_item_id or success_item_id not in game_items_data:
        if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Skinning): Success item '{success_item_id}' invalid.")
        return [] # Cannot yield success item, so fail skinning or return nothing
    if player_skill_value >= dc: 
        skinned_items.append(success_item_id)
        if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Skinning Success): Item '{success_item_id}'. Skill: {player_skill_value} vs DC: {dc}.")
    else:
        if failure_item_id and failure_item_id in game_items_data:
            skinned_items.append(failure_item_id)
            if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Skinning Failure - Yield): Item '{failure_item_id}'. Skill: {player_skill_value} vs DC: {dc}.")
        elif config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER (Skinning Failure): No specific failure item. Skill: {player_skill_value} vs DC: {dc}.")
    return skinned_items

def create_corpse_object_data(defeated_entity_template, defeated_entity_runtime_id, game_items_data, game_equipment_tables_data):
    entity_name = defeated_entity_template.get("name", "Unknown Creature")
    corpse_name = f"corpse of a {entity_name}"
    # --- CHANGE: Store the original template key ---
    # This assumes defeated_entity_template has an "_id" field which is its template key.
    # Or, if not, attempts to derive it from defeated_entity_runtime_id if it follows a pattern.
    original_template_key = defeated_entity_template.get("_id")
    if not original_template_key: # Fallback attempt if _id is not directly on the template passed
        parts = defeated_entity_runtime_id.split('_')
        if len(parts) > 1 and parts[0].isdigit(): # e.g., "roomID_templateKey_instance"
            original_template_key = parts[1] 
        else: # e.g. just "templateKey" if runtime_id is the template key
            original_template_key = defeated_entity_runtime_id
        if config.DEBUG_MODE:
            print(f"DEBUG LOOT_HANDLER: original_template_key derived as '{original_template_key}' from runtime_id '{defeated_entity_runtime_id}'.")
    # --- END CHANGE ---
    corpse_id = f"corpse_{defeated_entity_runtime_id}_{int(time.time())}" # Keep runtime_id in corpse_id for uniqueness

    loot_items_for_corpse_inventory = []
    drop_carried_chance = getattr(config, 'NPC_DROP_CARRIED_CHANCE', getattr(config, 'DEFAULT_DROP_CARRIED_CHANCE', 1.0))
    
    # 1. Carried items (not from equipment table, but general NPC/Monster "items" field)
    # These are typically things like quest items, specific flavor items, etc.
    for item_key in defeated_entity_template.get("items", []): 
        if item_key in game_items_data:
            if random.random() < drop_carried_chance:
                loot_items_for_corpse_inventory.append(item_key)
                if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Carried item '{item_key}' added to loot for {corpse_name}.")
            # ... (logging for not dropping)
        # ... (logging for item_key not in GAME_ITEMS)

    # 2. Equipped Items
    equipment_table_id = defeated_entity_template.get("equipment_table_id")
    equipment_table_definition = game_equipment_tables_data.get(equipment_table_id) if equipment_table_id else None
    always_drop_list = []
    chance_drop_others = getattr(config, 'NPC_DROP_EQUIPPED_CHANCE', 1.0) 
    if equipment_table_definition: 
        always_drop_list = equipment_table_definition.get("always_drop_equipped", [])
        chance_drop_others = equipment_table_definition.get("chance_drop_other_equipped_percent", chance_drop_others)
        # ... (debug logging for equip table)
    
    for slot, equipped_item_id in defeated_entity_template.get("equipped", {}).items():
        if equipped_item_id and equipped_item_id in game_items_data:
            item_should_drop = False
            if equipped_item_id in always_drop_list or random.random() < chance_drop_others:
                item_should_drop = True
            if item_should_drop:
                loot_items_for_corpse_inventory.append(equipped_item_id)
                # ... (debug logging for equipped item drop)
        # ... (logging for equipped item not in GAME_ITEMS or not dropping)

    # 3. Loot Table
    loot_table_id = defeated_entity_template.get("loot_table_id")
    if loot_table_id:
        table_loot_ids = generate_loot_from_table(loot_table_id, game_items_data)
        loot_items_for_corpse_inventory.extend(table_loot_ids)
    
    final_loot_on_corpse = loot_items_for_corpse_inventory 

    keywords_for_corpse = ["corpse", entity_name.lower()] + entity_name.lower().split()
    keywords_for_corpse = list(set(keywords_for_corpse))

    corpse_data = {
        "id": corpse_id, "name": corpse_name, "original_name": entity_name,
        "original_template_key": original_template_key, # Store the template key for skinning
        "description": f"The lifeless body of {entity_name}.",
        "keywords": keywords_for_corpse, "inventory": final_loot_on_corpse, 
        "is_corpse": True, 
        "skinnable": defeated_entity_template.get("skinnable", False), # Get from template
        "skinned": False, "searched_and_emptied": False, 
        "created_at": time.time(),
        "decay_at": time.time() + getattr(config, 'CORPSE_DECAY_TIME_SECONDS', 300)
    }
    if final_loot_on_corpse: corpse_data["description"] += " It looks like it might have something of value."
    else: corpse_data["description"] += " It appears to have nothing of value on it."; corpse_data["searched_and_emptied"] = True 
    if config.DEBUG_MODE: print(f"DEBUG LOOT_HANDLER: Created corpse data for '{corpse_name}' (ID: {corpse_id}) with inventory: {final_loot_on_corpse}, skinnable: {corpse_data['skinnable']}, template_key: {original_template_key}")
    return corpse_data

def process_corpse_decay(game_rooms_dict, log_time_prefix):
    current_time = time.time(); decayed_corpse_messages = {} 
    for room_id, room_data in game_rooms_dict.items():
        objects_in_room = room_data.get("objects", {}); 
        if not objects_in_room: continue
        corpse_ids_to_remove = [obj_id for obj_id, obj_data in objects_in_room.items() if obj_data.get("is_corpse") and obj_data.get("decay_at", 0) < current_time]
        for corpse_id_to_remove in corpse_ids_to_remove:
            obj_data = objects_in_room.pop(corpse_id_to_remove, None)
            if obj_data and config.DEBUG_MODE: print(f"{log_time_prefix} - CORPSE_DECAY: Corpse '{obj_data.get('name', corpse_id_to_remove)}' in room {room_id} decayed.")
            decay_message = f"The {obj_data.get('name', 'corpse') if obj_data else 'corpse'} decays and disappears."
            decayed_corpse_messages.setdefault(room_id, []).append(decay_message)
    return decayed_corpse_messages

if config.DEBUG_MODE: print("game_logic.loot_handler loaded.")


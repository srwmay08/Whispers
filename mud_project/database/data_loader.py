# mud_project/database/data_loader.py
import sys
import os
import copy # For deepcopying templates

try:
    from . import connection # To get get_db()
    import config # Your main config file

    # Import all default data modules
    from game_data import default_items, default_monsters, default_npcs, default_rooms
    from game_data import loot_tables as default_loot_data
    from game_data import race_tables as default_race_data
    from game_data import equipment_tables as default_equipment_data # NEW
    from game_data import default_rooms as default_rooms_data # NEW

except ImportError as e:
    print(f"ERROR (data_loader.py): Critical import failed. Error: {e}")
    # Fallback mocks for basic functionality if imports fail
    class MockConfig:
        DEBUG_MODE = True; MONGODB_URI = "mongodb://localhost:27017/"; DATABASE_NAME = "whispers_game_fallback"
        PLAYERS_COLLECTION = "players"; ITEMS_COLLECTION = "items"; MONSTERS_COLLECTION = "monsters"
        NPCS_COLLECTION = "npcs"; ROOMS_COLLECTION = "rooms"; LOOT_TABLES_COLLECTION = "loot_tables"
        RACES_COLLECTION = "races"; EQUIPMENT_TABLES_COLLECTION = "equipment_tables"
        EQUIPMENT_SLOTS = {"torso": "Torso", "mainhand": "Main Hand", "offhand": "Off Hand", "head": "Head"} # Ensure this matches your actual config
    config = MockConfig()
    class MockDefaultData:
        DEFAULT_ITEM_TEMPLATES = {}; DEFAULT_MONSTER_TEMPLATES = {}; DEFAULT_NPCS_TEMPLATES = {}
        DEFAULT_ROOM_TEMPLATES = {}; DEFAULT_LOOT_TABLES = {}; DEFAULT_RACE_TEMPLATES = {}
        DEFAULT_EQUIPMENT_TABLES = {}
    default_items = default_monsters = default_npcs = default_rooms = MockDefaultData()
    default_loot_data = default_race_data = default_equipment_data = MockDefaultData()


def _initialize_collection(db, collection_name_from_config, default_data_module, default_data_key_name, data_desc):
    """Helper function to initialize a single collection."""
    if db is None:
        print(f"DATA_LOADER: DB not available, cannot initialize '{data_desc}'.")
        return

    collection = db[collection_name_from_config]
    if collection.count_documents({}) == 0:
        default_data_dict = getattr(default_data_module, default_data_key_name, {})
        if not default_data_dict:
            print(f"DATA_LOADER: No default data for '{data_desc}', '{collection_name_from_config}' will be empty.")
            return

        list_to_insert = []
        items_source = default_data_dict.items() if isinstance(default_data_dict, dict) else []

        for item_id, item_data_value in items_source:
            doc = {}
            if collection_name_from_config in [config.LOOT_TABLES_COLLECTION, config.EQUIPMENT_TABLES_COLLECTION]:
                doc = item_data_value.copy() if isinstance(item_data_value, dict) else {"table_data": item_data_value}
                doc["_id"] = item_id # Use the dict key as _id for these table types
            elif collection_name_from_config == config.ROOMS_COLLECTION:
                doc = item_data_value.copy()
                try: doc["_id"] = int(item_id)
                except ValueError: doc["_id"] = item_id
            else: # NPCs, Monsters, Items, Races
                if isinstance(item_data_value, dict):
                    doc = item_data_value.copy()
                    doc.setdefault("_id", item_id)
                else: continue # Skip non-dict items
            list_to_insert.append(doc)

        if list_to_insert:
            try:
                collection.insert_many(list_to_insert)
                print(f"DATA_LOADER: Collection '{collection_name_from_config}' initialized with {len(list_to_insert)} {data_desc}.")
            except Exception as e:
                print(f"DATA_LOADER: Error inserting into '{collection_name_from_config}': {e}")
    elif config.DEBUG_MODE:
        print(f"DATA_LOADER: Collection '{collection_name_from_config}' already has data. Skipping initialization for '{data_desc}'.")


def initialize_database_with_defaults():
    db = connection.get_db()
    if db is None:
        print("DATA_LOADER: ERROR - Database connection not available.")
        return
    print("DATA_LOADER: Initializing database with default data if collections are empty...")
    _initialize_collection(db, config.ITEMS_COLLECTION, default_items, 'DEFAULT_ITEM_TEMPLATES', "items")
    _initialize_collection(db, config.MONSTERS_COLLECTION, default_monsters, 'DEFAULT_MONSTER_TEMPLATES', "monster templates")
    _initialize_collection(db, config.NPCS_COLLECTION, default_npcs, 'DEFAULT_NPCS_TEMPLATES', "NPC templates")
    _initialize_collection(db, config.ROOMS_COLLECTION, default_rooms_data, 'DEFAULT_ROOMS', "rooms")
    _initialize_collection(db, config.LOOT_TABLES_COLLECTION, default_loot_data, 'DEFAULT_LOOT_TABLES', "loot tables")
    _initialize_collection(db, config.RACES_COLLECTION, default_race_data, 'DEFAULT_RACE_TEMPLATES', "race templates")
    _initialize_collection(db, config.EQUIPMENT_TABLES_COLLECTION, default_equipment_data, 'DEFAULT_EQUIPMENT_TABLES', "equipment tables")
    print("DATA_LOADER: Database initialization check complete.")


def _load_collection_to_dict(db, collection_name_from_config, data_key_desc, id_field="_id", data_field=None):
    if db is None:
        print(f"DATA_LOADER: DB not available, cannot load '{data_key_desc}'.")
        return {}
    data_dict = {}
    try:
        for item in db[collection_name_from_config].find():
            key = item.get(id_field)
            if key is not None:
                # For loot tables and equipment tables, if data_field is specified, we expect the actual data to be under that field.
                # Otherwise, the whole document is the value.
                data_dict[key] = item.get(data_field) if data_field and data_field in item else item
            elif config.DEBUG_MODE:
                 print(f"DATA_LOADER: Warning - Item in '{collection_name_from_config}' missing '{id_field}'. Item: {item}")
    except Exception as e:
        print(f"DATA_LOADER: Error loading collection '{collection_name_from_config}': {e}")
    if config.DEBUG_MODE or not data_dict:
        print(f"DATA_LOADER: Loaded {len(data_dict)} entries from '{collection_name_from_config}' into '{data_key_desc}'.")
    return data_dict


def _process_entity_equipment(entity_template, game_equipment_tables, game_items):
    """Helper to initialize the 'equipped' dict for an NPC or Monster template."""
    processed_template = copy.deepcopy(entity_template)
    # Initialize all equipment slots from config to None
    processed_template["equipped"] = {slot_key_cfg: None for slot_key_cfg in config.EQUIPMENT_SLOTS.keys()}

    equipment_table_id = processed_template.get("equipment_table_id")
    if equipment_table_id and game_equipment_tables:
        table_data = game_equipment_tables.get(equipment_table_id)
        # Equipment tables themselves are dicts, "slots" is a key inside them
        table_slots = table_data.get("slots", {}) if isinstance(table_data, dict) else {}


        if table_slots:
            for slot_key_in_table, item_id_to_equip in table_slots.items():
                if slot_key_in_table not in config.EQUIPMENT_SLOTS.keys():
                    if config.DEBUG_MODE: print(f"DEBUG EQUIP_LOAD: Invalid slot key '{slot_key_in_table}' in equip table '{equipment_table_id}' for '{processed_template.get('name')}'.")
                    continue

                if item_id_to_equip and item_id_to_equip in game_items:
                    item_data_for_slot_check = game_items[item_id_to_equip]
                    item_defined_slots = item_data_for_slot_check.get("slot", [])
                    if not isinstance(item_defined_slots, list): item_defined_slots = [item_defined_slots]

                    if slot_key_in_table in item_defined_slots:
                        processed_template["equipped"][slot_key_in_table] = item_id_to_equip
                        if config.DEBUG_MODE: print(f"DEBUG EQUIP_LOAD: Pre-equipped '{item_id_to_equip}' to '{slot_key_in_table}' for entity '{processed_template.get('name')}'.")
                    elif config.DEBUG_MODE: print(f"DEBUG EQUIP_LOAD_WARN: Item '{item_id_to_equip}' cannot go in slot '{slot_key_in_table}' as per item's slots {item_defined_slots} for '{processed_template.get('name')}'.")
                elif config.DEBUG_MODE: print(f"DEBUG EQUIP_LOAD_WARN: Item_id '{item_id_to_equip}' from equip table '{equipment_table_id}' not in GAME_ITEMS for '{processed_template.get('name')}'.")
        elif config.DEBUG_MODE and equipment_table_id: # Only warn if an ID was given but table not found or no slots
            print(f"DEBUG EQUIP_LOAD_WARN: Equipment table ID '{equipment_table_id}' not found or has no 'slots' entry for '{processed_template.get('name')}'.")
    return processed_template


def load_all_game_data():
    db = connection.get_db()
    if db is None:
        print("DATA_LOADER: ERROR - Database connection not available.")
        return {"items": {}, "monster_templates": {}, "npc_templates": {}, "rooms": {}, "loot_tables": {}, "races": {}, "equipment_tables": {}}

    print("DATA_LOADER: Loading all game data from MongoDB...")
    all_data = {}

    all_data["items"] = _load_collection_to_dict(db, config.ITEMS_COLLECTION, "items")
    all_data["loot_tables"] = _load_collection_to_dict(db, config.LOOT_TABLES_COLLECTION, "loot_tables", data_field="table_data") # Expects table_data field
    all_data["races"] = _load_collection_to_dict(db, config.RACES_COLLECTION, "races")
    all_data["equipment_tables"] = _load_collection_to_dict(db, config.EQUIPMENT_TABLES_COLLECTION, "equipment_tables") # Loads the whole doc

    raw_npcs = _load_collection_to_dict(db, config.NPCS_COLLECTION, "npc_templates")
    all_data["npc_templates"] = {}
    for npc_id, npc_template in raw_npcs.items():
        all_data["npc_templates"][npc_id] = _process_entity_equipment(npc_template, all_data["equipment_tables"], all_data["items"])

    raw_monsters = _load_collection_to_dict(db, config.MONSTERS_COLLECTION, "monster_templates")
    all_data["monster_templates"] = {}
    for monster_id, monster_template in raw_monsters.items():
        all_data["monster_templates"][monster_id] = _process_entity_equipment(monster_template, all_data["equipment_tables"], all_data["items"])
    
    raw_rooms = _load_collection_to_dict(db, config.ROOMS_COLLECTION, "rooms")
    all_data["rooms"] = {}
    for k, v in raw_rooms.items():
        try: all_data["rooms"][int(k)] = v
        except ValueError: all_data["rooms"][k] = v; print(f"DATA_LOADER: Room ID '{k}' kept as string key.") if config.DEBUG_MODE else None

    print("DATA_LOADER: Game data loading process complete.")
    return all_data

# ... (if __name__ == '__main__': block) ...

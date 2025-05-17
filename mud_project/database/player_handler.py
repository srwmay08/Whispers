# mud_project/database/player_handler.py
from bson import ObjectId # For handling MongoDB's _id
import traceback # For detailed error logging
from . import connection as db_connection # Using relative import with alias

try:
    import config # From mud_project/config.py
    from classes import player as player_class # From mud_project/classes/player.py
    from . import connection as db_connection # Relative import for db_connection
except ImportError as e:
    print(f"ERROR in player_handler.py: Critical module import failed: {e}")
    # Consider re-raising the error if these are truly critical for the module to function
    # For now, will allow it to proceed which might lead to errors later if config or player_class is None
    # Fallback for config if not found (less ideal than ensuring it's always available)
    class MockConfigPlayerHandler:
        DEBUG_MODE = True
        PLAYERS_COLLECTION = "players" # Default fallback
    if 'config' not in locals(): config = MockConfigPlayerHandler()
    if 'player_class' not in locals(): player_class = None # Or a mock player class

def save_player(player_object: player_class.Player) -> bool:
    """Saves player data to MongoDB."""
    if not player_object or not hasattr(player_object, 'name') or not player_object.name:
        if config.DEBUG_MODE: print("DEBUG HANDLER ERROR: Invalid player object or player name for saving.")
        return False

    db = db_connection.get_db() # Get the database object
    if db is None:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER ERROR: Database connection not available. Cannot save player '{player_object.name}'.")
        return False
    
    try:
        players_coll = db[config.PLAYERS_COLLECTION] # Access collection from db object
    except Exception as e:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER ERROR: Could not get players collection '{config.PLAYERS_COLLECTION}' for saving. Error: {e}")
        return False


    if config.DEBUG_MODE:
        print(f"DEBUG HANDLER: Attempting to save player '{player_object.name}' (SID: {getattr(player_object, 'sid', 'N/A')})")

    if not hasattr(player_object, 'to_dict') or not callable(player_object.to_dict):
        print(f"ERROR HANDLER (save_player): Player object for '{player_object.name}' does not have a callable to_dict method.")
        return False
        
    player_data = player_object.to_dict()
    player_data["name_lower"] = player_object.name.lower()

    player_data.pop('sid', None)
    player_data.pop('creation_data', None)
    # player_data.pop('_queued_messages', None) # Also consider if this should be persisted

    try:
        db_id_to_use = None
        # Use player_object.db_id if it exists and is a valid ObjectId or string convertible to one
        player_db_id_attr = getattr(player_object, 'db_id', None)
        if player_db_id_attr:
            if isinstance(player_db_id_attr, ObjectId):
                db_id_to_use = player_db_id_attr
            elif isinstance(player_db_id_attr, str):
                try:
                    db_id_to_use = ObjectId(player_db_id_attr)
                except Exception: # bson.errors.InvalidId or similar
                    if config.DEBUG_MODE: print(f"DEBUG HANDLER WARNING: Player {player_object.name} has an invalid string format for db_id: {player_db_id_attr}. Will attempt save/upsert by name_lower.")
            else:
                 if config.DEBUG_MODE: print(f"DEBUG HANDLER WARNING: Player {player_object.name} has an unexpected type for db_id: {type(player_db_id_attr)}. Will attempt save/upsert by name_lower.")


        if db_id_to_use:
            if config.DEBUG_MODE: print(f"DEBUG HANDLER: Updating player '{player_object.name}' by _id: {db_id_to_use}")
            # Ensure the _id itself is not in the $set part of the update
            update_data = {k: v for k, v in player_data.items() if k != '_id'}
            result = players_coll.update_one(
                {"_id": db_id_to_use},
                {"$set": update_data} # Use the filtered update_data
            )
            if config.DEBUG_MODE:
                if result.modified_count > 0:
                    print(f"DEBUG HANDLER: Player '{player_object.name}' data updated (ID: {db_id_to_use}). Matched: {result.matched_count}, Modified: {result.modified_count}")
                else: # Matched but no changes, or not matched (shouldn't happen if db_id_to_use was valid)
                    print(f"DEBUG HANDLER: Player '{player_object.name}' (ID: {db_id_to_use}) data update attempted. Matched: {result.matched_count}, Modified: {result.modified_count}.")
            return True # Return true even if no fields were modified, as long as the operation didn't error.
        else:
            if config.DEBUG_MODE: print(f"DEBUG HANDLER: Upserting player '{player_object.name}' by name_lower: {player_data['name_lower']}")
            # When upserting, MongoDB will create _id if it doesn't exist in player_data
            # or if player_data['_id'] is None.
            # It's generally safer to let MongoDB generate _id on insert or ensure player_data doesn't have an invalid _id.
            # If player_data contains an _id from a previous load that was stringified, it's fine.
            # If it's a new player, _id should not be in player_data.
            if "_id" in player_data and player_data["_id"] is None: # Clean up if _id is explicitly None
                del player_data["_id"]

            result = players_coll.update_one(
                {"name_lower": player_data["name_lower"]},
                {"$set": player_data},
                upsert=True
            )
            if result.upserted_id:
                player_object.db_id = result.upserted_id
                if config.DEBUG_MODE: print(f"DEBUG HANDLER: New player '{player_object.name}' saved with _id {player_object.db_id}.")
            elif result.modified_count > 0:
                if config.DEBUG_MODE: print(f"DEBUG HANDLER: Player '{player_object.name}' data updated by name_lower. Matched: {result.matched_count}, Modified: {result.modified_count}")
                # If updated by name and db_id wasn't set, fetch and set it.
                if not player_db_id_attr: # Check original attribute, not db_id_to_use
                    player_doc = players_coll.find_one({"name_lower": player_data["name_lower"]}, {"_id": 1})
                    if player_doc and "_id" in player_doc:
                        player_object.db_id = player_doc["_id"]
                        if config.DEBUG_MODE: print(f"DEBUG HANDLER: Updated player_object.db_id to {player_object.db_id} after name_lower update.")
            else:
                 if config.DEBUG_MODE: print(f"DEBUG HANDLER: Player '{player_object.name}' (name_lower: {player_data['name_lower']}) upsert: Matched: {result.matched_count}, Mod: {result.modified_count}, UpsertedID: {result.upserted_id}.")
            return True
    except Exception as e:
        print(f"ERROR HANDLER: Exception during save_player for '{player_object.name}': {e}")
        traceback.print_exc()
        return False

def load_player(player_name_lower, sid_on_load, game_races_data=None, game_items_data=None): # Added new parameters
    db = db_connection.get_db()
    if db is None:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER: DB not available for loading player {player_name_lower}.")
        return None

    player_data_from_db = db[config.PLAYERS_COLLECTION].find_one({"name_lower": player_name_lower})

    if player_data_from_db:
        try:
            # Pass the new arguments to Player.from_dict
            player_obj = player_class.Player.from_dict(player_data_from_db, sid_on_load, game_races_data, game_items_data)
            if config.DEBUG_MODE:
                print(f"DEBUG HANDLER: Player '{player_obj.name}' (SID: {sid_on_load}) loaded successfully.")
            return player_obj
        except Exception as e:
            print(f"ERROR HANDLER: Failed to instantiate player {player_name_lower} from DB data: {e}")
            traceback.print_exc()
            return None
    else:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER: Player '{player_name_lower}' not found in database.")
        return None

def player_exists(player_name: str) -> bool:
    """Checks if a player exists in the database by name (case-insensitive)."""
    if not player_name:
        if config.DEBUG_MODE: print("DEBUG HANDLER: player_exists called with empty name.")
        return False

    db = db_connection.get_db() # Get the database object
    if db is None:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER ERROR: Database connection not available. Cannot check if player '{player_name}' exists.")
        return False # Or raise an exception
    
    try:
        players_coll = db[config.PLAYERS_COLLECTION] # Access collection from db object
    except Exception as e:
        if config.DEBUG_MODE: print(f"DEBUG HANDLER ERROR: Could not get players collection '{config.PLAYERS_COLLECTION}' for player_exists check. Error: {e}")
        return False
    
    name_lower_case = player_name.lower()
    if config.DEBUG_MODE:
        print(f"DEBUG HANDLER: player_exists called for Name: '{player_name}' (checking as '{name_lower_case}')")
    
    try:
        count = players_coll.count_documents({"name_lower": name_lower_case})
        exists = count > 0
        if config.DEBUG_MODE:
            print(f"DEBUG HANDLER: count_documents for '{name_lower_case}' returned {count}. Exists: {exists}")
        return exists
    except Exception as e:
        print(f"ERROR HANDLER: Exception checking if player {player_name} exists: {e}")
        traceback.print_exc()
        return False
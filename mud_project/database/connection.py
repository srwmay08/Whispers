# mud_project/database/connection.py
from pymongo import MongoClient
import sys # For sys.exit
try:
    import config # Your main config file
except ImportError:
    print("ERROR (database/connection.py): config.py not found. Cannot establish database connection.")
    # Define a fallback or exit if config is critical
    class MockConfigDB: # Minimal config for DB connection if main config fails
        MONGO_URI = "mongodb://localhost:27017/"
        DATABASE_NAME = "whispers_game_fallback"
    config = MockConfigDB()


client = None
db = None

def connect_to_mongo():
    global client, db
    if db is not None:
        if config.DEBUG_MODE: print("MongoDB connection already established.")
        return db

    mongo_uri = getattr(config, 'MONGO_URI', "mongodb://localhost:27017/")
    database_name = getattr(config, 'DATABASE_NAME', 'whispers_game')

    try:
        if config.DEBUG_MODE: print(f"Attempting to connect to MongoDB at {mongo_uri}...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000) # Added timeout
        client.admin.command('ping') # Verify connection
        db = client[database_name]
        if config.DEBUG_MODE: print(f"Successfully connected to MongoDB. Database: '{database_name}'")
        return db
    except Exception as e:
        print(f"ERROR: Could not connect to MongoDB at {mongo_uri}. Check if MongoDB is running. Error: {e}")
        # Depending on how critical DB is at startup, you might sys.exit()
        # For now, we'll allow it to proceed and data_loader will use a potentially None db
        db = None # Ensure db is None if connection fails
        return None


def get_db(): # <--- THIS IS THE FUNCTION data_loader.py NEEDS
    global db
    if db is None:
        # Attempt to connect if db is None. This can happen if connect_to_mongo wasn't called
        # or if it failed initially.
        print("WARNING (get_db): Database connection is None. Attempting to reconnect...")
        connect_to_mongo() # Try to establish the connection
    
    if db is None and config.DEBUG_MODE: # If still None after trying
        print("CRITICAL (get_db): Database is still None after attempting connection. Operations requiring DB will likely fail.")
    return db


def close_mongo_connection():
    global client, db
    if client:
        client.close()
        if config.DEBUG_MODE: print("MongoDB connection closed.")
        client = None
        db = None

if __name__ == '__main__':
    # Example usage/test
    connect_to_mongo()
    db_instance = get_db()
    if db_instance:
        print(f"Successfully got DB instance: {db_instance.name}")
        print("Collections:", db_instance.list_collection_names())
    else:
        print("Failed to get DB instance.")
    close_mongo_connection()
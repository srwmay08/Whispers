# mud_project/game_data/equipment_tables.py
"""
Defines default equipment sets for NPCs and Monsters.
Items listed here are item_ids from default_items.py.
"""

# Import EQUIPMENT_SLOTS from config to ensure consistency if you want to validate slot keys
# from .. import config # Assuming this file is in game_data and config is one level up

DEFAULT_EQUIPMENT_TABLES = {
    "timothy_town_crier_gear": {
        "description": "Standard town crier attire and bell.",
        "slots": {
            # Using keys from your detailed list (ensure they match config.EQUIPMENT_SLOTS keys)
            "torso": "old_tunic",           # Item ID for an old tunic
            "mainhand": "town_crier_bell",  # His bell, used as a "weapon" or tool
            # "head": "simple_cap",        # Example: if he wore a cap
            # "feet_boots": "worn_shoes"   # Example: if he wore shoes
        },
        # Define which of the *equipped* items from "slots" above should always drop
        "always_drop_equipped": ["town_crier_bell"], 
        # For other equipped items not in 'always_drop_equipped', what's their chance to drop?
        "chance_drop_other_equipped_percent": 0.25, # e.g., 25% chance his tunic drops
        # If an item is marked "droppable_on_death: False" in items.py, it won't drop even if listed here,
        # unless 'always_drop_equipped' overrides it. This provides multiple layers of control.
    },
    "goblin_archer_basic_kit": {
        "description": "Typical gear for a goblin archer.",
        "slots": {
            "torso": "patchwork_jerkin_goblin", # You'll need to define this item
            "mainhand": "crude_shortbow_goblin", # You'll need to define this item
            # "shoulder_slung": "crude_quiver_arrows" # Example for a quiver
        },
        "always_drop_equipped": ["crude_shortbow_goblin"], # Always drops his bow
        "chance_drop_other_equipped_percent": 0.50 # 50% chance his jerkin drops
    },
    "oakhaven_guard_standard_issue": {
        "description": "Standard Oakhaven Guard equipment.",
        "slots": {
            "torso": "boiled_leather_armor", # Defined in your NPCs
            "mainhand": "guard_spear",       # Defined in your NPCs
            "offhand": "oakhaven_shield",    # Defined in your NPCs
            # "head": "oakhaven_guard_helm"  # Example
        },
        "always_drop_equipped": [], # Maybe they don't always drop their main gear
        "chance_drop_other_equipped_percent": 0.15 # Low chance for uniform pieces to drop
    }
    # Add more equipment tables as needed for other NPCs and monsters
}

# Helper function (optional)
def get_equipment_table(table_id):
    return DEFAULT_EQUIPMENT_TABLES.get(table_id)

if __name__ == '__main__':
    print("Available Equipment Table IDs:")
    for table_id in DEFAULT_EQUIPMENT_TABLES.keys():
        print(f"- {table_id}")

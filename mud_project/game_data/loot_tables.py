# mud_project/game_data/loot_tables.py
"""
Defines loot tables for monsters and other game entities.
"""

DEFAULT_LOOT_TABLES = {
    "no_loot": [],

    "giant_rat_common_loot": [
        {"item_id": "rat_tail", "chance": 0.75, "quantity": 1, "notes": "A common drop."},
        {"item_id": "ruined_pelt", "chance": 0.40, "quantity": 1, "requires_skinning": True, "skinning_skill_dc": 8, "notes": "Obtained by skinning."},
        {"item_id": "small_bones", "chance": 0.50, "quantity": [1, 3], "notes": "Generic bones."},
        {"item_id": "small_pouch_coins", "chance": 0.10, "quantity": 1, "notes": "A very small chance for a few coins (1-5 copper)."} # Standardized coin pouch
    ],

    "goblin_basic_loot": [
        {"item_id": "goblin_ear", "chance": 0.60, "quantity": [1, 2], "notes": "Proof of a goblin kill."},
        {"item_id": "rusty_dagger_goblin", "chance": 0.15, "quantity": 1},
        {"item_id": "moldy_bread", "chance": 0.30, "quantity": 1}, # Standardized
    ],

    "kobold_warrior_loot": [ # Moved from monster direct loot
        {"item_id": "kobold_tooth_necklace", "chance": 0.20, "quantity": 1},
        {"item_id": "kobold_spear", "chance": 0.10, "quantity": 1}, # Already in items
        {"item_id": "small_pouch_coins", "chance": 0.4, "quantity": 1, "notes": "Yields 3-10 coins"}, # Standardized
        {"item_id": "shiny_rock", "chance": 0.15, "quantity": [1,2]}
    ],

    "goblin_archer_loot": [ # Moved from monster direct loot
        {"item_id": "goblin_shiv", "chance": 0.15, "quantity": 1}, # Already in items
        {"item_id": "arrow_bundle_crude", "chance": 0.5, "quantity": 1, "notes": "Bundle of 3-8 crude arrows."}, # Quantity for bundle, not individual arrows
        {"item_id": "moldy_bread", "chance": 0.2, "quantity": 1} # Standardized
    ],

    "training_dummy_loot": [ # Moved from monster direct loot
        {"item_id": "straw_pile", "chance": 0.8, "quantity": [1,3]},
        {"item_id": "splintered_wood", "chance": 0.5, "quantity": [1,2]}
    ],

    "timothy_town_crier_loot": [
        {"item_id": "crumpled_news_scroll", "chance": 0.75, "quantity": 1 },
        {"item_id": "small_pouch_coins", "chance": 0.30, "quantity": 1 , "notes": "Yields 1-5 coins"}, # Standardized
    ],

    # New Loot Tables for NPCs
    "grom_blacksmith_loot": [
        {"item_id": "iron_ingot", "chance": 0.3, "quantity": [1,2]},
        {"item_id": "hammer_handle", "chance": 0.1, "quantity": 1},
        {"item_id": "groms_lucky_charm", "chance": 0.01, "quantity": 1}
    ],
    "oakhaven_guard_loot": [
        {"item_id": "oakhaven_sigil_cloth", "chance": 0.1, "quantity": 1},
        {"item_id": "waterskin", "chance": 0.05, "quantity": 1, "notes": "May contain water or be empty"},
        {"item_id": "small_pouch_coins", "chance": 0.15, "quantity": 1, "notes": "A few coins"}
    ],
    "nervous_guard_loot": [
        {"item_id": "half_eaten_apple", "chance": 0.2, "quantity": 1},
        {"item_id": "oakhaven_sigil_cloth", "chance": 0.05, "quantity": 1}
    ],
    "master_elmsworth_loot": [
        {"item_id": "coin_pouch_modest", "chance": 0.5, "quantity": 1},
        {"item_id": "official_looking_document", "chance": 0.1, "quantity": 1},
        {"item_id": "spectacles", "chance": 0.02, "quantity": 1}
    ],
    "elder_rowan_loot": [
        {"item_id": "oakhaven_town_seal_replica", "chance": 0.05, "quantity": 1},
        {"item_id": "scroll_of_local_history", "chance": 0.1, "quantity": 1}
    ],
    "arya_peddler_loot": [ # Peddlers might not drop much, maybe some of their cheaper wares
        {"item_id": "healing_draught_minor", "chance": 0.05, "quantity": 1},
        {"item_id": "torch", "chance": 0.10, "quantity": 1},
        {"item_id": "small_pouch_coins", "chance": 0.20, "quantity": 1}
    ]
}

def get_loot_table(table_id): # Optional helper
    return DEFAULT_LOOT_TABLES.get(table_id)

if __name__ == '__main__':
    print("Available Loot Table IDs:")
    for table_id in DEFAULT_LOOT_TABLES.keys():
        print(f"- {table_id}")
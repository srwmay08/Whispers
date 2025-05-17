# mud_project/game_data/default_items.py

# Import EQUIPMENT_SLOTS from config to use for validation or consistency
# from .. import config # If config.py is one level up

DEFAULT_ITEM_TEMPLATES = {
    "rusty_sword": {
        "_id": "rusty_sword",
        "name": "Rusty Sword",
        "description": "A pitted and worn sword...",
        "type": "weapon",
        "slot": ["mainhand", "offhand"], # Validated against config.EQUIPMENT_SLOTS keys
        "occupies_slots": ["none"],
        "skill": "edged_weapons", 
        "damage": "1d4",          
        "weapon_as_bonus": -2,
        "enchantment_as_bonus": 0,
        "avd_modifiers": {"unarmored": 5, "cloth": 3, "leather": 0, "chain": -5, "plate": -10},
        "weight": 4, "value": 8, "rarity": "common",
        "keywords": ["sword", "rusty", "blade", "weapon"],
        "droppable_on_death": True # Default, can be overridden by NPC/Monster specific flags
    },
    "old_tunic": {
        "_id": "old_tunic",
        "name": "Old Tunic",
        "description": "A simple tunic made of coarse, faded fabric.",
        "type": "armor",
        "slot": ["torso"], # Use a key from EQUIPMENT_SLOTS, e.g., config.EQUIPMENT_SLOTS["torso"]
        "occupies_slots": ["torso"],
        "armor_type": "cloth",   # Crucial for combat calculations
        "armor_ds_bonus": 3,     
        "enchantment_ds_bonus": 0,
        "weight": 2, "value": 5, "rarity": "common",
        "keywords": ["tunic", "old", "cloth", "armor", "chestpiece"],
        "droppable_on_death": True
    },
    "town_crier_bell": {
        "_id": "town_crier_bell", 
        "type": "tool", # Or "weapon" if it can be used as such
        "name": "Town Crier's Bell",
        "slot": ["mainhand", "offhand"], # Can be held
        "weight": 1.0, 
        "description": "A sturdy brass bell, well-polished from frequent use.",
        "rarity": "uncommon", "value": 15,
        "keywords": ["bell", "crier", "tool", "brass"],
        "droppable_on_death": True, # Timothy might always drop this based on equipment table
        # If it can be used as an improvised weapon:
        "skill": "brawling", # or "blunt_weapons"
        "damage": "1d3", 
        "weapon_as_bonus": -5, # Not designed for combat
        "avd_modifiers": {"unarmored": 0, "cloth": 0, "leather": -2, "chain": -5, "plate": -8},
    },
    "patchwork_jerkin_goblin": { # New item example for goblin archer
        "_id": "patchwork_jerkin_goblin",
        "name": "Patchwork Goblin Jerkin",
        "description": "A crudely stitched jerkin of various animal hides and rags.",
        "type": "armor",
        "slot": ["torso"],
        "occupies_slots": ["torso"],
        "armor_type": "leather", # Treat as light leather
        "armor_ds_bonus": 4,
        "enchantment_ds_bonus": 0,
        "weight": 1.5, "value": 3, "rarity": "common",
        "keywords": ["jerkin", "goblin", "patchwork", "armor"],
        "droppable_on_death": True
    },
    "crude_shortbow_goblin": { # New item example for goblin archer
        "_id": "crude_shortbow_goblin",
        "name": "Crude Goblin Shortbow",
        "description": "A poorly made shortbow, prone to snapping.",
        "type": "weapon",
        "slot": ["mainhand"], # Typically bows are two-handed in concept, but occupy mainhand slot for this system
        "skill": "ranged_weapons",
        "damage": "1d4",
        "weapon_as_bonus": -3,
        "enchantment_as_bonus": 0,
        "avd_modifiers": {}, # Ranged weapons might not use AVD in the same way, or have their own system
        "weight": 1, "value": 2, "rarity": "common",
        "keywords": ["bow", "shortbow", "goblin", "weapon"],
        "droppable_on_death": True
    },
    # --- Ensure ALL your items, especially armor and weapons, have:
    # 1. "slot": A valid key (or list of keys) from config.EQUIPMENT_SLOTS
    # 2. "armor_type": (for armor) e.g., "cloth", "leather", "plate", "unarmored" (or config.DEFAULT_UNARMORED_TYPE)
    # 3. "droppable_on_death": True (or False if it should never be regular loot when equipped)
    # Example:
    "kobold_spear": {
        "_id": "kobold_spear", "type": "weapon", 
        "slot": ["mainhand"], # Can also be "twohand" if it requires two hands
        "skill": "polearm_weapons",
        "name": "Kobold Spear", "damage": "1d6-1", "weapon_as_bonus": -1, "enchantment_as_bonus": 0,
        "avd_modifiers": {"unarmored": 8, "cloth": 5, "leather": 2, "chain": -2, "plate": -6},
        "description": "A crudely made spear...",
        "weight": 3, "value": 6, "rarity": "common", "keywords": ["spear", "kobold", "polearm", "weapon"],
        "droppable_on_death": True
    },
    "boiled_leather_armor": { # From Oakhaven Guard
        "_id": "boiled_leather_armor",
        "name": "Boiled Leather Armor",
        "description": "Standard issue armor for Oakhaven guards, made of hardened leather.",
        "type": "armor",
        "slot": ["torso"],
        "occupies_slots": ["torso"],
        "armor_type": "leather",
        "armor_ds_bonus": 8, # Example value
        "enchantment_ds_bonus": 0,
        "weight": 15, "value": 40, "rarity": "common",
        "keywords": ["leather", "armor", "guard", "boiled"],
        "droppable_on_death": True # Guards might drop their armor
    },
    "guard_spear": { # From Oakhaven Guard
        "_id": "guard_spear",
        "name": "Guard's Spear",
        "description": "A standard military spear, well-maintained.",
        "type": "weapon",
        "slot": ["mainhand"], # Or "twohand"
        "skill": "polearm_weapons",
        "damage": "1d6+1",
        "weapon_as_bonus": 2,
        "enchantment_as_bonus": 0,
        "avd_modifiers": {"unarmored": 10, "cloth": 7, "leather": 3, "chain": 0, "plate": -4},
        "weight": 4, "value": 12, "rarity": "common",
        "keywords": ["spear", "guard", "polearm", "weapon"],
        "droppable_on_death": True
    },
    "oakhaven_shield": { # From Oakhaven Guard
        "_id": "oakhaven_shield",
        "name": "Oakhaven Shield",
        "description": "A sturdy wooden shield bearing the oak leaf insignia.",
        "type": "shield",
        "slot": ["offhand"],
        "shield_ds_bonus": 10, # Example value
        "enchantment_ds_bonus": 0,
        "weight": 6, "value": 18, "rarity": "common",
        "keywords": ["shield", "oakhaven", "guard"],
        "droppable_on_death": True
    }
    # ... and so on for all your other items
}

# mud_project/game_data/default_items.py

# Import EQUIPMENT_SLOTS from config to use for validation or consistency
# from .. import config # If config.py is one level up

DEFAULT_ITEM_TEMPLATES = {
    # ... your existing items ...
    "crumpled_news_scroll": {
        "_id": "crumpled_news_scroll",
        "name": "Crumpled News Scroll",
        "description": "A hastily written scroll with the latest (and perhaps embellished) news from around the region.",
        "type": "readable", # or "junk", "note"
        "slot": [], # Not equippable
        "weight": 0.1, "value": 1, "rarity": "common",
        "keywords": ["scroll", "news", "crumpled", "parchment"],
        "droppable_on_death": True,
        # "read_text": "Hear ye, hear ye! The price of ale is up again!" # Optional if readable
    },
    "small_pouch_coins": { # This item would represent a container of coins
        "_id": "small_pouch_coins",
        "name": "Small Pouch of Coins",
        "description": "A small leather pouch, jingling faintly.",
        "type": "currency_pouch", # A special type to indicate it contains gold
        "slot": [],
        "weight": 0.2, "value": 0, # The value is in the coins it yields
        "rarity": "common",
        "keywords": ["pouch", "coins", "money", "gold", "silver"],
        "droppable_on_death": True,
        # You might add min_gold/max_gold here if the pouch itself dictates the amount
        "min_gold": 10,
        "max_gold": 100,
    },
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
        "name": "Kobold Spear", "weapon_as_bonus": -1, "enchantment_as_bonus": 0,
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
    },
    "goblin_shiv": {
        "_id": "goblin_shiv",
        "name": "Goblin Shiv",
        "description": "A nasty-looking, sharpened piece of scrap metal. Clearly of goblin make.",
        "type": "weapon",
        "slot": ["mainhand", "offhand"],
        "skill": "edged_weapons", # Or perhaps "brawling" if it's very crude
        "damage": "1d4-1", # Worse than a proper dagger
        "weapon_as_bonus": -1,
        "enchantment_as_bonus": 0,
        "avd_modifiers": {"unarmored": 2, "cloth": 1, "leather": 0, "chain": -3, "plate": -6},
        "weight": 0.5, "value": 1, "rarity": "trash",
        "keywords": ["shiv", "goblin", "dagger", "crude", "weapon", "edged"],
        "droppable_on_death": True
    },
    "arrow_bundle_crude": {
        "_id": "arrow_bundle_crude",
        "name": "Bundle of Crude Arrows",
        "description": "A small bundle of poorly fletched arrows with sharpened wooden or bone tips.",
        "type": "ammunition_bundle", # Special type to indicate it yields multiple arrows
        "slot": [], # Not equippable directly
        "weight": 0.5, "value": 2, "rarity": "common",
        "keywords": ["arrows", "bundle", "crude", "ammunition", "ammo"],
        "droppable_on_death": True,
        "yields_item_id": "arrow_crude", # The ID of the individual arrow item
        "yields_quantity_min": 3,
        "yields_quantity_max": 8
    },
    "arrow_crude": { # Individual arrow, not directly in loot tables but yielded by bundle
        "_id": "arrow_crude",
        "name": "Crude Arrow",
        "description": "A poorly made arrow, likely to break on impact.",
        "type": "ammunition",
        "slot": [],
        "weight": 0.05, "value": 0, "rarity": "trash", # Individual arrows often have no value
        "keywords": ["arrow", "crude", "ammunition", "ammo"],
        "droppable_on_death": True # If a player has individual arrows
    },
    "moldy_bread": {
        "_id": "moldy_bread",
        "name": "Moldy Bread",
        "description": "A hunk of bread with visible patches of green and blue mold. Smells terrible.",
        "type": "food", # Or "junk"
        "slot": [],
        "weight": 0.3, "value": 0, "rarity": "trash",
        "keywords": ["bread", "moldy", "food", "stale"],
        "droppable_on_death": True,
        # "effects_on_consume": [{"type": "damage", "amount": "1d2", "damage_type": "poison"}, {"type": "status", "status_id": "nausea", "duration": 60}] # Example
    },
    "rat_tail": {
        "_id": "rat_tail",
        "name": "Rat Tail",
        "description": "The severed tail of a giant rat. Surprisingly tough.",
        "type": "crafting_material", # Or "junk", "trophy"
        "slot": [],
        "weight": 0.1, "value": 1, "rarity": "common",
        "keywords": ["rat", "tail", "trophy", "vermin"],
        "droppable_on_death": True
    },
    "ruined_pelt": {
        "_id": "ruined_pelt",
        "name": "Ruined Pelt",
        "description": "A tattered and torn piece of animal hide, mostly useless due to poor skinning or damage.",
        "type": "junk", # Or "crafting_material_poor"
        "slot": [],
        "weight": 0.5, "value": 0, "rarity": "trash",
        "keywords": ["pelt", "hide", "ruined", "tattered", "fur"],
        "droppable_on_death": True
    },
     "rat_pelt_clean": {
        "_id": "rat_pelt_clean",
        "name": "Clean Rat Pelt",
        "description": "The surprisingly intact pelt of a giant rat, carefully skinned.",
        "type": "crafting_material", 
        "slot": [],
        "weight": 0.4, "value": 3, "rarity": "common",
        "keywords": ["pelt", "hide", "rat", "fur", "clean"],
        "droppable_on_death": True
    },
    "small_bones": {
        "_id": "small_bones",
        "name": "Small Bones",
        "description": "A handful of small, unremarkable animal bones.",
        "type": "crafting_material", # Or "junk"
        "slot": [],
        "weight": 0.3, "value": 1, "rarity": "common",
        "keywords": ["bones", "small", "fragments"],
        "droppable_on_death": True
    },
    "kobold_scales_patch": {
        "_id": "kobold_scales_patch",
        "name": "Patch of Kobold Scales",
        "description": "A small patch of dull, reptilian scales, likely from a kobold.",
        "type": "crafting_material",
        "slot": [],
        "weight": 0.2, "value": 2, "rarity": "common",
        "keywords": ["scales", "kobold", "hide", "patch"],
        "droppable_on_death": True
    },
    "tarnished_locket": { # From room 17
        "_id": "tarnished_locket",
        "name": "Tarnished Locket",
        "description": "A small, heart-shaped locket, its silver surface heavily tarnished. It might once have held a portrait.",
        "type": "trinket", # or "jewelry"
        "slot": ["neck"], # Can be worn
        "weight": 0.1, "value": 10, "rarity": "uncommon",
        "keywords": ["locket", "tarnished", "jewelry", "heart", "necklace"],
        "droppable_on_death": True,
        "look_description_ground": "A small, tarnished locket lies here, glinting faintly.",
        # "stat_bonuses": {"charisma": 1} # Example if it had a minor bonus
    }
}
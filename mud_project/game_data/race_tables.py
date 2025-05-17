# mud_project/game_data/race_tables.py
"""
Defines default playable races and their attributes.
This is the single source of truth for race definitions.
"""

DEFAULT_RACE_TEMPLATES = {
    "human": {
        "_id": "human",
        "name": "Human",
        "description": "Versatile and driven, humans adapt quickly to all walks of life.",
        "stat_modifiers": { # Flat +/- to base stats at creation
            "strength": 0, "stamina": 0, "dexterity": 0, "agility": 0, "constitution": 0,
            "charisma": 0, "intelligence": 0, "wisdom": 0, "logic": 0, "perception": 0,
            "aura": 0, "willpower": 0
        },
        # --- Modifiers for Derived Primary Stat Bonuses (StatValue // 50 + This_Mod) ---
        "strength_primary_bonus_mod": 0,
        "stamina_primary_bonus_mod": 0,
        "dexterity_primary_bonus_mod": 0,
        "agility_primary_bonus_mod": 0,
        "constitution_primary_bonus_mod": 0,
        "charisma_primary_bonus_mod": 1,     # Example: Humans are generally sociable
        "intelligence_primary_bonus_mod": 0,
        "wisdom_primary_bonus_mod": 1,       # Example: Humans have decent common sense
        "logic_primary_bonus_mod": 1,        # Example: Humans can be quite logical
        "perception_primary_bonus_mod": 0,
        "aura_primary_bonus_mod": 0,
        "willpower_primary_bonus_mod": 0,
        # --- Other Racial Attributes ---
        "skill_bonuses": { "survival": 5, "diplomacy": 3, "trading": 10 }, # From your race_tables
        "bonus_inventory": [], # From your race_tables
        "size": "medium",
        "speed": 30,
        "vision": "normal", # Standard vision
        "languages": ["common"],
        "resistances": {}, # e.g., "fire": 0.1 for 10% resistance
        "vulnerabilities": {}, # e.g., "cold": 0.1 for 10% vulnerability
        "racial_abilities": ["adaptability", "determination"], # Example names
        "factions": ["OakhavenCivilian"], # Default starting faction alignment
        "starting_zone_id": 1, # Ensure this room ID exists
        "lifespan": 80, # Average lifespan
        "reputation_modifiers": {}, # e.g., {"elves": 0.05} for slightly better starting rep
        "playable": True,
        "notes": "Well-rounded and adaptable, the baseline for many adventurers."
    },
    "elf": {
        "_id": "elf",
        "name": "Elf",
        "description": "Graceful and wise, elves live long and pursue mastery of mind, blade, or spell.",
        "stat_modifiers": {
            "strength": -5, "stamina": -5, "dexterity": 10, "agility": 5, "constitution": -10,
            "charisma": 0, "intelligence": 5, "wisdom": 5, "logic": 0, "perception": 5, # Adjusted Elf from your files
            "aura": 5, "willpower": 0
        },
        # --- Modifiers for Derived Primary Stat Bonuses ---
        "strength_primary_bonus_mod": -1,
        "stamina_primary_bonus_mod": 0,
        "dexterity_primary_bonus_mod": 1,
        "agility_primary_bonus_mod": 1,
        "constitution_primary_bonus_mod": -1,
        "charisma_primary_bonus_mod": 0,
        "intelligence_primary_bonus_mod": 1, # Good at deriving bonus from INT
        "wisdom_primary_bonus_mod": 1,       # Good at deriving bonus from WIS
        "logic_primary_bonus_mod": 0,
        "perception_primary_bonus_mod": 1,   # Keen senses enhance derived perception bonus
        "aura_primary_bonus_mod": 1,
        "willpower_primary_bonus_mod": 0,
        # --- Other Racial Attributes ---
        "skill_bonuses": { "ranged_weapons": 5, "arcane_symbols": 5, "active_perception": 3 }, # From your race_tables
        "bonus_inventory": ["elven_shortbow_starter", "quiver_arrows_basic"], # From your race_tables
        "size": "medium",
        "speed": 30, # Elves are often quick
        "vision": "darkvision", # Standard elven darkvision
        "languages": ["common", "elvish"],
        "resistances": {"charm": 0.25, "sleep": 0.5}, # Example: 25% vs charm, 50% vs sleep
        "vulnerabilities": {},
        "racial_abilities": ["keen_senses", "trance", "forest_stride"],
        "factions": ["ForestKin"], # Example faction
        "starting_zone_id": 1, # Was "elven_glade" (room_id for it?)
        "lifespan": 750,
        "reputation_modifiers": { "dwarves": -0.1, "orcs": -0.15 },
        "playable": True,
        "notes": "Agile, intelligent, and long-lived, with a natural affinity for magic and nature."
    },
    "dwarf": {
        "_id": "dwarf",
        "name": "Dwarf",
        "description": "Stout and sturdy, dwarves prize craftsmanship, honor, and strong ale.",
        "stat_modifiers": {
            "strength": 5, "stamina": 10, "dexterity": -5, "agility": -10, "constitution": 10, # Adjusted from your files
            "charisma": -5, "intelligence": 0, "wisdom": 0, "logic": 0, "perception": 0,
            "aura": -5, "willpower": 5
        },
        # --- Modifiers for Derived Primary Stat Bonuses ---
        "strength_primary_bonus_mod": 1,
        "stamina_primary_bonus_mod": 1,
        "dexterity_primary_bonus_mod": -1,
        "agility_primary_bonus_mod": -1,
        "constitution_primary_bonus_mod": 2, # Excellent derived CON bonus
        "charisma_primary_bonus_mod": -1,
        "intelligence_primary_bonus_mod": 0,
        "wisdom_primary_bonus_mod": 0,
        "logic_primary_bonus_mod": 0,
        "perception_primary_bonus_mod": 0,
        "aura_primary_bonus_mod": -1,
        "willpower_primary_bonus_mod": 1,
        # --- Other Racial Attributes ---
        "skill_bonuses": { "mining": 10, "axes": 5, "armor_crafting": 3 }, # From your race_tables
        "bonus_inventory": ["dwarven_ale_mug", "mining_pick_basic"], # From your race_tables
        "size": "medium", # Though short, they are broad
        "speed": 25, # Typically slower
        "vision": "darkvision",
        "languages": ["common", "dwarvish"],
        "resistances": {"poison": 0.20, "magic_constructs": 0.1}, # 20% poison resist, 10% vs constructs
        "vulnerabilities": {},
        "racial_abilities": ["stonecunning", "battle_fury", "hardiness"],
        "factions": ["IronholdClans"],
        "starting_zone_id": 1, # Was "mountain_pass"
        "lifespan": 350,
        "reputation_modifiers": { "elves": -0.05, "goblins": -0.1 },
        "playable": True,
        "notes": "Resilient and strong, with a knack for stonework and a distrust of flimsy things."
    },
    "dark_elf": {
        "_id": "dark_elf",
        "name": "Dark Elf",
        "description": "Sinister and graceful, dark elves are masters of shadow and subtle arts, thriving in the depths.",
        "stat_modifiers": { # Based on your race_tables, adjusted for balance
            "strength": -5, "stamina": -5, "dexterity": 10, "agility": 10, "constitution": -5,
            "charisma": 0, "intelligence": 5, "wisdom": 0, "logic": 0, "perception": 5,
            "aura": 5, "willpower": 5
        },
        # --- Modifiers for Derived Primary Stat Bonuses ---
        "strength_primary_bonus_mod": -1,
        "stamina_primary_bonus_mod": 0,
        "dexterity_primary_bonus_mod": 1,
        "agility_primary_bonus_mod": 1,
        "constitution_primary_bonus_mod": -1,
        "charisma_primary_bonus_mod": 0,
        "intelligence_primary_bonus_mod": 1,
        "wisdom_primary_bonus_mod": 0,
        "logic_primary_bonus_mod": 0,
        "perception_primary_bonus_mod": 1,
        "aura_primary_bonus_mod": 1,
        "willpower_primary_bonus_mod": 1, # Strong-willed
        # --- Other Racial Attributes ---
        "skill_bonuses": { "harness_power": 10, "stalking_and_hiding": 5, "edged_weapons": 3 }, # Adjusted "athletics"
        "bonus_inventory": ["obsidian_dagger", "dark_cloak_starter"], # Added cloak
        "size": "medium",
        "speed": 30,
        "vision": "superior_darkvision", # Better than standard darkvision
        "languages": ["common", "elvish", "undercommon"],
        "resistances": {"magic": 0.15, "shadow_magic": 0.25}, # Specific magic resist
        "vulnerabilities": {"sunlight_sensitivity": 0.1}, # Often a thematic weakness
        "racial_abilities": ["faerie_fire", "shadowmeld", "poison_craft"],
        "factions": ["HouseVelkryn"], # Example
        "starting_zone_id": 1, # Was "underdark_gate"
        "lifespan": 700,
        "reputation_modifiers": { "humans": -0.25, "elves": -0.5, "dwarves": -0.15 },
        "playable": True,
        "notes": "Stealthy and magically adept, accustomed to the darkness and its intrigues."
    },
    "troll": {
        "_id": "troll",
        "name": "Troll",
        "description": "Massive and brutally strong, trolls possess formidable regenerative capabilities but are notoriously dim-witted.",
        "stat_modifiers": { # Adjusted from your files for better balance as a playable race
            "strength": 20, "stamina": 15, "dexterity": -15, "agility": -15, "constitution": 20,
            "charisma": -15, "intelligence": -20, "wisdom": -10, "logic": -20, "perception": -5,
            "aura": -10, "willpower": 5
        },
        # --- Modifiers for Derived Primary Stat Bonuses ---
        "strength_primary_bonus_mod": 2,    # Excellent derived STR bonus
        "stamina_primary_bonus_mod": 1,
        "dexterity_primary_bonus_mod": -2,
        "agility_primary_bonus_mod": -2,
        "constitution_primary_bonus_mod": 2, # Excellent derived CON bonus
        "charisma_primary_bonus_mod": -2,
        "intelligence_primary_bonus_mod": -2,
        "wisdom_primary_bonus_mod": -1,
        "logic_primary_bonus_mod": -2,
        "perception_primary_bonus_mod": -1,
        "aura_primary_bonus_mod": -1,
        "willpower_primary_bonus_mod": 0,     # Not particularly strong or weak willed bonus-wise
        # --- Other Racial Attributes ---
        "skill_bonuses": { "unarmed_combat": 10, "intimidation": 5, "brawling": 5 }, # Merged and adjusted
        "bonus_inventory": ["bone_club", "scrap_hide_armor"], # Added basic armor
        "size": "large",
        "speed": 30, # Can be deceptively quick for their size
        "vision": "darkvision",
        "languages": ["trollish", "broken_common"],
        "resistances": {"bludgeoning": 0.05 }, # "slashing" was in config, "regeneration" is an ability
        "vulnerabilities": {"fire": 0.25, "acid": 0.15}, # From config
        "racial_abilities": ["regeneration", "powerful_smash", "fearsome_presence"], # "rend" -> powerful_smash
        "factions": ["GrukTharnTribe"], # Example
        "starting_zone_id": 1, # Was "troll_mire"
        "lifespan": 100, # Shorter, more violent lives typically
        "reputation_modifiers": { "humans": -0.5, "elves": -0.5, "dwarves": -0.4 },
        "playable": True,
        "notes": "Incredibly strong and regenerative, but lacking in intellect and social graces."
    }
}

# Function to easily access race data (optional, main.py will load the whole dict)
def get_race_template(race_id):
    return DEFAULT_RACE_TEMPLATES.get(race_id)
# mud_project/game_data/default_monsters.py
from config import DISPOSITION_PASSIVE, DISPOSITION_NEUTRAL, DISPOSITION_AGGRESSIVE, DISPOSITION_THREATENING, DISPOSITION_HOSTILE_GENERAL, THREATENING_DELAY_TICKS

DEFAULT_MONSTER_TEMPLATES = {
    "training_dummy": {
        "_id": "training_dummy", # Ensure _id matches key
        "name": "Training Dummy",
        "description": "A sturdy straw-filled dummy...",
        "hp": 30, "max_hp": 30, "defense": 0, "attack_damage": "0d0", "attack_delay": 999,
        "stats": { "strength": 20, "stamina": 100, "dexterity": 1, "agility": 1, "constitution": 100, "charisma": 1, "intelligence": 1, "wisdom": 1, "logic": 1, "perception": 1, "aura": 1, "willpower": 1},
        "spawn_config": {"respawn_time_seconds": 300, "spawn_chance": 0.75, "max_instances": 3},
        "faction_id": "NeutralConstructs", # Example faction for constructs
        "xp_value": 0, # No XP for dummies
        "keywords": ["dummy", "training", "practice"],
        "leaves_corpse": True, "loot_table_id": "training_dummy_loot",
        "skinnable": False,
        "aggression_behavior": {
            "base_disposition": DISPOSITION_PASSIVE, # Doesn't attack back
            "attacks_on_sight": False,
            "hostile_factions": [],
            "threatening_delay_ticks": 0
        },
        "ambient_actions": ["stands silently.", "wobbles slightly."]
    },
    "giant_rat": {
        "_id": "giant_rat",
        "name": "Giant Rat",
        "description": "An oversized rodent with beady red eyes...",
        "hp": 25, "max_hp": 25, "defense": 2, "attack_damage": "1d4", "attack_delay": 2.0,
        "stats": { "strength": 30, "stamina": 40, "dexterity": 45, "agility": 50, "constitution": 35, "charisma": 10, "intelligence": 15, "wisdom": 25, "logic": 10, "perception": 45, "aura": 5, "willpower": 20 },
        "skills": ["bite"],
        "spawn_config": {"respawn_time_seconds": 120, "spawn_chance": 0.8, "max_instances": 3}, # Adjusted respawn
        "faction_id": "Vermin",
        "xp_value": 10,
        "keywords": ["rat", "vermin", "rodent"],
        "leaves_corpse": True, "loot_table_id": "giant_rat_common_loot",
        "skinnable": True,
        "skinning": { "item_yield_success_key": "rat_pelt_clean", "item_yield_failed_key": "ruined_pelt", "skill_required": "survival", "base_dc": 5, "success_message":"...", "failure_message":"..."},
        "aggression_behavior": {
            "base_disposition": DISPOSITION_AGGRESSIVE,
            "attacks_on_sight": True, # Will attack players entering its room
            "hostile_factions": [],
            "threatening_delay_ticks": 0
        },
        "ambient_actions": ["scurries around nervously.", "twitches its whiskers."]
    },
    "goblin_archer": {
        "_id": "goblin_archer",
        "name": "Goblin Archer",
        "description": "A small, wiry humanoid with sickly green skin...",
        "hp": 35, "max_hp": 35, "defense": 3, "attack_damage": "1d4+1", "attack_delay": 2.8,
        "stats": { "strength": 35, "stamina": 45, "dexterity": 65, "agility": 60, "constitution": 40, "charisma": 25, "intelligence": 30, "wisdom": 35, "logic": 25, "perception": 60, "aura": 20, "willpower": 30},
        "skills": ["shoot_arrow", "hide_in_shadows"],
        "spawn_config": {"respawn_time_seconds": 260, "spawn_chance": 0.5, "max_instances": 2},
        "faction_id": "GreenSkinMarauders",
        "xp_value": 20,
        "keywords": ["goblin", "archer", "greenskin"],
        "leaves_corpse": True, "loot_table_id": "goblin_archer_loot",
        "equipment_table_id": "goblin_archer_basic_kit",
        "skinnable": True,
        "skinning": {"item_yield_success_key": "goblin_ear", "item_yield_failed_key": "ruined_pelt", "skill_required": "survival", "base_dc": 7, "success_message":"...", "failure_message":"..."},
        "aggression_behavior": {
            "base_disposition": DISPOSITION_AGGRESSIVE,
            "attacks_on_sight": True,
            "faction_hostility_threshold": -100, # Will attack players with low Greenskin faction too
            "hostile_factions": ["OakhavenCivilian", "ScaleScourgeClan"], # Attacks Oakhaven and Kobolds
            "threatening_delay_ticks": 0
        },
        "ambient_actions": ["cackles quietly.", "scans with shifty eyes."]
    },
    "kobold_warrior": {
        "_id": "kobold_warrior",
        "name": "Kobold Warrior",
        "description": "A small, reptilian humanoid with dull scales...",
        "hp": 40, "max_hp": 40, "defense": 5, "attack_damage": "1d6", "attack_delay": 2.3,
        "stats": { "strength": 45, "stamina": 50, "dexterity": 55, "agility": 50, "constitution": 45, "charisma": 20, "intelligence": 25, "wisdom": 30, "logic": 20, "perception": 50, "aura": 10, "willpower": 35},
        "skills": ["spear_thrust", "dodge_small"],
        "spawn_config": {"respawn_time_seconds": 240, "spawn_chance": 0.6, "max_instances": 3},
        "faction_id": "ScaleScourgeClan",
        "xp_value": 25,
        "keywords": ["kobold", "reptilian", "warrior"],
        "leaves_corpse": True, "loot_table_id": "kobold_warrior_loot",
        "equipment_table_id": None, # Define one or list items directly
        "items": ["kobold_spear"], # Example direct item
        "skinnable": True,
        "skinning": {"item_yield_success_key": "kobold_scales_patch", "item_yield_failed_key": "ruined_pelt", "skill_required": "survival", "base_dc": 10, "success_message":"...", "failure_message":"..."},
        "aggression_behavior": {
            "base_disposition": DISPOSITION_AGGRESSIVE,
            "attacks_on_sight": True,
            "faction_hostility_threshold": -100,
            "hostile_factions": ["OakhavenCivilian", "GreenSkinMarauders"], # Attacks Oakhaven and Goblins
            "threatening_delay_ticks": 0
        },
        "ambient_actions": ["sniffs suspiciously.", "scratches its scales."]
    }
}

# mud_project/game_data/default_monsters.py

DEFAULT_MONSTER_TEMPLATES = {
    "training_dummy": { # Renamed key for consistency
        "name": "Training Dummy",
        "hp": 30, "max_hp": 30, "defense": 0, "attack_damage": "0d0", "attack_delay": 999,
        "stats": { # Added basic stats
            "strength": 20, "stamina": 100, "dexterity": 1, "agility": 1, "constitution": 100,
            "charisma": 1, "intelligence": 1, "wisdom": 1, "logic": 1, "perception": 1,
            "aura": 1, "willpower": 1
        },
        "items": [], "skills": [], "spells": [],
        "spawn_config": {"respawn_time_seconds": 300, "spawn_chance": 0.75, "max_instances": 3},
        "faction": "Oakhaven Civilian", "faction_hits_on_kill": [], "religion": "Cerenos", "religion_hits_on_kill": [],
        "dialogue": ["Don't hit me too hard", "Boards might hit back.", "I'm just here for practice!", "Feeling stronger yet?"],
        "is_merchant": False, "shop_inventory": [], "is_backroom_merchant": False, "backroom_inventory": [], "can_repair": False,
        "buffs_on_spawn": [], "accuracy_bonus": 0, "agility_mod": -5,
        "loot_table_id": "training_dummy_loot", # Changed from direct loot
        "xp_value": 5,
        "description": "A sturdy straw-filled dummy, patched from numerous strikes. Its painted-on face has a surprisingly stoic expression.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.0},
        "group_behavior": {"calls_for_help": False, "group_id": "training_dummies", "assist_allies": False},
        "ambient_actions": ["stands silently, awaiting a beating.", "wobbles slightly if prodded.", "seems to stare blankly ahead."],
        "resistances": ["cold", "bludgeoning"], "vulnerabilities": ["fire", "slashing"], "inflicts_status": [],
        "dialogue_script": "oakhaven_intro", "quest_giver": False,
        "keywords": ["help", "combat", "dummy", "training", "practice"],
        "leaves_corpse": True, # Assumed true to drop loot
        "skinnable": False # Dummies usually aren't skinnable
    },
    "giant_rat": {
        "name": "Giant Rat",
        "hp": 25, "max_hp": 25, "defense": 2, "attack_damage": "1d4", "attack_delay": 2.0,
        "stats": {
            "strength": 30, "stamina": 40, "dexterity": 45, "agility": 50, "constitution": 35,
            "charisma": 10, "intelligence": 15, "wisdom": 25, "logic": 10, "perception": 45,
            "aura": 5, "willpower": 20
        },
        "items": [], "skills": ["bite"], "spells": [],
        "home_room_id": 16, "respawn_chance": 1.0, "respawn_time_seconds": 20, "is_unique": True, # Note: respawn time very short
        "faction": "Vermin", "faction_hits_on_kill": [], "religion": "None", "religion_hits_on_kill": [],
        "dialogue": ["*Squeak!*", "*Chitters angrily*"],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": [],
        "accuracy_bonus": 0, "agility_mod": 2,
        "loot_table_id": "giant_rat_common_loot", # Standardized name and using ID
        "xp_value": 10,
        "description": "An oversized rodent with beady red eyes and matted fur. It sniffs the air aggressively, baring sharp teeth.",
        "aggressive": True,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.20, "special_attacks": ["gnaw"]},
        "group_behavior": {"calls_for_help": True, "group_id": "rat_pack", "assist_allies": True},
        "ambient_actions": ["scurries around nervously.", "twitches its whiskers.", "lets out a soft squeak."],
        "resistances": ["poison_weak"], "vulnerabilities": ["fire_weak"], "inflicts_status": [{"status": "disease_minor", "chance": 0.1, "on_hit": True}],
        "dialogue_script": None, "quest_giver": False,
        "keywords": ["rat", "vermin", "rodent"],
        "leaves_corpse": True,
        "skinnable": True,
        "skinning": {
            "item_yield_success_key": "rat_pelt_clean",
            "item_yield_failed_key": "ruined_pelt",
            "skill_required": "survival", "base_dc": 5,
            "already_skinned_description": "The creature has already been skinned.",
            "success_message": "You skillfully skin the {monster_name}, obtaining a {item_name}.",
            "failure_message": "You try to skin the {monster_name} but make a mess of it."
        },
    },
    "kobold_warrior": {
        "name": "Kobold Warrior",
        "hp": 40, "max_hp": 40, "defense": 5, "attack_damage": "1d6", "attack_delay": 2.3,
        "stats": { # Added some plausible stats
            "strength": 45, "stamina": 50, "dexterity": 55, "agility": 50, "constitution": 45,
            "charisma": 20, "intelligence": 25, "wisdom": 30, "logic": 20, "perception": 50,
            "aura": 10, "willpower": 35
        },
        "items": ["kobold_spear", "tattered_leather_scraps"],
        "skills": ["spear_thrust", "dodge_small"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 240, "spawn_chance": 0.6, "max_instances": 3},
        "faction": "ScaleScourgeClan", "faction_hits_on_kill": [{"faction_id": "ScaleScourgeClan", "amount": -50}, {"faction_id": "GreenSkinMarauders", "amount": 5}, {"faction_id": "OakhavenCivilian", "amount": 5}],
        "religion": "Kurtulmak", "religion_hits_on_kill": [],
        "dialogue": ["Yip yip!", "For the clan!", "Shiny things for me!"],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": ["darkvision"],
        "accuracy_bonus": 1, "agility_mod": 1,
        "loot_table_id": "kobold_warrior_loot", # Changed from direct loot
        "xp_value": 25,
        "description": "A small, reptilian humanoid with dull scales and beady eyes. It clutches a crude spear and snarls, revealing tiny, sharp teeth.",
        "aggressive": True,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.15, "special_attacks": ["trap_sense", "coordinated_strike"]},
        "group_behavior": {"calls_for_help": True, "group_id": "kobold_warband", "assist_allies": True},
        "ambient_actions": ["sniffs the air suspiciously.", "scratches at its scales.", "mutters in a guttural tongue."],
        "resistances": ["poison_minor"], "vulnerabilities": ["bright_light_sensitivity"], "inflicts_status": [],
        "dialogue_script": None, "quest_giver": False,
        "keywords": ["kobold", "reptilian", "warrior"],
        "leaves_corpse": True,
        "skinnable": True, # Assuming kobolds can be skinned for scales or similar
        "skinning": {
            "item_yield_success_key": "kobold_scales_patch", # Needs to be added to items
            "item_yield_failed_key": "ruined_pelt",
            "skill_required": "survival", "base_dc": 10,
            "already_skinned_description": "The kobold has already been skinned.",
            "success_message": "You manage to gather some usable scales from the kobold.",
            "failure_message": "You attempt to skin the kobold but only make a mess of its hide."
        },
    },
    "goblin_archer": {
        "name": "Goblin Archer",
        "hp": 35, "max_hp": 35, "defense": 3, "attack_damage": "1d4+1", "attack_delay": 2.8,
        "stats": {
            "strength": 35, "stamina": 45, "dexterity": 65, "agility": 60, "constitution": 40,
            "charisma": 25, "intelligence": 30, "wisdom": 35, "logic": 25, "perception": 60,
            "aura": 20, "willpower": 30
        },
        "items": ["goblin_shiv", "crude_shortbow", "patchwork_jerkin"],
        "skills": ["shoot_arrow", "hide_in_shadows"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 260, "spawn_chance": 0.5, "max_instances": 2},
        "faction": "GreenSkinMarauders", "faction_hits_on_kill": [{"faction_id": "GreenSkinMarauders", "amount": -50}, {"faction_id": "ScaleScourgeClan", "amount": 5}, {"faction_id": "OakhavenCivilian", "amount": 5}],
        "religion": "Maglubiyet", "religion_hits_on_kill": [],
        "dialogue": ["Die, tallwalker!", "Me shoot you good!", "Goblins rule!"],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": ["low_light_vision"],
        "accuracy_bonus": 2, "agility_mod": 3,
        "loot_table_id": "goblin_archer_loot", # Changed from direct loot
        "xp_value": 20,
        "description": "A small, wiry humanoid with sickly green skin, pointed ears, and malevolent yellow eyes. It nocks an arrow to a crudely made bow, a sneer on its face.",
        "aggressive": True,
        "combat_behavior": {"preferred_range": "ranged", "flee_at_hp_pct": 0.25, "special_attacks": ["poisoned_arrow_weak", "quick_shot"]},
        "group_behavior": {"calls_for_help": True, "group_id": "goblin_skirmishers", "assist_allies": True},
        "ambient_actions": ["cackles quietly to itself.", "scans the area with shifty eyes.", "fiddles with its bowstring."],
        "resistances": [], "vulnerabilities": ["holy_damage_minor"], "inflicts_status": [{"status": "poison_weak", "chance": 0.1, "on_ranged_hit": True}],
        "dialogue_script": None, "quest_giver": False,
        "keywords": ["goblin", "archer", "greenskin"],
        "leaves_corpse": True,
        "skinnable": True, # Goblins might offer ears or some minor trophy
        "skinning": {
            "item_yield_success_key": "goblin_ear", # Already in items
            "item_yield_failed_key": "ruined_pelt", # Generic failure item
            "skill_required": "survival", "base_dc": 7,
            "already_skinned_description": "The goblin has already been skinned (or what's left of it).",
            "success_message": "You manage to take a grimy goblin ear as a trophy.",
            "failure_message": "You try to take something from the goblin, but it's too mangled."
        },
    },
}
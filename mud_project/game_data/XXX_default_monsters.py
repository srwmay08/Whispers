# mud_project/game_data/default_monsters.py

# --- MONSTERS ---
DEFAULT_MONSTER_TEMPLATES = {
    "training dummy": {
        "name": "Training Dummy",
        "hp": 30,
        "max_hp": 30,
        "defense": 0,
        "attack_damage": "0d0",
        "attack_delay": 999, # Effectively doesn't attack
        "stats": [],
        "items": [],
        "skills": [],
        "spells": [],
        "spawn_config": {
            "respawn_time_seconds": 300,
            "spawn_chance": 0.75,
            "max_instances": 3
        },
        "faction": "Oakhaven Civilian", # Neutral, for practice
        "faction_hits_on_kill": [], # No faction penalty for destroying it
        "religion": "Cerenos",
        "religion_hits_on_kill": [],
        "dialogue": ["Don't hit me too hard", "Boards might hit back.", "I'm just here for practice!", "Feeling stronger yet?"],
        "is_merchant": True, # Unlikely for a dummy, but kept from original
        "shop_inventory": ["rusty_sword"], # Unlikely, but kept
        "is_backroom_merchant": True, # Unlikely, but kept
        "backroom_inventory": [], # Unlikely, but kept
        "can_repair": True, # Unlikely, but kept
        "buffs_on_spawn": ["dummy_courage"] ,
        "accuracy_bonus": 0,
        "agility_mod": -5,
        "loot_table": [{"item_id": "straw_pile", "chance": 0.5, "quantity": [1,3]}, {"item_id": "splintered_wood", "chance": 0.3, "quantity": [1,2]}], # Example loot
        "xp_value": 5,
        "description": "A sturdy straw-filled dummy, patched from numerous strikes. Its painted-on face has a surprisingly stoic expression.",
        "aggressive": False,
        "combat_behavior": {
            "preferred_range": "melee",
            "flee_at_hp_pct": 0.0, # Doesn't flee
            "special_attacks": [] # Unlikely to have special attacks
        },
        "group_behavior": {
            "calls_for_help": False, # Doesn't call for help
            "group_id": "training_dummies",
            "assist_allies": False
        },
        "ambient_actions": [
            "stands silently, awaiting a beating.",
            "wobbles slightly if prodded.",
            "seems to stare blankly ahead."
        ],
        "resistances": ["cold", "bludgeoning"], # More resistant to being bashed
        "vulnerabilities": ["fire", "slashing"], # Straw is weak to fire and cuts
        "inflicts_status": [],
        "dialogue_script": "oakhaven_intro", # If it can talk...
        "quest_giver": False,
        "keywords": ["help", "combat", "dummy", "training", "practice"]
    },
    "giant_rat": {
        "name": "Giant Rat",
        "hp": 25,
        "max_hp": 25,
        "defense": 2,
        "attack_damage": "1d4",
        "attack_delay": 2.0,
        "stats": { # <<< Stats for Giant Rat
            "strength": 30, "stamina": 40, "dexterity": 45, "agility": 50, "constitution": 35,
            "charisma": 10, "intelligence": 15, "wisdom": 25, "logic": 10, "perception": 45,
            "aura": 5, "willpower": 20
        },
        "items": [], # Equipped items
        "skills": ["bite"],
        "spells": [],
        "home_room_id": 16,
        "respawn_chance": 1.0,
        "respawn_time_seconds": 10,
        "is_unique": True,
        "faction": "Vermin",
        "faction_hits_on_kill": [],
        "religion": "None",
        "religion_hits_on_kill": [],
        "dialogue": ["*Squeak!*", "*Chitters angrily*"],
        "is_merchant": False,
        "shop_inventory": [],
        "is_backroom_merchant": False,
        "backroom_inventory": [],
        "can_repair": False,
        "buffs_on_spawn": [],
        "accuracy_bonus": 0,
        "agility_mod": 2,
        "loot_table": [{"item_id": "rat_tail", "chance": 0.6, "quantity": [1,1]}, {"item_id": "ruined_pelt", "chance": 0.3, "quantity": [1,1]}],
        "xp_value": 10,
        "description": "An oversized rodent with beady red eyes and matted fur. It sniffs the air aggressively, baring sharp teeth.",
        "aggressive": True,
        "combat_behavior": {
            "preferred_range": "melee",
            "flee_at_hp_pct": 0.20,
            "special_attacks": ["gnaw"] # Example
        },
        "group_behavior": {
            "calls_for_help": True,
            "group_id": "rat_pack",
            "assist_allies": True
        },
        "ambient_actions": [
            "scurries around nervously.",
            "twitches its whiskers.",
            "lets out a soft squeak."
        ],
        "resistances": ["poison_weak"],
        "vulnerabilities": ["fire_weak"],
        "inflicts_status": [{"status": "disease_minor", "chance": 0.1, "on_hit": True}],
        "dialogue_script": None,
        "quest_giver": False,
        "keywords": ["rat", "vermin", "rodent"],
        "loot_table_id": "giant_rat_common",
        "skinnable": True,
        "skinning": {
            "item_yield_success_key": "rat_pelt_clean", # Key for the item yielded by skinning
            "item_yield_failed_key": "ruined_pelt",
            "skill_required": "survival", # Optional: skill to check
            "base_dc": 5,                 # Optional: base difficulty for skinning
            "already_skinned_description": "The creature has already been skinned.",
            "success_message": "You skillfully skin the {monster_name}, obtaining a {item_name}.",
            "failure_message": "You try to skin the {monster_name} but make a mess of it."
        },
    },
    "kobold_warrior": {
        "name": "Kobold Warrior",
        "hp": 40,
        "max_hp": 40,
        "defense": 5, # Scaly hide
        "attack_damage": "1d6", # From their spear
        "attack_delay": 2.3,
        
        "items": ["kobold_spear", "tattered_leather_scraps"], # Equipped
        "skills": ["spear_thrust", "dodge_small"],
        "spells": [],
        "spawn_config": {
            "respawn_time_seconds": 240,
            "spawn_chance": 0.6,
            "max_instances": 3
        },
        "faction": "ScaleScourgeClan", # Kobold Faction
        "faction_hits_on_kill": [{"faction_id": "GreenSkinMarauders", "amount": 5}, {"faction_id": "OakhavenCivilian", "amount": -2}], # Gain standing with Goblins, lose with Oakhaven
        "religion": "Kurtulmak", # Kobold deity
        "religion_hits_on_kill": [],
        "dialogue": ["Yip yip!", "For the clan!", "Shiny things for me!"],
        "is_merchant": False,
        "shop_inventory": [],
        "is_backroom_merchant": False,
        "backroom_inventory": [],
        "can_repair": False,
        "buffs_on_spawn": ["darkvision"],
        "accuracy_bonus": 1,
        "agility_mod": 1,
        "loot_table": [{"item_id": "kobold_spear", "chance": 0.2, "quantity": [1,1]}, {"item_id": "small_pouch_coins", "chance": 0.4, "quantity": [3,10]}, {"item_id": "shiny_rock", "chance": 0.1, "quantity": [1,1]}],
        "xp_value": 25,
        "description": "A small, reptilian humanoid with dull scales and beady eyes. It clutches a crude spear and snarls, revealing tiny, sharp teeth.",
        "aggressive": True,
        "combat_behavior": {
            "preferred_range": "melee",
            "flee_at_hp_pct": 0.15,
            "special_attacks": ["trap_sense", "coordinated_strike"] # More thematic
        },
        "group_behavior": {
            "calls_for_help": True,
            "group_id": "kobold_warband",
            "assist_allies": True
        },
        "ambient_actions": [
            "sniffs the air suspiciously.",
            "scratches at its scales.",
            "mutters in a guttural tongue."
        ],
        "resistances": ["poison_minor"],
        "vulnerabilities": ["bright_light_sensitivity"],
        "inflicts_status": [],
        "dialogue_script": None,
        "quest_giver": False,
        "keywords": ["kobold", "reptilian", "warrior"]
    },
    "goblin_archer": {
        "name": "Goblin Archer",
        "hp": 35,
        "max_hp": 35,
        "defense": 3,
        "attack_damage": "1d4+1", # Shortbow
        "attack_delay": 2.8,
        "stats": { # <<< ADDED/UPDATED STATS DICTIONARY
            "strength": 35,
            "stamina": 45,
            "dexterity": 65,     # Primary for archery
            "agility": 60,       # Primary for defense (as per current combat.py logic)
            "constitution": 40,
            "charisma": 25,
            "intelligence": 30,
            "wisdom": 35,
            "logic": 25,
            "perception": 60,    # Important for an archer
            "aura": 20,
            "willpower": 30
        },
        "items": ["goblin_shiv", "crude_shortbow", "patchwork_jerkin"], # Equipped
        
        "skills": ["shoot_arrow", "hide_in_shadows"],
        "spells": [],
        "spawn_config": {
            "respawn_time_seconds": 260,
            "spawn_chance": 0.5,
            "max_instances": 2
        },
        "faction": "GreenSkinMarauders", # Goblin Faction (Opposite to Kobold)
        "faction_hits_on_kill": [{"faction_id": "ScaleScourgeClan", "amount": 5}, {"faction_id": "OakhavenCivilian", "amount": -3}], # Gain standing with Kobolds, lose with Oakhaven
        "religion": "Maglubiyet", # Goblin deity
        "religion_hits_on_kill": [],
        "dialogue": ["Die, tallwalker!", "Me shoot you good!", "Goblins rule!"],
        "is_merchant": False,
        "shop_inventory": [],
        "is_backroom_merchant": False,
        "backroom_inventory": [],
        "can_repair": False,
        "buffs_on_spawn": ["low_light_vision"],
        "accuracy_bonus": 2, # Better for an archer
        "agility_mod": 3,
        "loot_table": [{"item_id": "goblin_shiv", "chance": 0.15, "quantity": [1,1]}, {"item_id": "arrow_bundle_crude", "chance": 0.5, "quantity": [3,8]}, {"item_id": "moldy_bread", "chance": 0.2, "quantity": [1,1]}],
        "xp_value": 20,
        "description": "A small, wiry humanoid with sickly green skin, pointed ears, and malevolent yellow eyes. It nocks an arrow to a crudely made bow, a sneer on its face.",
        "aggressive": True,
        "combat_behavior": {
            "preferred_range": "ranged",
            "flee_at_hp_pct": 0.25,
            "special_attacks": ["poisoned_arrow_weak", "quick_shot"]
        },
        "group_behavior": {
            "calls_for_help": True,
            "group_id": "goblin_skirmishers",
            "assist_allies": True
        },
        "ambient_actions": [
            "cackles quietly to itself.",
            "scans the area with shifty eyes.",
            "fiddles with its bowstring."
        ],
        "resistances": [],
        "vulnerabilities": ["holy_damage_minor"],
        "inflicts_status": [{"status": "poison_weak", "chance": 0.1, "on_ranged_hit": True}],
        "dialogue_script": None,
        "quest_giver": False,
        "keywords": ["goblin", "archer", "greenskin"]
    },
}
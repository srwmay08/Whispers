# mud_project/game_data/default_npcs.py

DEFAULT_NPCS_TEMPLATES = {
    "grom_blacksmith": {
        "name": "Grom the Blacksmith",
        "hp": 100, "max_hp": 100, "defense": 10, "attack_damage": "1d4+2", "attack_delay": 2.5,
        "stats": {
            "strength": 70, "stamina": 65, "dexterity": 40, "agility": 30, "constitution": 75,
            "charisma": 45, "intelligence": 50, "wisdom": 55, "logic": 60, "perception": 50,
            "aura": 20, "willpower": 60
        },
        "items": ["blacksmith_hammer", "leather_apron"],
        "skills": ["power_strike", "armor_crafting", "weapon_crafting"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 600, "spawn_chance": 1.0, "max_instances": 1},
        "faction": "Oakhaven Civilian", "religion": "Sevax",
        "dialogue": [
            "Need something reforged or ruined?", "The forge never sleeps, and neither do I.",
            "Got good steel, if you've got the coin.", "Don't touch that, it's hotter than your mother's temper!"
        ],
        "is_merchant": True,
        "shop_inventory": ["rusty_sword", "old_tunic", "iron_ingot", "hammer_handle", "leather_cap"],
        "is_backroom_merchant": True,
        "backroom_inventory": ["tarnished_blade", "reinforced_tunic", "steel_ingot_lowgrade"], # reinforced_tunic
        "can_repair": True, "buffs_on_spawn": ["heat_resistance", "strong_grip"],
        "accuracy_bonus": 1, "agility_mod": -1, "xp_value": 10,
        "description": "A burly dwarf with soot-covered arms and a perpetual scowl. Grom is more anvil than man, his muscles thick from years at the forge. He eyes you appraisingly.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.10, "special_attacks": ["hammer_smash", "disarming_blow"]},
        "group_behavior": {"calls_for_help": False, "group_id": "oakhaven_merchants", "assist_allies": False},
        "ambient_actions": [
            "hammers metal on an anvil.", "wipes sweat from his brow with a singed rag.",
            "murmurs about faulty alloys.", "quenches a glowing piece of metal with a loud hiss."
        ],
        "resistances": ["fire", "bludgeoning_minor"], "vulnerabilities": ["cold_minor"], "inflicts_status": [],
        "dialogue_script": "blacksmith_services", "quest_giver": True,
        "quests_available": ["retrieve_coal_shipment", "sharpen_town_guard_swords"],
        "keywords": ["blacksmith", "repair", "merchant", "shop", "grom", "forge", "weapons", "armor"],
        "leaves_corpse": True,
        "loot_table_id": "grom_blacksmith_loot", # Updated
    },
    "oakhaven_guard": {
        "name": "Oakhaven Guard",
        "hp": 70, "max_hp": 70, "defense": 8, "attack_damage": "1d6+1", "attack_delay": 2.2,
        "items": ["guard_spear", "oakhaven_shield", "boiled_leather_armor"],
        "skills": ["shield_bash", "vigilance"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 300, "spawn_chance": 1.0, "max_instances": 2},
        "faction": "Oakhaven Civilian", "religion": "Cerenos",
        "dialogue": ["Move along, citizen.", "Keep the peace, or you'll answer to me.", "Seen any trouble?", "The walls keep us safe."],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": ["guard_duty_resolve"],
        "accuracy_bonus": 1, "agility_mod": 0, "xp_value": 20,
        "description": "A stern-faced guard clad in boiled leather armor, bearing the oak leaf sigil of Oakhaven. They carry a spear and a shield, their eyes watchful.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.05, "special_attacks": ["call_for_backup", "arresting_strike"]},
        "group_behavior": {"calls_for_help": True, "group_id": "oakhaven_guard_patrol", "assist_allies": True},
        "ambient_actions": ["stands at attention.", "surveys the surroundings.", "shifts their grip on their spear."],
        "resistances": [], "vulnerabilities": [], "inflicts_status": [],
        "dialogue_script": "guard_interaction", "quest_giver": False,
        "keywords": ["guard", "oakhaven", "law", "patrol"],
        "leaves_corpse": True,
        "loot_table_id": "oakhaven_guard_loot", # Updated
    },
    "nervous_guard": {
        "name": "Nervous Guard",
        "hp": 60, "max_hp": 60, "defense": 7, "attack_damage": "1d6", "attack_delay": 2.4,
        "items": ["guard_spear_worn", "oakhaven_shield_dented", "ill_fitting_leather_armor"],
        "skills": ["fumble", "shaky_block"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 360, "spawn_chance": 1.0, "max_instances": 1},
        "faction": "Oakhaven Civilian", "religion": "Cerenos",
        "dialogue": [
            "H-hello there. All quiet, I hope?", "Did you hear that? Probably just the wind... right?",
            "I really hope my shift ends soon.", "Try not to cause any trouble, alright?"
        ],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": ["anxiety"],
        "accuracy_bonus": -1, "agility_mod": -1, "xp_value": 15,
        "description": "This young guard looks distinctly uncomfortable in their armor, constantly glancing towards the nearby forest. Their shield seems a bit too big for them.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "melee", "flee_at_hp_pct": 0.30, "special_attacks": ["panicked_shout"]},
        "group_behavior": {"calls_for_help": True, "group_id": "oakhaven_guard_patrol", "assist_allies": True},
        "ambient_actions": ["fidgets with their shield strap.", "jumps at sudden noises.", "wipes sweaty palms on their trousers."],
        "resistances": [], "vulnerabilities": ["fear_effects"], "inflicts_status": [],
        "dialogue_script": "nervous_guard_talk", "quest_giver": True,
        "quests_available": ["find_lost_gauntlet_forest_edge"],
        "keywords": ["guard", "nervous", "south gate", "scared"],
        "leaves_corpse": True,
        "loot_table_id": "nervous_guard_loot", # Updated
    },
    "master_elmsworth": {
        "name": "Master Elmsworth",
        "hp": 50, "max_hp": 50, "defense": 2, "attack_damage": "1d2", "attack_delay": 3.0,
        "items": ["spectacles", "ledger_book", "ink_stained_robes"],
        "skills": ["accounting", "appraisal", "calligraphy"], "spells": [],
        "spawn_config": {"respawn_time_seconds": 900, "spawn_chance": 1.0, "max_instances": 1},
        "faction": "Oakhaven Civilian", "religion": "Lex",
        "dialogue": [
            "Welcome to the Oakhaven Bank. How may I be of service?", "All transactions are final, you understand.",
            "Your funds are safe with us... mostly.", "Remember, a copper saved is a copper earned."
        ],
        "is_merchant": True,
        "shop_inventory": ["secure_lockbox_small", "deed_of_deposit"],
        "can_repair": False, "buffs_on_spawn": ["meticulous_mind"],
        "accuracy_bonus": 0, "agility_mod": -2, "xp_value": 5,
        "description": "Master Elmsworth is a thin, balding man with spectacles perched on his nose. He peers at you over a large ledger, an air of fussy precision about him.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "far", "flee_at_hp_pct": 0.80, "special_attacks": ["shout_for_guards"]},
        "group_behavior": {"calls_for_help": True, "group_id": "oakhaven_civilians_important", "assist_allies": False},
        "ambient_actions": [
            "adjusts his spectacles.", "scribbles in a large ledger with a quill.",
            "clears his throat officiously.", "counts coins meticulously."
        ],
        "resistances": [], "vulnerabilities": [], "inflicts_status": [],
        "dialogue_script": "bank_services", "quest_giver": True,
        "quests_available": ["recover_stolen_deposit_box", "deliver_financial_report"],
        "keywords": ["bank", "banker", "elmsworth", "money", "finance", "merchant"],
        "leaves_corpse": True,
        "loot_table_id": "master_elmsworth_loot", # Updated
    },
    "elder_rowan": {
        "name": "Elder Rowan",
        "hp": 60, "max_hp": 60, "defense": 3, "attack_damage": "1d3", "attack_delay": 2.8,
        "items": ["elder_staff_oak", "ceremonial_robes_oakhaven"],
        "skills": ["diplomacy", "local_history", "leadership_minor"], "spells": ["minor_soothe", "detect_intentions"],
        "spawn_config": {"respawn_time_seconds": 1800, "spawn_chance": 1.0, "max_instances": 1},
        "faction": "Oakhaven Leadership", "religion": "Cerenos",
        "dialogue": [
            "Welcome to Oakhaven, traveler. May your stay be peaceful.", "The strength of our town lies in its people.",
            "Wisdom is a heavy burden, but one I bear for this community.", "What guidance do you seek?"
        ],
        "is_merchant": False, "can_repair": False, "buffs_on_spawn": ["aura_of_calm", "respected_elder"],
        "accuracy_bonus": 0, "agility_mod": -1, "xp_value": 10,
        "description": "Elder Rowan is an elderly human with a kind face, etched with the lines of many years. They wear simple but dignified robes and lean on a polished oak staff. Their eyes hold a gentle wisdom.",
        "aggressive": False,
        "combat_behavior": {"preferred_range": "ranged", "flee_at_hp_pct": 0.50, "special_attacks": ["plea_for_peace", "town_summons"]},
        "group_behavior": {"calls_for_help": True, "group_id": "oakhaven_leadership", "assist_allies": False},
        "ambient_actions": [
            "gazes thoughtfully into the distance.", "offers a gentle smile to passersby.",
            "consults a worn leather-bound book.", "straightens a tapestry on the wall."
        ],
        "resistances": ["mental_influence_minor"], "vulnerabilities": [], "inflicts_status": [],
        "dialogue_script": "elder_council", "quest_giver": True,
        "quests_available": ["investigate_cistern_rumors", "mediate_merchant_dispute", "lost_historical_artifact"],
        "keywords": ["elder", "rowan", "moot hall", "leader", "council", "wisdom"],
        "leaves_corpse": True,
        "loot_table_id": "elder_rowan_loot", # Updated
    },
    "town_crier_timothy": {
        "_id": "town_crier_timothy", "name": "Timothy the Town Crier",
        "description": "Timothy is a young man with a surprisingly loud voice, clutching a scroll of news.",
        "home_room_id": 1, "respawn_chance": 1.0, "respawn_time_seconds": 30, "is_unique": True,

        "xp_on_kill": 100,
        "faction": "OakhavenCivilian", 
        "faction_hits_on_kill": [{"faction_id": "OakhavenCivilian", "amount": -50}, {"faction_id": "GreenSkinMarauders", "amount": 5}, {"faction_id": "ScaleScourgeClan", "amount": 5}],
        "hp": 1, "max_hp": 1,
        "stats": {
            "strength": 35, "stamina": 45, "dexterity": 5, "agility": 5, "constitution": 40,
            "charisma": 25, "intelligence": 30, "wisdom": 35, "logic": 25, "perception": 60,
            "aura": 20, "willpower": 30
        },
        "dialogue": ["Hear ye, hear ye!", "Fresh news from the capital!", "Mind the cobblestones, folks!"],
        "is_merchant": False, "can_repair": False, "aggressive": False, "xp_value": 0,
        "ambient_actions": [
            "clears his throat importantly.", "unfurls his scroll and squints at it.",
            "calls out, 'Extra! Extra! Read all about it!'", "paces back and forth, looking for an audience.",
            "adjusts his spectacles."
        ],
        "keywords": ["timothy", "crier", "news"],
        "items": [], # Items he *carries* in addition to equipped items.
                                          # His bell is now part of his equipment table.
        "equipment_table_id": "timothy_town_crier_gear", # NEW - Links to equipment_tables.py

        "leaves_corpse": True,
        "loot_table_id": "timothy_town_crier_loot", 
        "gold_min": 100,
        "gold_max": 1000
    },
    "wandering_peddler_arya": {
        "_id": "wandering_peddler_arya", "name": "Arya the Wandering Peddler",
        "description": "Arya carries a large, surprisingly neat backpack overflowing with various trinkets and supplies. Her eyes sparkle with a keen business sense.",
        "faction": "Independent Merchants", "hp": 40, "max_hp": 40, "defense": 3, "attack_damage": "1d3", "attack_delay": 2.8,
        "dialogue": ["Looking for something special, traveler?", "Best prices this side of the Whispering Peaks!", "Got just the thing for you..."],
        "is_merchant": True,
        "shop_inventory": ["healing_draught_minor", "torch", "rope_50ft"], # Standardized healing_draught_minor
        "can_repair": False, "aggressive": False, "xp_value": 0,
        "ambient_actions": [
            "hums a jaunty tune.", "adjusts the straps of her heavy backpack.",
            "polishes a small trinket from her wares.", "scans the crowd with a merchant's hopeful gaze.",
            "jingles a small pouch of coins thoughtfully."
        ],
        "keywords": ["arya", "peddler", "merchant", "shop", "wares"],
        "leaves_corpse": True,
        "loot_table_id": "arya_peddler_loot", # Updated
    },
}
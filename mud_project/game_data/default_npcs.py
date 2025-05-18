# mud_project/game_data/default_npcs.py
from config import DISPOSITION_PASSIVE, DISPOSITION_NEUTRAL, DISPOSITION_AGGRESSIVE, DISPOSITION_THREATENING, DISPOSITION_HOSTILE_GENERAL, NPC_DEFAULT_FACTION_HOSTILITY_THRESHOLD, THREATENING_DELAY_TICKS

DEFAULT_NPCS_TEMPLATES = {
    "grom_blacksmith": {
        "_id": "grom_blacksmith", 
        "name": "Grom the Blacksmith",
        "description": "A burly dwarf with soot-covered arms and a perpetual scowl...",
        "hp": 100, "max_hp": 100, "defense": 10, "attack_damage": "1d4+2", "attack_delay": 2.5,
        "stats": {"strength": 70, "stamina": 65, "dexterity": 40, "agility": 30, "constitution": 75, "charisma": 45, "intelligence": 50, "wisdom": 55, "logic": 60, "perception": 50, "aura": 20, "willpower": 60},
        "skills": { 
            "blunt_weapons": 70, # For his blacksmith hammer
            # "armor_crafting": 85, # Placeholder if you implement crafting skills
            # "weapon_crafting": 85, # Placeholder
            "physical_fitness": 60,
            "trading": 50 # He's a merchant
        }, 
        "spells": [],
        "spawn_config": {"respawn_time_seconds": 600, "spawn_chance": 1.0, "max_instances": 1},
        "faction_id": "OakhavenCivilian", 
        "faction_hits_on_kill": [ 
            {"faction_id": "OakhavenCivilian", "amount": -200},
            {"faction_id": "IndependentMerchants", "amount": -50}
        ],
        "religion": "Sevax",
        "dialogue": ["Need something reforged or ruined?", "The forge never sleeps..."],
        "is_merchant": True, "shop_inventory": ["rusty_sword", "old_tunic", "iron_ingot"], "can_repair": True, "xp_value": 10,
        "keywords": ["blacksmith", "repair", "merchant", "shop", "grom"],
        "leaves_corpse": True, "loot_table_id": "grom_blacksmith_loot",
        "equipment_table_id": None, 
        "items": ["blacksmith_hammer", "leather_apron"], 
        "aggression_behavior": {
            "base_disposition": DISPOSITION_NEUTRAL, 
            "attacks_on_sight": False,
            "faction_hostility_threshold": -1000, 
            "hostile_factions": ["GreenSkinMarauders"], 
            "threatening_delay_ticks": 0 
        },
        "ambient_actions": ["hammers metal on an anvil.", "wipes sweat from his brow."]
    },
    "oakhaven_guard": {
        "_id": "oakhaven_guard",
        "name": "Oakhaven Guard",
        "description": "A stern-faced guard clad in boiled leather armor...",
        "hp": 70, "max_hp": 70, "defense": 8, "attack_damage": "1d6+1", "attack_delay": 2.2,
        "stats": {"strength": 60, "stamina": 55, "dexterity": 50, "agility": 45, "constitution": 60, "charisma": 40, "intelligence": 40, "wisdom": 45, "logic": 40, "perception": 55, "aura": 20, "willpower": 50},
        "skills": { 
            "polearm_weapons": 60, # For their spear
            "shield_use": 65,
            "armor_use": 55, # Proficient with their armor
            "combat": 50, # General combat awareness
            "active_perception": 60 # For vigilance
        }, 
        "spells": [],
        "spawn_config": {"respawn_time_seconds": 180, "spawn_chance": 1.0, "max_instances": 2},
        "faction_id": "OakhavenCivilian",
        "faction_hits_on_kill": [
            {"faction_id": "OakhavenCivilian", "amount": -500}, 
            {"faction_id": "GreenSkinMarauders", "amount": 10}, 
            {"faction_id": "ScaleScourgeClan", "amount": 5}
        ],
        "religion": "Cerenos",
        "dialogue": ["Move along, citizen.", "Keep the peace..."],
        "is_merchant": False, "can_repair": False, "xp_value": 20,
        "keywords": ["guard", "oakhaven", "law", "patrol"],
        "leaves_corpse": True, "loot_table_id": "oakhaven_guard_loot",
        "equipment_table_id": "oakhaven_guard_standard_issue",
        "aggression_behavior": {
            "base_disposition": DISPOSITION_NEUTRAL,
            "attacks_on_sight": False,
            "faction_hostility_threshold": NPC_DEFAULT_FACTION_HOSTILITY_THRESHOLD,
            "hostile_factions": ["GreenSkinMarauders", "ScaleScourgeClan"],
            "threatening_delay_ticks": 0
        },
        "ambient_actions": ["stands at attention.", "surveys the surroundings."]
    },
    "town_crier_timothy": {
        "_id": "town_crier_timothy",
        "name": "Timothy the Town Crier",
        "description": "Timothy is a young man with a surprisingly loud voice...",
        "hp": 25, "max_hp": 25, "defense": 0, "attack_damage": "1d2", "attack_delay": 3.0, 
        "stats": {"strength": 35, "stamina": 45, "dexterity": 50, "agility": 55, "constitution": 40, "charisma": 60, "intelligence": 50, "wisdom": 45, "logic": 45, "perception": 60, "aura": 20, "willpower": 30},
        "skills": {
            "brawling": 25, # If he has to use his bell
            "observe": 50, # Good at noticing things for news
            "basic_literacy": 60 # Needs to read his scrolls
        },
        "faction_id": "OakhavenCivilian",
         "faction_hits_on_kill": [ 
            {"faction_id": "OakhavenCivilian", "amount": -100}, 
            {"faction_id": "IndependentMerchants", "amount": -10} 
        ],
        "xp_value": 5, 
        "dialogue": ["Hear ye, hear ye!", "Fresh news from the capital!"],
        "keywords": ["timothy", "crier", "news"],
        "leaves_corpse": True, "loot_table_id": "timothy_town_crier_loot",
        "equipment_table_id": "timothy_town_crier_gear",
        "spawn_config": {"respawn_time_seconds": 120, "spawn_chance": 1.0, "max_instances": 1, "is_unique": True},
        "aggression_behavior": {
            "base_disposition": DISPOSITION_PASSIVE, 
            "attacks_on_sight": False,
            "faction_hostility_threshold": -20000, 
            "hostile_factions": [],
            "threatening_delay_ticks": 0 
        },
        "ambient_actions": ["clears his throat importantly.", "unfurls his scroll."]
    }
    # TODO: Update nervous_guard, master_elmsworth, elder_rowan, wandering_peddler_arya
    # with "skills" as a dictionary (e.g., nervous_guard might have low polearm_weapons, low shield_use)
    # and ensure they have "faction_id", "faction_hits_on_kill",
    # and "aggression_behavior" defined.
}

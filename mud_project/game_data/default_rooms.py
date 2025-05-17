# game_data/default_rooms.py
# mud_project/game_data/default_rooms.py

# --- ROOMS ---
# Define rooms with their IDs as keys for easy lookup, but store with _id in DB
DEFAULT_ROOMS = {
    1: { "id": 1, "name": "Oakhaven Well - Town Center", "occupancy": 30,
        # --- ROOM INFO ---
        "tags": ["town", "oakhaven"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": True, "is_underground": False,
        "xp_modifier": 1.0,
        "is_node": True, "xp_absorbtion_modifier": 2.0,
        # --- ROOM DESCRIPTION & AMBIENT EVENTS ---
        "description": ( "The biting wind whips around you, carrying the scents of woodsmoke, baking bread, and damp earth from the nearby forest. You stand in the heart of Oakhaven, a bustling town square paved with worn, uneven cobblestones radiating outwards from the central well. The well itself is a sturdy structure of moss-speckled grey stone, its lip worn smooth by countless hands and buckets over generations. A thick, slightly frayed rope descends into the shadowed depths, secured to a weathered wooden beam overhead. Timber-framed buildings, some leaning companionably against their neighbours, crowd the edges of the square, their upper stories occasionally jutting out over the street. The sounds of town life echo here – the distant clang of a hammer, the murmur of unseen conversations, the creak of a sign swaying in the breeze, all blending into the constant hum of this frontier settlement nestled against the wild."
        ),
        "description_night": ( "The moon casts long, dancing shadows across the cobblestones of Oakhaven's town square. Most windows are dark, though a warm glow spills from the tavern to the north-east. The central well stands as a dark silhouette, its depths even more mysterious. The usual daytime bustle is replaced by a hushed quiet, broken only by the chirp of crickets, the distant hoot of an owl, and the occasional drunken song from the tavern. The air is cool and carries the scent of dying embers and night-blooming flowers from small window boxes."
        ),
        "description_storm": ( "Rain lashes down, turning the cobblestones of the town square into slick, reflective mirrors. The wind howls through the gaps between buildings, making signs creak and groan protestingly. The central well is a dark maw, its rope soaked and heavy. People hurry past, heads down, or huddle in doorways. The usual sounds of town are drowned out by the roar of the storm, a primal force temporarily reclaiming Oakhaven from its inhabitants. Flashes of lightning briefly illuminate the square in stark, ghostly detail."
        ),
        "ambient_sounds": [
            "a blacksmith's hammer rings in the distance",
            "a sign creaks as wind tugs at it",
            "the murmur of voices drifts from the tavern",
            "children laughing and playing nearby (daytime)",
            "a dog barking occasionally"
        ],
        "ambient_smells": ["woodsmoke", "baking bread", "damp earth", "livestock faintly"],
        "touch_textures": ["worn cobblestones", "rough stone of the well", "weathered wood"],
        "exits": {
            "north": 2, # Oakhaven North Gate
            "south": 3, # Oakhaven South Gate
            "east": 4,  # Market Street East
            "west": 5,  # Moot Hall Approach
        },
        #--- OBVIOUS ENEMIES, ITEMS & OBJECTS ---
        "items": ["rusty_sword"],
        "npcs": ["town_crier_timothy"],
        "monsters": [],
        "objects": {
            "well": {
                "name": "Old Stone Well",
                "description": "A mossy stone well with a frayed rope disappearing into shadow. It looks like you could possibly CLIMB ROPE DOWN. The water within is said to be fresh and cold.",
                "interactable": True,
                "actions": {"climb rope down": 9},
                "keywords": ["well", "rope", "stone well", "water", "old well"]
            },
            "notice_board": {
                "name": "Town Notice Board",
                "description": "A weathered wooden board covered in various parchments: town announcements, merchant advertisements, and a few crudely drawn 'wanted' posters.",
                "interactable": True,
                "actions": {"read notices": "display_active_quests_regional"},
                "keywords": ["notice", "board", "poster", "parchment", "notice board", "town notice board"] # MODIFIED
            }
        },
        #--- HIDDEN ENEMIES, ITEMS & OBJECTS ---
        "passive_perception_required": True,
        "active_perception_required": True,
        "hidden_items": [{"item_id": "lost_coin_pouch", "dc": 15, "description_found":"Tucked beside a loose cobblestone, you spot a small, forgotten coin pouch."}],
        "hidden_npcs": [],
        "hidden_monsters": [],
        "hidden_objects": [],
        "monster_spawns": [],
        "visited": False,
        "on_enter_script": "oakhaven_welcome_event",
        "on_linger_script": None,
        "on_exit_script": None,
        "trap_script": None
    },
    2: { "id": 2, "name": "Oakhaven North Gate","occupancy": 30,
        "tags": ["town", "gate", "defense", "oakhaven"],
        "searching": True,
        "hiding": True,
        "pvp": False,
        "shouting": True,
        "is_outdoor": True, 
        "is_underground": False, 
        "xp_modifier": 1.0,
        "is_node": False,
        "xp_absorbtion_modifier": 1.0,
        "description": "You stand before the massive North Gate of Oakhaven, a formidable structure designed to repel invaders and impress visitors. Twin towers of rough-hewn stone flank a colossal gate made from thick, iron-banded oak, scarred and weathered by time and conflict. Above, the menacing teeth of a heavy portcullis are visible, currently raised but ready to drop at a moment's notice. A lone Oakhaven Guard, clad in boiled leather armour bearing the town's oak leaf sigil, stands watch, their polearm held firmly, eyes scanning the northern approaches with practiced vigilance. The wind whistles through the crenellations high above, and you can feel the solid strength of the wall stretching away to the east and west, a bulwark against the dangers of the outside world.",
        "description_night": "Under the cloak of night, the North Gate looms even larger, its towers dark sentinels against the starry sky. Torches flicker on either side of the gate, casting dancing shadows that make the weathered wood seem to writhe. The portcullis is a shadowy maw overhead. The guard on duty is more alert, their silhouette sharply defined by the torchlight. The sounds of the wild seem closer beyond the walls.",
        "description_storm": "Rain hammers against the stone towers and the oak gate, streaming in rivulets down their surfaces. The wind howls around the battlements, threatening to tear the town sigil banner from its pole. The guard huddles deeper into their cloak, peering out into the tempest with narrowed eyes. The portcullis groans under the assault of the storm.",
        "ambient_sounds": ["wind whistling", "distant forest sounds", "guard's occasional cough"],
        "ambient_smells": ["pine", "damp stone", "oil from gate mechanism"],
        "touch_textures": ["cold stone", "rough wood of the gate"],
        "exits": {
            "south": 1,
        },
        "items": [],
        "npcs": ["oakhaven_guard"],
        "monsters": [],
        "objects": {
            "gate": {
                "name": "North Gate",
                "description": "A large, heavy-duty portcullis that serves as protection over the main gates. It looks well-maintained. The gate is currently closed and the guard here is standing watch over it.",
                "interactable": False,
                "actions": {},
                "keywords": ["gate", "door", "north gate"]
            },
            "gate_mechanism": {
                "name": "Gate Winch",
                "description": "A large, heavy-duty winch mechanism for raising and lowering the portcullis and opening the main gates. It looks well-maintained.",
                "interactable": False,
                "actions": {},
                "keywords": ["winch", "mechanism", "portcullis control"]
            }
        },
        "passive_perception_required": False,
        "active_perception_required": False,
        "hidden_items": [],
        "hidden_npcs": [],
        "hidden_monsters": [],
        "hidden_objects": [],
        "monster_spawns": [],
        "visited": False,
        "on_enter_script": None,
        "on_linger_script": None,
        "on_exit_script": "check_leaving_town_north_event",
        "trap_script": None
    },
    3: { "id": 3, "name": "Oakhaven South Gate", "occupancy": 30,
        "tags": ["town", "gate", "defense", "oakhaven"],
        "searching": True,
        "hiding": True,
        "pvp": False,
        "shouting": True,
        "is_outdoor": True, 
        "is_underground": False, 
        "xp_modifier": 1.0,
        "is_node": False,
        "xp_absorbtion_modifier": 1.0,
        "description": "The South Gate of Oakhaven feels somewhat less imposing than its northern counterpart, though still a sturdy barrier of timber and stone. It sees more traffic related to local farms and lumber operations, judging by the rutted track leading away from it and the faint smell of sawdust and livestock on the air. The gate itself shows signs of frequent use and repair, flanked by stone walls that continue the town's perimeter. A guard stands duty here, but their posture is less rigid than the northern sentry; they seem younger, perhaps greener, casting nervous glances towards the nearby forest and fidgeting with the strap of their shield. While secure, this gate feels more like a working entrance than a military stronghold.",
        "description_night": "Lamplight from the guard post casts a small pool of light around the South Gate. The nearby forest is a dark, rustling presence. The young guard seems even more on edge, jumping at every snap of a twig from the woods. The gate itself is securely barred.",
        "description_storm": "The South Gate is battered by wind and rain, the rutted track outside turning into a muddy quagmire. The guard has taken shelter in a small alcove, looking miserable. The scent of wet earth and pine from the forest is strong.",
        "ambient_sounds": ["wind through trees", "distant animal calls", "creaking of the gate"],
        "ambient_smells": ["sawdust", "livestock", "pine forest", "damp soil"],
        "touch_textures": ["weathered wood", "cold stone"],
        "exits": {
            "north": 1,
            "east": 8,
            "west": 10,
            "south": 21
        },
        "items": [],
        "npcs": ["nervous_guard"],
        "monsters": [],
        "objects": {
            "gate": { # Added basic gate object for South Gate
                "name": "South Gate",
                "description": "A sturdy wooden gate, currently closed. The guard here eyes it nervously.",
                "interactable": False,
                "actions": {},
                "keywords": ["gate", "door", "south gate"]
            }
        },
        "passive_perception_required": False,
        "active_perception_required": False,
        "hidden_items": [],
        "hidden_npcs": [],
        "hidden_monsters": [],
        "hidden_objects": [],
        "monster_spawns": [],
        "visited": False,
        "on_enter_script": None,
        "on_linger_script": None,
        "on_exit_script": "check_leaving_town_south_event",
        "trap_script": None
    },
    4: { "id": 4, "name": "Market Street East", "occupancy": 30,
        "tags": ["town", "market", "shops", "oakhaven"],
        "searching": True,
        "hiding": True,
        "pvp": False,
        "shouting": True,
        "is_outdoor": True, 
        "is_underground": False, 
        "xp_modifier": 1.0,
        "is_node": False,
        "xp_absorbtion_modifier": 1.0,
        "description": "This cobbled street runs along the eastern side of Oakhaven's central square, sloping gently upwards. Modest, timber-and-plaster buildings line the way, housing various shops and residences, their windows small and shuttered against the elements. Faint sounds drift from alleyways – muffled arguments, a dog's bark, the clatter of pans. Further down the street, two more significant structures stand out: one marked by a simple, painted sign of a crossed hammer and sword – the Oakhaven Armory, from which faint metallic clangs can be heard – and another, slightly more austere stone building bearing the sign of a balanced scale, proclaiming it the Town Bank. The street itself is relatively quiet compared to the town center, used more for access than for gathering.",
        "description_night": "Market Street East is dimly lit by a few scattered lanterns hanging from doorways. Most shops are closed, their shutters secured. Shadows pool in the alleyways, and the clanging from the Armory has ceased. Only the occasional cat darts across the cobbles.",
        "description_storm": "Rain gushes down Market Street East, forming small rivers along the edges of the cobbles. The signs for the Armory and Bank swing wildly in the wind. Most doors and windows are tightly shut against the storm's fury.",
        "ambient_sounds": ["distant hammering", "muffled conversations", "shop bell tinkling"],
        "ambient_smells": ["coal smoke", "metal", "old wood", "various merchant wares"],
        "touch_textures": ["cobblestones", "wooden walls of shops"],
        "exits": {
            "west": 1,
            "up": 14, # Assuming this leads to an upper floor or different area
            "alley_north": 22,
            "alley_south": 23,
            "enter armory": 11, # Direct entry to shops
            "enter bank": 12
        },
        "items": [],
        "npcs": ["wandering_peddler_arya"],
        "monsters": [],
        "objects": {
            "armory_sign": {
                "name": "Armory Sign",
                "description": "A wooden sign depicting a crossed hammer and sword. It's clearly the mark of a blacksmith or armorer. You could probably 'enter armory'.",
                "interactable": True,
                "actions": {"enter armory": 11},
                "keywords": ["sign", "armory", "hammer", "sword", "armory sign"]
            },
            "bank_sign": {
                "name": "Bank Sign",
                "description": "A sturdy sign showing a pair of balanced scales, symbolizing the Town Bank. You could likely 'enter bank'.",
                "interactable": True,
                "actions": {"enter bank": 12},
                "keywords": ["sign", "bank", "scales", "bank sign"]
            }
        },
        "passive_perception_required": False,
        "active_perception_required": False,
        "hidden_items": [],
        "hidden_npcs": [],
        "hidden_monsters": [],
        "hidden_objects": [],
        "monster_spawns": [],
        "visited": False,
        "on_enter_script": None,
        "on_linger_script": None,
        "on_exit_script": None,
        "trap_script": None
    },
    5: {  "id": 5, "name": "Moot Hall Approach", "occupancy": 30,
        "tags": ["town", "civic", "government", "oakhaven"],
        "searching": True,
        "hiding": True,
        "pvp": False,
        "shouting": True,
        "is_outdoor": True, 
        "is_underground": False, 
        "xp_modifier": 1.0,
        "is_node": False,
        "xp_absorbtion_modifier": 1.0,
        "description": "This area lies west of the town center, opening into a slightly wider plaza paved with smoother, more carefully laid flagstones than the central square. The atmosphere here feels more formal, quieter, and dedicated to civic matters. Surrounding buildings appear well-maintained, perhaps belonging to town officials or wealthier merchants. Dominating the western side of the plaza is the Oakhaven Moot Hall, a large, imposing building constructed from sturdy timber beams and stone foundations, its entrance marked by carved oak doors and flanked by tall, narrow windows. It stands as a symbol of Oakhaven's governance and community, radiating an air of quiet authority.",
        "description_night": "The Moot Hall Approach is quiet and stately under the moonlight. The flagstones gleam faintly, and the Moot Hall itself is a dark, imposing structure. A few windows in the surrounding residences show soft light. The air is still and respectful.",
        "description_storm": "Wind and rain sweep across the Moot Hall Approach, making the flagstones treacherous. The large oak doors of the Moot Hall seem to brace themselves against the storm. Any official business is likely on hold.",
        "ambient_sounds": ["quiet murmurs", "rustle of official documents", "footsteps on flagstones"],
        "ambient_smells": ["old parchment", "polished wood", "beeswax"],
        "touch_textures": ["smooth flagstones", "cold stone of buildings"],
        "exits": {
            "east": 1,
            "up": 15, # Assuming this leads somewhere like a balcony or upper walkway
            "enter moot hall": 13 # Direct entry
        },
        "items": [],
        "npcs": ["elderly_scholar_finneas"], # Add NPC if defined, e.g., a clerk or official
        "monsters": [],
        "objects": {
             "moot_hall_doors": {
                "name": "Moot Hall Doors",
                "description": "Large, imposing doors made of dark, carved oak. They are currently closed, but you could try to 'enter moot hall'.",
                "interactable": True,
                "actions": {"enter moot hall": 13},
                "keywords": ["door", "doors", "moot hall entrance", "moot hall doors"]
            }
        },
        "passive_perception_required": False,
        "active_perception_required": False,
        "hidden_items": [],
        "hidden_npcs": [],
        "hidden_monsters": [],
        "hidden_objects": [],
        "monster_spawns": [],
        "visited": False,
        "on_enter_script": None,
        "on_linger_script": None,
        "on_exit_script": None,
        "trap_script": None
    },
    # ... other rooms ...
    # Room 9 (Well Bottom)
    9: { "id": 9, "name": "Well Bottom - Cistern Antechamber", "occupancy": 30,
        "tags": ["underground", "cistern", "dark", "dungeon_entrance"],
        "searching": True, "hiding": True, "pvp": True, "shouting": True,
        "is_outdoor": False, "is_underground": True,
        "xp_modifier": 2.5, "is_node": True, "xp_absorbtion_modifier": 1.0,
        "description": "You land with a jarring thud on the cold, damp stone floor, the impact stealing your breath for a moment. The air is heavy, cool, and smells strongly of stagnant water, wet earth, and something vaguely unpleasant, perhaps mildew or decay. Utter darkness presses in, broken only by the faint light filtering down from the well opening high above, illuminating the dangling rope you descended. Water drips incessantly from unseen cracks in the roughly carved ceiling, echoing eerily in the confined space. The walls are slick with moisture and grime. To the east, a low, arched opening promises passage deeper into whatever lies beneath Oakhaven, its threshold shrouded in deeper shadow. A profound sense of isolation and hidden secrets permeates this forgotten place beneath the town's busy streets.",
        "description_night": "The darkness at the bottom of the well is absolute, save for the faintest glimmer from the distant well opening, which might now show starlight instead of daylight. The oppressive atmosphere feels even more pronounced.",
        "description_storm": "The sound of the storm above is a muted roar, but the dripping of water intensifies as more rainwater seeps through the earth and stone. The air becomes even colder and damper.",
        "ambient_sounds": ["dripping water", "faint echo of town above", "scuttling (faint)"],
        "ambient_smells": ["stagnant water", "wet earth", "mildew", "decay"],
        "touch_textures": ["cold damp stone", "slick grime", "frayed rope"],
        "exits": { "east": 16, "up": 1 },
        "items": [], "npcs": [], "monsters": ["goblin_archer"], # Ensure goblin_archer is defined
        "objects": {
            "rope": {
                "name": "Dangling Rope",
                "description": "The frayed rope you used to descend. It looks strong enough for another climb, but you wouldn't want to test it too many times. You could CLIMB ROPE UP.",
                "interactable": True, "actions": {"climb rope up": 1},
                "keywords": ["rope", "climb", "dangling rope"]
            },
            "debris_pile": {
                "name": "Pile of Debris",
                "description": "A small pile of rocks, mud, and what looks like rotted wood in a corner. It seems to have fallen from above or washed in.",
                "interactable": True, "actions": {"search debris": "find_item_or_nothing_debris_well_bottom"},
                "keywords": ["debris", "pile", "rocks", "mud", "debris pile"]
            }
        },
        "passive_perception_required": True, "active_perception_required": True,
        "hidden_items": [{"item_id": "cracked_pottery_shard", "dc": 12, "description_found": "Among the debris, you find a shard of old, cracked pottery."}],
        "monster_spawns": [
            {"template_key": "goblin_archer", "max_active": 1, "respawn_time_seconds": 100, "simulated_spawn_chance": 1.0, "_killed_at": [] }
        ],
        "visited": False, "on_enter_script": "check_fall_damage_script", "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 11 (Armory)
    11: { "id": 11, "name": "Oakhaven Armory", "occupancy": 4,
        "tags": ["town", "shop", "blacksmith", "armory", "oakhaven"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": False,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "Pushing open the heavy wooden door, you step into the Oakhaven Armory. The air inside is thick with the metallic tang of cooling steel, the acrid bite of coal smoke from the perpetually glowing forge, and the faint scent of sweat and oil. Racks of serviceable swords, axes, and spears line the stone walls, interspersed with pieces of leather and chainmail armour awaiting repair or purchase. The rhythmic clang of a hammer striking an anvil dominates the soundscape, punctuated by the hissing sizzle of hot metal quenched in water. In the corner, a stout, muscular figure – Grom the Blacksmith – hammers relentlessly on a piece of glowing iron, his brow furrowed in concentration. Near the back, a battered training dummy, stuffed with straw and covered in countless dents and cuts, stands ready for practice blows. It's a place of practical craft and martial necessity, humming with latent energy.",
        "description_night": "At night, the Armory is quieter. The forge might be banked, glowing softly, or Grom might still be working by lamplight, the clang of his hammer more pronounced in the stillness. Shadows deepen in the corners, making the racks of weapons look more menacing.",
        "description_storm": "During a storm, the sound of rain on the Armory roof is a dull roar, and the wind might whistle through cracks. The forge's heat is a welcome contrast to the cold outside. The clang of the hammer fights against the storm's noise.",
        "ambient_sounds": ["hammer on anvil", "hiss of quenched metal", "bellows whooshing", "grunts of effort from Grom"],
        "ambient_smells": ["burning coal", "hot metal", "quenching oil", "sweat"],
        "touch_textures": ["warm air", "rough stone walls", "smooth metal of tools"],
        "exits": { "out": 4 },
        "items": [], "npcs": ["grom_blacksmith"], "monsters": ["training_dummy"], # Make sure these keys match definitions
        "objects": {
            "forge": {
                "name": "Blacksmith's Forge",
                "description": "A large stone forge, currently radiating intense heat. Coals glow brightly within, and bellows stand ready to intensify the flames.",
                "interactable": True, "actions": {"use_forge": "player_smithing_interface"},
                "keywords": ["forge", "fire", "coals", "blacksmiths forge", "blacksmith forge"]
            },
            "anvil": {
                "name": "Anvil",
                "description": "A heavy steel anvil, its surface scarred and worn from countless hammer blows. It rings sharply when struck.",
                "interactable": False, "actions": {},
                "keywords": ["anvil", "steel block"]
            },
            "weapon_racks": {
                "name": "Weapon Racks",
                "description": "Several sturdy wooden racks displaying various weapons: swords, axes, maces, and spears. Most look functional, if not finely crafted.",
                "interactable": True, "actions": {"browse_weapons": "show_grom_weapon_inventory"},
                "keywords": ["weapons", "racks", "swords", "axes", "weapon racks"]
            }
        },
        "passive_perception_required": False, "active_perception_required": False,
        "hidden_items": [{"item_id": "chipped_whetstone", "dc": 13, "description_found":"Tucked under a bench, you find a chipped whetstone."}],
        "monster_spawns": [
            {"template_key": "training_dummy", "max_active": 1, "respawn_time_seconds": 60, "_killed_at": [] }
        ],
        "visited": False, "on_enter_script": None, "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 12 (Bank)
    12: { "id": 12, "name": "Oakhaven Bank", "occupancy": 3,
        "tags": ["town", "shop", "bank", "finance", "oakhaven"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": False,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "The Oakhaven Bank is a small but solidly built stone structure, projecting an image of security and stability amidst the more rustic timber buildings nearby. Inside, the air is cool and still, carrying the faint, dry scent of old parchment, ink, and the metallic tang of currency. A heavy oak counter, polished smooth by years of transactions, separates the public space from the banker's area. Small, barred windows let in minimal light, adding to the secure, slightly somber atmosphere. Behind the counter, Master Elmsworth, a man of precise habits and clad in respectable, if slightly ink-stained, clothes, likely presides over ledgers and coin sacks. A heavy, iron-reinforced door, presumably leading to a vault or strongroom, is visible in the back wall, underscoring the building's purpose.",
        "description_night": "At night, the Oakhaven Bank is securely locked. No light escapes from within. It stands as a silent, solid presence on Market Street. The only sound might be the faint rustle of a guard patrol passing by.",
        "description_storm": "The Bank's stone walls easily repel the storm. Inside, it would be a quiet refuge from the noise, though the barred windows would show the lashing rain. Master Elmsworth is likely ensuring all is secure.",
        "ambient_sounds": ["scratch of quill on parchment", "clink of coins (occasional)", " hushed tones"],
        "ambient_smells": ["old parchment", "ink", "coins", "polished wood"],
        "touch_textures": ["smooth polished wood", "cold metal bars", "cool air"],
        "exits": { "out": 4 },
        "items": [], "npcs": ["master_elmsworth"], "monsters": [],
        "objects": {
            "tellers_counter": {
                "name": "Teller's Counter",
                "description": "A sturdy oak counter, worn smooth with age. A small grille allows for transactions while maintaining security.",
                "interactable": True, "actions": {"speak_to_banker": "initiate_dialogue_elmsworth"},
                "keywords": ["counter", "desk", "teller", "tellers counter"]
            },
            "vault_door": {
                "name": "Vault Door",
                "description": "A very thick, iron-reinforced door set into the back wall. It has multiple complex locks and looks incredibly secure.",
                "interactable": False, "actions": {},
                "keywords": ["vault", "door", "safe", "strongroom", "vault door"]
            }
        },
        "passive_perception_required": False, "active_perception_required": False,
        "hidden_items": [], "monster_spawns": [],
        "visited": False, "on_enter_script": None, "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 13 (Moot Hall)
    13: { "id": 13, "name": "Oakhaven Moot Hall", "occupancy": 7,
        "tags": ["town", "civic", "government", "moot hall", "oakhaven"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": False,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "The Moot Hall is a spacious, high-ceilinged chamber that serves as the center of Oakhaven's governance and important community gatherings. Massive, dark oak beams support the roof overhead, and the air smells faintly of polished wood, old beeswax, and dust motes dancing in the light filtering through tall, arched windows. A long, heavy table dominates the center of the room, surrounded by sturdy wooden chairs, where the town elders likely convene. The stone walls might be adorned with faded tapestries depicting scenes from Oakhaven's history or perhaps shields bearing the crests of founding families. The atmosphere is one of quiet dignity and deliberation, presided over by the venerable Elder Rowan, whose wisdom guides the town.",
        "description_night": "By night, the Moot Hall is often dark and silent, unless a council meeting runs late, in which case muted light might spill from its tall windows. The grand table is a shadowy expanse in the moonlight filtering through.",
        "description_storm": "The sounds of the storm are muffled within the thick walls of the Moot Hall. Rain streaks down the arched windows. It feels like a secure, important place, sheltered from the elements.",
        "ambient_sounds": ["solemn quiet", "rustle of robes", "creak of old wood", "faint echoes"],
        "ambient_smells": ["polished wood", "old beeswax", "dust", "old parchment"],
        "touch_textures": ["smooth polished wood", "cool stone walls", "velvet cushions on chairs"],
        "exits": { "out": 5 },
        "items": [], "npcs": ["elder_rowan"], "monsters": [],
        "objects": {
            "council_table": {
                "name": "Council Table",
                "description": "A very long and heavy table made of dark, polished oak. Many important decisions for Oakhaven have likely been made here.",
                "interactable": False, "actions": {},
                "keywords": ["table", "council table"]
            },
            "historical_tapestries": {
                "name": "Historical Tapestries",
                "description": "Several large, faded tapestries hang on the walls, depicting scenes of Oakhaven's founding, battles, and notable events. They are quite old.",
                "interactable": True, "actions": {"examine_tapestries": "learn_local_lore_oakhaven"},
                "keywords": ["tapestry", "tapestries", "wall hangings", "historical tapestries"]
            }
        },
        "passive_perception_required": False, "active_perception_required": False,
        "hidden_items": [{"item_id": "lost_page_town_charter", "dc": 16, "description_found":"Slipped behind a tapestry, you discover a missing page from what appears to be an official document."}],
        "monster_spawns": [],
        "visited": False, "on_enter_script": "moot_hall_ambience_script", "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 16 (Decaying Passage)
    16: { "id": 16, "name": "Decaying Passage", "occupancy": 2,
        "tags": ["underground", "sewer", "passage", "decaying", "dangerous"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": True,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "You wade through knee-deep, murky water that chills you to the bone and obscures the treacherous footing below. The passage walls are constructed of crumbling brick and stone, weeping moisture and coated in patches of slimy, green algae. The air is stagnant and foul, thick with the stench of decay and the unmistakable musk of vermin. Every splash of your movement echoes unnervingly down the narrow corridor, occasionally answered by faint scuttling sounds from the oppressive darkness ahead or behind. Loose stones and debris litter the submerged floor, making progress slow and cautious. This forgotten waterway clearly hasn't seen proper maintenance in decades, perhaps centuries, slowly surrendering to the damp and the creatures that thrive in it.",
        "description_night": "Night makes no difference in this already lightless passage. The oppressive darkness and foul smells remain constant.",
        "description_storm": "The storm above might cause the water level to rise slightly, making wading more difficult. The dripping from the ceiling could increase to a steady trickle.",
        "ambient_sounds": ["splashing water", "dripping", "scuttling sounds", "distant groans of shifting earth"],
        "ambient_smells": ["decay", "stagnant water", "vermin musk", "mold"],
        "touch_textures": ["murky cold water", "slimy walls", "loose stones underfoot"],
        "exits": { "west": 9, "north": 17, "south": 18 },
        "items": [], "npcs": [], "monsters": ["giant_rat", "giant_rat"],
        "objects": {
            "slimy_algae": {
                "name": "Slimy Algae",
                "description": "Patches of disgusting green and black algae cling to the walls, slick to the touch.",
                "interactable": False, "actions": {},
                "keywords": ["algae", "slime", "moss", "slimy algae"]
            }
        },
        "passive_perception_required": True, "active_perception_required": True,
        "hidden_items": [{"item_id": "waterlogged_coin", "dc": 14, "description_found":"Your foot nudges something small and metallic in the murky water - an old, waterlogged coin."}],
        "hidden_monsters": [{"monster_id": "slimy_creeper", "dc": 15, "description_found": "A patch of algae suddenly detaches from the wall, revealing a lurking Slimy Creeper!"}],
        "monster_spawns": [
            {"template_key": "giant_rat", "max_active": 3, "respawn_time_seconds": 120, "_killed_at": []},
            {"template_key": "sewer_leech_swarm", "max_active": 1, "respawn_time_seconds": 300, "_killed_at": []}
        ],
        "visited": False, "on_enter_script": None, "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 17 (Flooded Storeroom)
    17: { "id": 17, "name": "Flooded Storeroom", "occupancy": 2,
        "tags": ["underground", "cistern", "storeroom", "flooded", "dangerous"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": True,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "This small chamber is mostly submerged in the same cold, murky water as the passage, reaching waist-height in the center. Rotting wooden crates and the warped staves of broken barrels bob listlessly on the surface or rest waterlogged on the bottom. The stone walls are slick with damp and decay, and the air hangs heavy and still, disturbed only by the constant drip... drip... drip from the low ceiling. Shelves carved into the walls are either empty or hold only rusted, unrecognizable shapes. Partially hidden on a higher shelf, just above the waterline and catching a faint glint of light, lies a small, tarnished metal object – perhaps a locket, strangely preserved amidst the ruin. The silence here feels heavy, a repository of forgotten goods and perhaps forgotten stories.",
        "description_night": "Darkness is total. The only change might be the temperature of the water feeling even colder.",
        "description_storm": "The dripping might become more pronounced, and the water level could rise, making it harder to reach the shelf.",
        "ambient_sounds": ["dripping water", "water lapping gently", "faint gurgling"],
        "ambient_smells": ["stagnant water", "rot", "rust", "mildew"],
        "touch_textures": ["cold water", "slimy stone", "rotting wood"],
        "exits": { "south": 16 },
        "items": ["tarnished_locket"], "npcs": [], "monsters": ["kobold_warrior"],
        "objects": {
            "rotting_crates": {
                "name": "Rotting Crates",
                "description": "Several wooden crates, mostly fallen apart and waterlogged. Their original contents are long gone or ruined.",
                "interactable": True, "actions": {"search_crates": "find_ruined_junk_or_nothing"},
                "keywords": ["crates", "boxes", "wood", "rotting crates"]
            },
            "high_shelf": {
                "name": "High Shelf",
                "description": "A stone shelf carved into the wall, just above the current waterline. Something small and metallic glints there.",
                "interactable": True, "actions": {"reach_for_locket": "attempt_get_tarnished_locket"},
                "keywords": ["shelf", "ledge", "high shelf"]
            }
        },
        "passive_perception_required": True, "active_perception_required": True,
        "hidden_items": [{"item_id": "waterproof_pouch_rotted", "dc": 15, "description_found":"Wedged behind a loose stone in a shelf, you find a rotted waterproof pouch. It contains nothing of value."}],
        "monster_spawns": [
            {"template_key": "kobold_warrior", "max_active": 1, "respawn_time_seconds": 240, "_killed_at": []},
            {"template_key": "kobold_skirmisher_lesser", "max_active": 2, "respawn_time_seconds": 180, "_killed_at": []}
        ],
        "visited": False, "on_enter_script": None, "on_linger_script": None, "on_exit_script": None, "trap_script": None
    },
    # Room 18 (Trapped Corridor)
    18: { "id": 18, "name": "Trapped Corridor", "occupancy": 1,
        "tags": ["underground", "corridor", "trapped", "narrow", "dangerous"],
        "searching": True, "hiding": True, "pvp": False, "shouting": True,
        "is_outdoor": False, "is_underground": True,
        "xp_modifier": 1.0, "is_node": False, "xp_absorbtion_modifier": 1.0,
        "description": "The passage narrows here, forcing you to turn sideways to squeeze through. The walls press close, rough-hewn and claustrophobic, covered in dust and thick cobwebs that cling to you as you pass. The air is stale and undisturbed, suggesting few have trod this way recently. Underfoot, the ground is uneven, and a section of the floor ahead appears disturbed, composed of looser stones than the surrounding flagstones. It looks suspiciously unstable, hinting that a careless step might trigger an unwelcome surprise from the shadows. The tension is palpable; the confined space and the suspicious flooring create an atmosphere thick with potential danger, urging extreme caution.",
        "description_night": "No change from daytime in this lightless corridor.",
        "description_storm": "The storm is inaudible here, deep underground. The stale air remains.",
        "ambient_sounds": ["absolute quiet", "your own breathing", "faint rustle of cobwebs"],
        "ambient_smells": ["stale air", "dust", "faint metallic tang (trap mechanism?)"],
        "touch_textures": ["rough stone walls", "sticky cobwebs", "uneven floor"],
        "exits": { "north": 16 },
        "items": [], "npcs": [], "monsters": ["goblin_archer"],
        "objects": {
            "loose_stones": {
                "name": "Loose Stones",
                "description": "A section of the floor paved with loose, unstable-looking stones. It's likely a pressure plate for a trap.",
                "interactable": True, "actions": {"disarm trap": "attempt_disarm_dart_trap_18", "step_carefully": "attempt_avoid_trap_18"},
                "keywords": ["stones", "loose stones", "floor", "plate", "trap"]
            },
            "cobwebs": {
                "name": "Thick Cobwebs",
                "description": "Thick, dusty cobwebs hang like curtains, obscuring vision slightly.",
                "interactable": True, "actions": {"clear_cobwebs": "action_clear_cobwebs"},
                "keywords": ["cobwebs", "webs", "spiderwebs", "thick cobwebs"]
            }
        },
        "passive_perception_required": True, "active_perception_required": True,
        "hidden_items": [{"item_id": "bent_dart", "dc": 10, "description_found":"Lodged in a crack near the floor, you find a bent dart, evidence of the trap."}],
        "monster_spawns": [
            {"template_key": "goblin_archer", "max_active": 1, "respawn_time_seconds": 260, "_killed_at": []},
            {"template_key": "goblin_sneak_lesser", "max_active": 1, "respawn_time_seconds": 200, "_killed_at": []}
        ],
        "visited": False, "on_enter_script": "check_trigger_trap_18_script", "on_linger_script": None, "on_exit_script": None, "trap_script": "dart_trap_18_logic"
    }
}
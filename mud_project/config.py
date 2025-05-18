# --- FILE DIRECTORY ---
# mud_project/
#├── main.py                   # Main application script (Flask, SocketIO setup, game loop start)
#├── config.py                 # Game constants, database configuration
#|
#├── game_data/                # Static game data, potentially in JSON, YAML, or Python modules
#│   ├── items.py              # Item definitions (or .json, .yaml)
#│   ├── monsters.py           # Monster template definitions
#│   ├── npcs.py               # NPC definitions
#│   ├── rooms.py              # Room definitions
#│   └── skills_config.py      # Skill lists, initial skill values
#│   └── player_config.py      # Player pronoun config, level thresholds, stat info
#|
#├── game_logic/               # Core game mechanics and systems
#│   ├── __init__.py
#│   ├── character_creation.py # STARTED - Character Creation Logic
#│   ├── movement.py           # NOT YET IMPLEMENTED - Movement logic
#│   ├── combat.py             # Combat calculations, attack logic
#│   ├── skills.py             # Skill system (training, usage - if complex enough)
#│   ├── magic.py              # Magic system (if/when implemented)
#│   ├── enchanting.py         # Enchanting system (if/when implemented)
#│   ├── forging.py            # Forging system (if/when implemented)
#│   ├── player_actions.py     # Handlers for player commands like take, drop, equip, etc.
#│   └── npc_behavior.py       # NPC interaction logic, dialogue, shop
#│   └── monster_behavior.py   # Monster AI, roaming, respawning
#|
#├── database/                 # Database interaction logic
#│   ├── __init__.py
#│   ├── connection.py         # MongoDB connection setup (connect_to_mongo, get_db)
#│   ├── data_loader.py        # Loading game data from DB, initializing DB with defaults
#│   └── player_handler.py     # Saving/loading player data
#|
#├── classes/                 # Game entity classes
#│   ├── __init__.py
#│   ├── player.py             # Player class definition
#│   ├── monster.py            # Monster class definition
#│   ├── npc_class.py          # (Optional) NPC class if they become more complex than dicts
#│   └── item_class.py         # (Optional) Item class if they become more complex
#|
#├── utils/                    # Utility functions
#│   ├── __init__.py
#│   ├── dice.py               # roll_dice function
#│   └── text_utils.py         # (Optional) For text formatting, pronoun handling etc.
#|
#└── templates/                # Flask HTML templates
#    └── index.html

# mud_project/config.py
import math

# --- General MUD Configuration ---
MUD_NAME = "Whispers in the Dark"
WELCOME_MESSAGE = "From the swirling mists of unbeing, a consciousness stirs..."

# --- Server Configuration ---
HOST = '0.0.0.0'
PORT = 8024
SECRET_KEY = 'your_very_secret_key_here!' # IMPORTANT: Change this for production
SOCKETIO_ASYNC_MODE = None # Let SocketIO choose, or specify 'threading', 'eventlet', 'gevent'

# --- DATABASE CONFIGURATION ---
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "whispers_game" # Use a new DB name for the refactored structure
PLAYERS_COLLECTION = "players"
ITEMS_COLLECTION = "items"
MONSTERS_COLLECTION = "monsters"
NPCS_COLLECTION = "npcs"
ROOMS_COLLECTION = "rooms"
LOOT_TABLES_COLLECTION = "loot_tables"
RACES_COLLECTION = "races"
EQUIPMENT_TABLES_COLLECTION = "equipment_tables"

# --- DEBUGGING GRANULARITY ---
DEBUG_MODE = True
DEBUG_RESPAWN_VERBOSE = False
DEBUG_GAME_TICK_RESPAWN_PHASE = False
SEND_CLIENT_TICK_MARKERS = True
DEBUG_COMBAT_ROLLS = True
DEBUG_AI_AGGRO = True # New flag for AI aggression logging


# --- GAME TICK INTERVALS
TICK_INTERVAL_SECONDS = 6  # Seconds per game tick
MONSTER_ROAM_TICK_INTERVAL = 5 # How many game ticks before attempting monster roams
MONSTER_RESPAWN_TICK_INTERVAL = 1 # How many game ticks before checking respawns
AI_AGGRESSION_CHECK_INTERVAL_TICKS = 1 # How many game ticks before AI checks for new targets

# --- CREATION & RESPAWN ---
MIN_CHAR_NAME_LENGTH = 3
MAX_CHAR_NAME_LENGTH = 32
DEFAULT_START_ROOM_ID = 1
PLAYER_DEATH_ROOM_ID = 1 # Room player goes to on PvP death (or PvE if implemented)
PLAYER_RESPAWN_ROOM_ID = 1 # For general respawn/relog if no other location
PVP_ENABLED_ROOM_TAG = True # If a room has "pvp": true, PvP is allowed
MAX_INVENTORY_SIZE = 20
DEFAULT_STAT_VALUE = 10

# --- ENVIRONMENT SIMULATION (for testing, can be longer for production) ---
TIME_CHANGE_INTERVAL_TICKS = 20      # How many game ticks before time of day might change (e.g., 20 ticks * 6s/tick = 2 minutes)
WEATHER_CHANGE_INTERVAL_TICKS = 15   # How many game ticks before weather might change (e.g., 15 ticks * 6s/tick = 1.5 minutes) - Made more frequent for testing

# --- WEATHER ---
WEATHER_SEVERITY_ORDER = ["clear", "light clouds", "overcast", "light rain", "rain", "heavy rain", "storm"]

WEATHER_STAY_CLEAR_BASE_CHANCE = 0.65       # Base chance to remain clear
WEATHER_WORSEN_FROM_CLEAR_START_CHANCE = 0.10 # Initial chance to worsen from clear
WEATHER_WORSEN_ESCALATION = 0.03            # Increase worsen chance by this amount each time it stays clear
WEATHER_MAX_WORSEN_FROM_CLEAR_CHANCE = 0.75 # Cap for worsening chance from clear

WEATHER_IMPROVE_BASE_CHANCE = 0.50          # Base chance for bad weather to improve by one step
WEATHER_STAY_SAME_BAD_CHANCE = 0.40         # Base chance for bad weather to stay the same

# --- TIME OF DAY CONFIGURATION ---
SECONDS_PER_GAME_MINUTE = 10  # Real-time seconds for one game minute
DAY_NIGHT_CYCLE_SECONDS = 10 * SECONDS_PER_GAME_MINUTE  # 10 minutes total cycle
DAY_DURATION_SECONDS = 6 * SECONDS_PER_GAME_MINUTE     # 6 minutes of daylight
NIGHT_DURATION_SECONDS = DAY_NIGHT_CYCLE_SECONDS - DAY_DURATION_SECONDS # 4 minutes of night
INITIAL_GAME_DAY_PHASE = "DAWN"

# Define transition points within the DAY_NIGHT_CYCLE_SECONDS (0 to DAY_NIGHT_CYCLE_SECONDS - 1)
# Format: (time_threshold, phase_name, transition_message_to_broadcast)
TIME_OF_DAY_PHASES = [
    (0, "DAWN", "The first rays of dawn paint the eastern sky."),
    (int(DAY_DURATION_SECONDS * 0.15), "MORNING", "The sun climbs higher, bathing the land in morning light."), # Approx 15% into day
    (int(DAY_DURATION_SECONDS * 0.50), "MIDDAY", "The sun is high in the sky, casting short shadows."),    # Midpoint of day
    (int(DAY_DURATION_SECONDS * 0.85), "AFTERNOON", "The sun begins its slow descent towards the western horizon."), # Approx 85% into day
    (DAY_DURATION_SECONDS, "DUSK", "The sun dips below the horizon, painting the sky in fiery hues. Night approaches."), # Start of night
    (DAY_DURATION_SECONDS + int(NIGHT_DURATION_SECONDS * 0.25), "EVENING", "Twilight fades as stars begin to pepper the darkening sky."), # 25% into night
    (DAY_DURATION_SECONDS + int(NIGHT_DURATION_SECONDS * 0.50), "MIDNIGHT", "The moon hangs high, casting an ethereal glow, or darkness reigns under a new moon."), # Midpoint of night
    (DAY_DURATION_SECONDS + int(NIGHT_DURATION_SECONDS * 0.75), "LATE_NIGHT", "The night wears on, and a pre-dawn chill settles upon the land.") # 75% into night
]

# --- EXPERIENCE ---
XP_ABSORPTION_TICKS = max(1, round(30 / TICK_INTERVAL_SECONDS)) # Approx 30 real seconds
XP_LEVEL_THRESHOLDS = {2: 100, 3: 300, 4: 600, 5: 1000}
MIND_STATUS_THRESHOLDS = [
    {"threshold": 1.01, "phrase": "Completely saturated"}, {"threshold": 0.90, "phrase": "Must rest"},
    {"threshold": 0.75, "phrase": "Numbed"}, {"threshold": 0.62, "phrase": "Becoming numbed"},
    {"threshold": 0.50, "phrase": "Muddled"}, {"threshold": 0.25, "phrase": "Clear"},
    {"threshold": 0.00, "phrase": "Fresh and clear"}, {"threshold": -0.01, "phrase": "Clear as a bell"}
]
MIN_XP_ABSORBED_PER_EVENT = 1
BASE_FIELD_XP_POOL_CAPACITY = 1000
FIELD_XP_POOL_LOGIC_BONUS_MULTIPLIER = 50
XP_ABSORB_LOGIC_BONUS_DIVISOR_NODE_TOWN = 5
XP_ABSORB_LOGIC_BONUS_DIVISOR_OTHER = 7
XP_ABSORB_POOL_SIZE_BONUS_PER_XP_AMOUNT = 200
XP_ABSORB_POOL_SIZE_BONUS_POINT = 1
XP_ABSORB_POOL_SIZE_BONUS_MAX_POINTS = 10
XP_ABSORB_SUPER_NODE_BONUS = 2
XP_ABSORB_GROUP_BONUS = 1
XP_ABSORB_BASE_RATE_ON_NODE = 25
XP_ABSORB_BASE_RATE_IN_TOWN_OFF_NODE = 22
XP_ABSORB_BASE_RATE_OTHER_AREAS = 19


# --- ROUND TIME DEFAULTS ---
ROUNDTIME_DEFAULTS = {"roundtime_look": 0.2, "roundtime_move": 0.5, "roundtime_attack": 3.0, "roundtime_action_short": 1.0}
STAT_FOR_SEARCH_TIME_REDUCTION = "perception" # The name of the stat in player.stats

# --- Loot Config ---
NPC_DROP_CARRIED_CHANCE = 1.0  # 0.0 to 1.0
NPC_DROP_EQUIPPED_CHANCE = 0.8 # 0.0 to 1.0 (e.g., 80% chance for each equipped item to drop)
CORPSE_DECAY_TIME_SECONDS = 300 # (You likely have this)
CORPSE_DECAY_TICK_INTERVAL = 10 # How many game ticks before checking corpse decay (adjust as needed)

# --- COMBAT ---
COMBAT_ADVANTAGE_FACTOR = 40
COMBAT_HIT_THRESHOLD = 0 # Gemstone used 100, but your formula adds AvD and d100 to (AS-DS)
COMBAT_DAMAGE_MODIFIER_DIVISOR = 10
DEFAULT_UNARMORED_TYPE = "unarmored"
ARMOR_TYPES = [DEFAULT_UNARMORED_TYPE, "cloth", "leather", "scale", "chain", "plate"]
BAREHANDED_FLAT_DAMAGE = 1 # Flat damage for barehanded attacks

# --- FACTION & AI ---
MAX_FACTION_STANDING = 25000
MIN_FACTION_STANDING = -25000
NPC_DEFAULT_FACTION_HOSTILITY_THRESHOLD = -750 # Player CONSIDER below this with NPC's FACTION = hostile
# Disposition levels for AI behavior
DISPOSITION_PASSIVE = "passive"
DISPOSITION_NEUTRAL = "neutral"
DISPOSITION_THREATENING = "threatening"
DISPOSITION_AGGRESSIVE = "aggressive"
DISPOSITION_HOSTILE_GENERAL = "hostile" # General hostility, may attack on sight or with triggers
THREATENING_DELAY_TICKS = 3 # Number of game ticks a "threatening" entity waits before attacking

FACTION_DISPLAY_NAMES = {
    "OakhavenCivilian": "Oakhaven Civilians",
    "GreenSkinMarauders": "Greenskin Marauders",
    "ScaleScourgeClan": "Scalescourge Clan",
    "Vermin": "Vermin",
    "IndependentMerchants": "Independent Merchants",
    "OakhavenLeadership": "Oakhaven Leadership",
    # Add other faction IDs and their display names
}



# --- STATS ---
STAT_CATEGORIES = {
    "physical": ["strength", "stamina", "dexterity", "agility", "constitution"],
    "mental": ["charisma", "intelligence", "wisdom", "logic", "perception"],
    "spiritual": ["aura", "willpower"]
}
ALL_STATS_ORDERED = STAT_CATEGORIES["physical"] + STAT_CATEGORIES["mental"] + STAT_CATEGORIES["spiritual"]

STAT_BONUS_BASELINE = 50
MELEE_AS_STAT_BONUS_DIVISOR = 20
RANGED_AS_STAT_BONUS_DIVISOR = 10
WEAPON_SKILL_AS_BONUS_DIVISOR = 50
DEFENSE_AGILITY_BONUS_DIVISOR = 50
DODGING_SKILL_DS_BONUS_DIVISOR = 50

STAT_DESCRIPTIONS = {
    "strength": {
        "abbr": "STR",
        "name": "Strength",
        "type": "physical",
        "desc": "A measure of a character's raw physical power, muscle mass, and ability to exert brute force. It dictates how much a character can lift, push, pull, and break. In combat, it's crucial for melee characters who rely on might. Influences: Melee Damage Bonus, Carrying Capacity, Feats of Strength (breaking doors, lifting obstacles), Weapon Handling requirements, Grappling/Climbing, Physical Intimidation, and can have a minor effect on Round Time for physical actions by representing greater efficiency in power delivery."
    },
    "stamina": {
        "abbr": "STA",
        "name": "Stamina",
        "type": "physical",
        "desc": "Represents a character's physical endurance, resilience, and ability to sustain prolonged physical exertion before succumbing to fatigue. It's about how long they can keep going. Influences: Stamina Points (SP) / Endurance Pool (as per your Max SP), Fatigue Resistance, Duration of Exertion (running, swimming), Recovery Rate of resources, minor Resistance to Physical Ailments, and can have a minor effect on Round Time by allowing quicker recovery between actions."
    },
    "dexterity": {
        "abbr": "DEX",
        "name": "Dexterity",
        "type": "physical",
        "desc": "Measures a character's physical adroitness, hand-eye coordination, precision, and fine motor skills. It governs their ability to perform delicate tasks, aim accurately, and handle weapons with finesse. Influences: Attack Accuracy (especially ranged/finesse melee), Melee Damage (for finesse weapons), Lockpicking, Disarming Traps, Pickpocketing, Crafting Precision, can contribute to Initiative/Reaction Speed, Ranged Weapon Reload Speed, and can have a minor effect on Round Time for actions requiring quick hands."
    },
    "agility": {
        "abbr": "AGI",
        "name": "Agility",
        "type": "physical",
        "desc": "Reflects a character's quickness, nimbleness, balance, and ability to move their entire body swiftly and effectively. It's about dodging attacks, maneuvering in complex environments, and overall physical grace. Influences: Defense/Evasion (Dodge Chance), Movement Speed, Initiative/Reaction Speed, Stealth/Hiding, Acrobatics, Reduced Fall Damage, and Resistance to Tripping/Knockdown."
    },
    "constitution": {
        "abbr": "CON",
        "name": "Constitution",
        "type": "physical",
        "desc": "Represents a character's overall physical health, hardiness, toughness, and resilience against bodily harm and adverse effects. It's a direct measure of their vitality. Influences: Hit Points (HP) (as per your Max HP), Resistance to Poison & Disease, Resistance to Environmental Effects, Pain Tolerance/Resistance to Stun, minor influence on Healing Rate, and ability to maintain Concentration through physical pain."
    },
    "charisma": {
        "abbr": "CHA",
        "name": "Charisma",
        "type": "mental",
        "desc": "A measure of a character's force of personality, persuasiveness, social grace, leadership qualities, and ability to influence or inspire others. It's about charm, eloquence, confidence, and presence. Influences: NPC Reactions/Disposition, Dialogue Options & Success (persuasion, diplomacy, intimidation, deception), Bartering/Trading Prices, Leadership/Follower Loyalty, Performance Skills (singing, storytelling), and can be a primary spellcasting attribute for certain classes (e.g., Bards, Sorcerers)."
    },
    "intelligence": {
        "abbr": "INT",
        "name": "Intelligence",
        "type": "mental",
        "desc": "Represents a character's capacity for learning, memory, reasoning, analytical thinking, and knowledge acquisition. It governs their ability to understand complex information and arcane subjects. Influences: Skill Points/Learning Rate, Spellcasting (especially Arcane/Wizardly, affecting spell power, spells known, or Mana Points, as per your Max MP), Knowledge-based Skills (history, arcana), Problem Solving/Puzzle Solving, Crafting (complex items like alchemy/enchanting), Language Comprehension, and Identifying Magical Effects/Items."
    },
    "wisdom": {
        "abbr": "WIS",
        "name": "Wisdom",
        "type": "mental",
        "desc": "Measures a character's common sense, intuition, awareness, and ability to make sound judgments, often reflecting an understanding of the world and a connection to instinct or divine insight. Influences: Perceptive abilities (insight, sensing danger, seeing through deception - distinct from PER's sensory acuity), Resistance to Mental Manipulation (charm, confusion), Spellcasting (especially Divine/Nature-based, affecting spell power or Mana Points, as per your Max MP), Survival Skills, Healing Skills effectiveness, and unlocking insightful Dialogue Options."
    },
    "logic": {
        "abbr": "LOG",
        "name": "Logic",
        "type": "mental",
        "desc": "Represents a character's ability for rational thought, deductive reasoning, pattern recognition, and understanding complex systems or abstract concepts. It's about the application of knowledge through structured thinking. Influences: Problem Solving (puzzles, riddles requiring deduction), Strategy & Tactics, Crafting (technical/mechanical devices), Deciphering Codes/Languages, Identifying Flaws/Weaknesses in arguments or defenses, certain specialized Spellcasting, and analytical Trap Detection/Disarm (complementing Dexterity)."
    },
    "perception": {
        "abbr": "PER",
        "name": "Perception",
        "type": "mental",
        "desc": "A measure of a character's ability to observe their environment using their senses (sight, hearing, smell, etc.) and notice details. It's about raw sensory acuity and picking up on things others might miss. Influences: Spotting Hidden Objects/Secrets, Detecting Traps (sensory indicators), Detecting Ambushes/Stealthy Creatures, Initiative/Reaction Speed, Tracking, Ranged Attack Accuracy (at long distances/obscured targets), and Listening."
    },
    "aura": {
        "abbr": "AUR",
        "name": "Aura",
        "type": "spiritual",
        "desc": "Represents a character's innate connection to spiritual, magical, and elemental energies, and the strength of their personal life force. Influences their innate magical potential and resilience to spiritual attacks. Influences: Spirit Points (SP) or Mana Points (MP) for elemental/spiritual magic (as per your Max SP, described as Spirit Points), Effectiveness of Elemental/Spiritual Magic, Resistance to Spiritual/Aura-based Attacks (life drain, soul manipulation), Detecting Auras/Magical Signatures, Empathy/Connection to Nature or Spirits, and can influence Magical Item Attunement."
    },
    "willpower": {
        "abbr": "WIL",
        "name": "Willpower",
        "type": "spiritual",
        "desc": "Represents a character's mental fortitude, self-discipline, determination, and ability to resist coercion, fear, temptation, and mental stress. It's the strength of their mind to stay focused and endure. Influences: Resistance to Mental Attacks (fear, charm, illusion), Maintaining Concentration (especially for spellcasters under duress), Resisting Fear/Morale Checks, Overcoming Pain/Debilitation to continue acting, minor influence on Magic Point Regeneration, Resisting Temptation/Corruption, and Channeling/Controlling Powerful or Volatile Energies (as per your contribution to Max SP)."
    }
}

STAT_ABBR_TO_FULL = {v["abbr"].lower(): k for k, v in STAT_DESCRIPTIONS.items()}

STAT_BONUS_BASELINE = 50
DERIVED_STATISTICS_INFO = {
        "hit_points_max": {
        "abbr": "Max HP",
        "name": "Maximum Hit Points",
        "desc": "The total amount of damage a character can sustain before being incapacitated or dying. Directly reflects vitality and physical toughness.",
        "primary_contributors": ["Constitution", "Stamina"],
        "formula_idea": "(Constitution * 10) + (Stamina * 2)  # Your current formula"
    },
    "mana_points_max": {
        "abbr": "Max MP",
        "name": "Maximum Mana Points",
        "desc": "The total pool of magical energy available for casting spells, typically those of an intellectual or learned nature.",
        "primary_contributors": ["Intelligence", "Wisdom", "Logic"],
        "formula_idea": "(Intelligence * 7) + (Wisdom * 5) + (Logic * 3)  # Your current formula"
    },
    "spirit_points_max": {
        "abbr": "Max SP",
        "name": "Maximum Spirit Points",
        "desc": "The total pool of energy used for spiritual abilities, exertions of will, or elemental manifestations. Represents inner strength and connection to vital energies.",
        "primary_contributors": ["Stamina", "Strength", "Willpower", "Aura"], # Aura added as a strong conceptual link
        "formula_idea": "(Stamina * 8) + (Strength * 2) + (Willpower // 2) + (Aura * AuraMultiplier) # Your current + Aura conceptual addition"
    },
    "physical_attack_power": {
        "abbr": "PAP",
        "name": "Physical Attack Power",
        "desc": "Represents the character's base effectiveness and damage bonus with physical attacks (melee and potentially ranged).",
        "primary_contributors": ["Strength", "Dexterity"],
        "formula_idea": "BaseWeaponDamage + (Strength * StrMultiplier) + (Dexterity * DexMultiplierForFinesse)"
    },
    "magical_potency": {
        "abbr": "MPO",
        "name": "Magical Potency",
        "desc": "Determines the effectiveness, damage, or duration of cast spells.",
        "primary_contributors": ["Intelligence", "Wisdom", "Aura", "Logic"],
        "formula_idea": "BaseSpellEffect + (PrimaryCastingStat * Multiplier) + (SecondaryCastingStat * OtherMultiplier)"
    },
    "physical_defense": {
        "abbr": "PDF",
        "name": "Physical Defense",
        "desc": "Measures a character's ability to avoid or mitigate damage from physical attacks, through dodging or armor.",
        "primary_contributors": ["Agility", "Equipment", "Stamina"],
        "formula_idea": "BaseDefense + (Agility * AgiMultiplier) + ArmorValue + (Stamina * StaSoakMultiplier)"
    },
    "magical_resistance": {
        "abbr": "MRES",
        "name": "Magical Resistance",
        "desc": "Indicates a character's ability to resist or lessen the effects of harmful magic.",
        "primary_contributors": ["Willpower", "Aura", "Wisdom", "Constitution"],
        "formula_idea": "(Willpower * WilMultiplier) + (Aura * AuraMultiplier) + (Wisdom * WisResistMultiplier)"
    },
    "initiative": {
        "abbr": "INIT",
        "name": "Initiative",
        "desc": "Determines how quickly a character reacts and their turn order in combat scenarios.",
        "primary_contributors": ["Agility", "Perception", "Dexterity"],
        "formula_idea": "BaseInitiative + (Agility * AgiMultiplier) + (Perception * PerMultiplier) + (Dexterity * DexMultiplier)"
    },
    "dodge_chance": {
        "abbr": "DODGE",
        "name": "Dodge Chance",
        "desc": "The probability of completely avoiding a physical attack through nimbleness.",
        "primary_contributors": ["Agility", "Perception"],
        "formula_idea": "BaseDodge + (Agility * AgiMultiplier) + (Perception * PerAwarenessMultiplier)"
    },
    "critical_hit_chance": {
        "abbr": "CRIT%",
        "name": "Critical Hit Chance",
        "desc": "The probability of an attack striking a vital point for increased effect or damage.",
        "primary_contributors": ["Dexterity", "Perception", "Logic"],
        "formula_idea": "BaseCritChance + (Dexterity * DexMultiplier) + (Perception * PerMultiplier / 2) + (Logic * LogMultiplier / 2)"
    },
    "carry_capacity": {
        "abbr": "CARRY",
        "name": "Carry Capacity",
        "desc": "The maximum amount of weight a character can carry without suffering penalties.",
        "primary_contributors": ["Strength", "Stamina"],
        "formula_idea": "BaseCarryWeight + (Strength * StrMultiplier) + (Stamina * StaEnduranceMultiplier)"
    },
    "healing_effectiveness": {
        "abbr": "HEAL+",
        "name": "Healing Effectiveness",
        "desc": "Increases the amount restored by healing abilities or items.",
        "primary_contributors": ["Wisdom", "Intelligence", "Aura"],
        "formula_idea": "BaseHealBonus + (Wisdom * WisMultiplier) + (Aura * AuraLifeMultiplier)"
    },
    "skill_aptitude": {
        "abbr": "SKILL+",
        "name": "Skill Aptitude",
        "desc": "Affects the rate at which skills are learned or the maximum rank achievable in skills.",
        "primary_contributors": ["Intelligence", "Logic", "Wisdom"],
        "formula_idea": "BaseLearningRate + (Intelligence * IntMultiplier) + (Logic * LogMultiplier)"
    },
    "social_influence": {
        "abbr": "SOC+",
        "name": "Social Influence",
        "desc": "Modifier for interactions with NPCs, such as persuasion, intimidation, or bartering.",
        "primary_contributors": ["Charisma", "Perception", "Wisdom"],
        "formula_idea": "BaseSocialMod + (Charisma * ChaMultiplier) + (Perception * PerInsightMultiplier)"
    },
    "trap_lore": {
        "abbr": "TRAPLR",
        "name": "Trap Lore",
        "desc": "Affects the ability to detect, understand, and disarm traps.",
        "primary_contributors": ["Perception", "Logic", "Dexterity", "Intelligence"],
        "formula_idea": "Detect: (Perception + Logic), Disarm: (Dexterity + Intelligence + Logic)"
    },
    "stealth_modifier": {
        "abbr": "STLTH+",
        "name": "Stealth Modifier",
        "desc": "A bonus or penalty to attempts to move unseen or unheard.",
        "primary_contributors": ["Agility", "Perception"],
        "formula_idea": "BaseStealth + (Agility * AgiMultiplier) - (SizeModifier) + (Perception * PerAwarenessMultiplier)"
    },
    "concentration": {
        "abbr": "CONC",
        "name": "Concentration",
        "desc": "Ability to maintain focus on tasks, especially spellcasting, when under duress or distracted.",
        "primary_contributors": ["Willpower", "Constitution", "PrimaryCastingStat"],
        "formula_idea": "BaseConcentration + (Willpower * WilMultiplier) + (Constitution * ConMultiplier) + (CastingStat * CastFocusMultiplier)"
    }
}

#--- RT DEFAULTS ----
ROUNDTIME_DEFAULTS = {
    "roundtime_look": 0.2,
    "roundtime_move": 0.5,
    "roundtime_attack": 3
}

# --- COMBAT REFACTOR CONSTANTS ---
COMBAT_ADVANTAGE_FACTOR = 40  # The static "AvD" value added to the d100 roll formula component
COMBAT_HIT_THRESHOLD = 0      # If (AS_eff - DS + COMBAT_ADVANTAGE_FACTOR + d100_roll) > this, it's a hit.
COMBAT_DAMAGE_MODIFIER_DIVISOR = 10 # How much the margin of success affects damage (e.g. result / 20)
                                   # Example: result of 136 -> 136/20 = +6.8 damage.
                                   # Adjust this to scale damage appropriately.
DEFAULT_UNARMORED_TYPE = "unarmored"
ARMOR_TYPES = [DEFAULT_UNARMORED_TYPE, "cloth", "leather", "scale", "chain", "plate"] # Define standard armor categories




ALL_SKILLS_LIST = [
    "armor_use",   
    "shield_use", 
    "edged_weapons", 
    "blunt_weapons", 
    "two_handed_weapons",
    "ranged_weapons", 
    "thrown_weapons", 
    "polearm_weapons", 
    "brawling", 
    "combat",
    "athletics", 
    "ambush", 
    "two_weapon_combat", 
    "combat_maneuvers", 
    "multi_opponent_combat",
    "physical_fitness", 
    "dodging", 
    "diplomacy", 
    "survival", 
    "disarming_traps",
    "picking_locks", 
    "stalking_and_hiding", 
    "active_perception", 
    "climbing", 
    "swimming",
    "first_aid", 
    "trading", 
    "pickpocketing", 
    "arcane_symbols", 
    "magic_item_use",
    "spell_aiming", 
    "harness_power", 
    "mana_control", 
    "spell_research", 
    "elemental_lore",
    "spiritual_lore", 
    "sorcerous_lore", 
    "mental_lore",
    "unarmed_combat", 
    "observe", 
    "basic_literacy", 
    "healing_arts"
]

INITIAL_SKILLS = {
    "brawling": 5, # Give a small base brawling skill
    "dodging": 5,  # Example
    # ... other initial skills if any ...
}


ALL_ORGANIZATIONS_LIST = {
    "Mercenary Guild", "Knightly Order", "Gladiator Arena", "Monastery", "Assassins", 
    "Trappers & Rangers", "Scouts", "Seafarer's", "Herbalists",
    "Arcane Academy", "Mystics",
    "Sorcerers", "Elementalists", "Patron Gods",
    "Town Hall", "Civics", "Trade Guilds", "Cartopgraphy",
    "Theives Guild", "Spies", "Forgery"
    "Clerics & Healers", "Empaths",
    "Loremasters", "Archivists", "Tinker's",
    "House of Many Faces", "Performing Arts", "Storycraft", "Seduction/Charm",
    "Alchemy", "Cooking", "Enchanting",

}

SKILL_DESCRIPTIONS = {
    "armor_use": {
        "name": "Armor Use",
        "type": "Combat - Defensive",
        "desc": "Proficiency in wearing and moving effectively in various types of armor. Reduces encumbrance penalties, improves maximum dexterity bonus allowed by armor, and may unlock an armor's special protective qualities. Higher skill allows comfortable use of heavier armors.",
        "governing_stats": ["CON", "STR", "STA"]
    },
    "shield_use": {
        "name": "Shield Use",
        "type": "Combat - Defensive",
        "desc": "The ability to effectively wield a shield for defense. Improves block chance, defensive coverage, and allows for shield-specific maneuvers like bashing or interposing for allies.",
        "governing_stats": ["STR", "DEX", "AGI"]
    },
    "edged_weapons": {
        "name": "Edged Weapons",
        "type": "Combat - Melee",
        "desc": "Skill in wielding weapons with a sharp edge, such as swords, axes, daggers, and scythes. Affects accuracy, damage, and the ability to perform special attacks like cleaving or precise strikes.",
        "governing_stats": ["STR", "DEX", "AGI"]
    },
    "blunt_weapons": {
        "name": "Blunt Weapons",
        "type": "Combat - Melee",
        "desc": "Proficiency with impact weapons like maces, hammers, clubs, and staves. Influences accuracy, damage (especially against armored foes), and the chance to daze or stun opponents.",
        "governing_stats": ["STR", "CON"]
    },
    "two_handed_weapons": {
        "name": "Two-Handed Weapons",
        "type": "Combat - Melee",
        "desc": "Mastery of large weapons requiring two hands to wield, such as greatswords, greataxes, and heavy mauls. Governs accuracy, enhances damage output through powerful swings, and may enable sweeping attacks.",
        "governing_stats": ["STR", "STA", "CON"]
    },
    "ranged_weapons": {
        "name": "Ranged Weapons",
        "type": "Combat - Ranged",
        "desc": "Skill with projectile weapons like bows, crossbows, and slings. Determines accuracy at various distances, rate of fire, and the ability to make called shots or use specialized ammunition effectively.",
        "governing_stats": ["DEX", "PER", "STR"] # STR for draw strength/larger bows
    },
    "thrown_weapons": {
        "name": "Thrown Weapons",
        "type": "Combat - Ranged",
        "desc": "Proficiency in accurately throwing weapons such as daggers, javelins, axes, or shuriken. Affects range, accuracy, damage, and the ability to retrieve or rapidly draw throwing weapons.",
        "governing_stats": ["DEX", "STR", "PER"]
    },
    "polearm_weapons": {
        "name": "Polearm Weapons",
        "type": "Combat - Melee",
        "desc": "Skill in using long-shafted weapons like spears, halberds, glaives, and tridents. Impacts accuracy, reach, ability to set against charges, make sweeping attacks, or control spacing in combat.",
        "governing_stats": ["STR", "DEX", "AGI"]
    },
    "brawling": {
        "name": "Brawling",
        "type": "Combat - Melee",
        "desc": "Effectiveness in rough-and-tumble, improvised fighting, often utilizing underhanded tactics, environmental objects, or brute force rather than formal technique. May include grapples, shoves, and headbutts.",
        "governing_stats": ["STR", "AGI", "CON"]
    },
    "combat": { # Renamed "Combat Tactics" for clarity if "Combat" is too general
        "name": "Combat Tactics",
        "type": "Combat - General",
        "desc": "A general understanding of combat flow, positioning, recognizing enemy patterns, and making sound tactical decisions during a fight. May provide bonuses to initiative, defense against flanking, or exploiting openings.",
        "governing_stats": ["INT", "LOG", "PER", "WIS"]
    },
    "athletics": {
        "name": "Athletics",
        "type": "Physical - General",
        "desc": "General physical prowess covering a range of activities like running, jumping, lifting, and throwing (non-combat). Influences movement speed over difficult terrain, jump distance/height, and resistance to physical fatigue from non-combat exertion.",
        "governing_stats": ["STR", "AGI", "STA"]
    },
    "ambush": {
        "name": "Ambush",
        "type": "Combat - Stealth",
        "desc": "The art of setting up and executing surprise attacks. Improves the chance of remaining undetected before an attack, increases damage or status effects applied on the initial strike from stealth, and may grant initiative bonuses.",
        "governing_stats": ["AGI", "PER", "LOG", "INT"]
    },
    "two_weapon_combat": {
        "name": "Two-Weapon Combat",
        "type": "Combat - Melee",
        "desc": "Skill in effectively fighting with a weapon in each hand. Mitigates penalties to accuracy and damage typically associated with dual-wielding and may allow for additional attacks or defensive maneuvers.",
        "governing_stats": ["DEX", "AGI", "STR"] # STR for managing weight/balance
    },
    "combat_maneuvers": {
        "name": "Combat Maneuvers",
        "type": "Combat - Melee/General",
        "desc": "Proficiency in performing specialized combat actions beyond basic attacks, such as disarming, tripping, feinting, grappling, shoving, or overrunning opponents. Success depends on skill and relevant physical attributes.",
        "governing_stats": ["DEX", "STR", "LOG", "AGI"]
    },
    "multi_opponent_combat": {
        "name": "Multi-Opponent Combat",
        "type": "Combat - General",
        "desc": "The ability to effectively engage and defend against multiple adversaries simultaneously. Reduces penalties when outnumbered, improves awareness of surrounding threats, and may enable techniques to strike multiple foes.",
        "governing_stats": ["AGI", "PER", "STA", "WIS"]
    },
    "physical_fitness": {
        "name": "Physical Fitness",
        "type": "Physical - General",
        "desc": "Represents overall bodily conditioning, resilience to sustained effort, and rapid recovery from physical strain. Improves stamina regeneration, resistance to non-magical fatigue, and may slightly increase base health or carrying capacity.",
        "governing_stats": ["STA", "CON", "STR"]
    },
    "dodging": {
        "name": "Dodging",
        "type": "Combat - Defensive",
        "desc": "The active skill of evading incoming physical attacks through timely body movements, weaves, and sidesteps. Directly contributes to an active defense roll or chance to avoid being hit.",
        "governing_stats": ["AGI", "PER", "DEX"]
    },
    "diplomacy": {
        "name": "Diplomacy",
        "type": "Social",
        "desc": "The art of peaceful negotiation, persuasion, and fostering amicable relations. Used to influence NPC attitudes, resolve conflicts without violence, gather information, or strike favorable bargains.",
        "governing_stats": ["CHA", "WIS", "INT"]
    },
    "survival": {
        "name": "Survival",
        "type": "Utility - Outdoors",
        "desc": "Knowledge and skills for thriving in wilderness or hostile environments. Includes tracking, foraging for food/water, creating shelter, navigating, and identifying natural hazards or resources.",
        "governing_stats": ["WIS", "PER", "CON", "INT"]
    },
    "disarming_traps": {
        "name": "Disarming Traps",
        "type": "Utility - Rogue",
        "desc": "The delicate skill of neutralizing mechanical and potentially magical traps without triggering them. Requires keen observation, steady hands, and an understanding of trap mechanisms.",
        "governing_stats": ["DEX", "LOG", "PER", "INT"]
    },
    "picking_locks": {
        "name": "Picking Locks",
        "type": "Utility - Rogue",
        "desc": "The ability to open locks on doors, chests, and other containers without a key, using picks and tension tools. Success relies on manual dexterity and understanding lock mechanics.",
        "governing_stats": ["DEX", "PER", "LOG"]
    },
    "stalking_and_hiding": {
        "name": "Stalking and Hiding",
        "type": "Stealth",
        "desc": "Proficiency in moving silently and remaining unseen in various environments. Essential for reconnaissance, evasion, setting up ambushes, and avoiding detection by creatures or guards.",
        "governing_stats": ["AGI", "PER", "WIS"]
    },
    "perception": { # Skill of active perception
        "name": "Perception",
        "type": "Utility - General",
        "desc": "The trained skill of actively focusing one's senses to notice subtle details, hidden objects, approaching enemies, or other important environmental cues that might otherwise be missed. Differs from the passive stat by representing active effort.",
        "governing_stats": ["PER", "WIS", "INT"] # PER stat as base, WIS for intuition, INT for pattern rec
    },
    "climbing": {
        "name": "Climbing",
        "type": "Physical - Movement",
        "desc": "Skill in ascending, descending, or traversing vertical or dangerously angled surfaces like walls, cliffs, and trees. Governs speed, safety, and the ability to find handholds.",
        "governing_stats": ["STR", "AGI", "STA", "DEX"]
    },
    "swimming": {
        "name": "Swimming",
        "type": "Physical - Movement",
        "desc": "Proficiency in moving through water. Affects speed, stamina consumption while swimming, and the ability to navigate currents or swim in adverse conditions.",
        "governing_stats": ["STA", "STR", "AGI"]
    },
    "first_aid": {
        "name": "First Aid",
        "type": "Utility - Healing",
        "desc": "Basic medical knowledge to treat minor wounds, staunch bleeding, and apply rudimentary care to injuries in the field. Can restore a small amount of health or alleviate simple negative conditions.",
        "governing_stats": ["INT", "DEX", "WIS"]
    },
    "trading": {
        "name": "Trading",
        "type": "Social - Utility",
        "desc": "The art of commerce and bartering. Higher skill allows for negotiating better prices when buying or selling goods, identifying valuable items, and understanding market fluctuations.",
        "governing_stats": ["CHA", "INT", "LOG"]
    },
    "pickpocketing": {
        "name": "Pickpocketing",
        "type": "Stealth - Rogue",
        "desc": "The ability to deftly steal small items from an unsuspecting target's person or possessions. Success depends on stealth, manual dexterity, and awareness of the target's attention.",
        "governing_stats": ["DEX", "AGI", "PER", "LOG"]
    },
    "arcane_symbols": {
        "name": "Arcane Symbols",
        "type": "Magic - Knowledge",
        "desc": "The ability to recognize, interpret, and understand magical runes, glyphs, sigils, and other symbolic representations of magical power. Essential for reading scrolls, deciphering magical texts, and identifying enchanted objects.",
        "governing_stats": ["INT", "LOG", "AUR", "WIS"]
    },
    "magic_item_use": {
        "name": "Magic Item Use",
        "type": "Magic - Utility",
        "desc": "Proficiency in identifying, attuning to, and activating the properties of magical items such as wands, staves, rings, and amulets. Higher skill may unlock more potent effects or allow use of more complex items.",
        "governing_stats": ["INT", "AUR", "WIL", "WIS"]
    },
    "spell_aiming": {
        "name": "Spell Aiming",
        "type": "Magic - Combat",
        "desc": "The skill of precisely targeting spells, especially those that require a direct hit or affect a specific area. Improves accuracy against moving or evasive targets and can reduce chances of friendly fire.",
        "governing_stats": ["DEX", "PER", "PrimaryCastingStat", "WIL"] # PrimaryCastingStat varies
    },
    "harness_power": {
        "name": "Harness Power",
        "type": "Magic - General",
        "desc": "The ability to safely draw upon and channel raw magical energies from internal reserves or external sources. Improves the efficiency of mana usage, the amount of power that can be gathered, and reduces risks of magical backlash.",
        "governing_stats": ["AUR", "WIL", "CON", "INT"]
    },
    "mana_control": {
        "name": "Mana Control",
        "type": "Magic - General",
        "desc": "The fine manipulation of magical energies during spellcasting. Allows for more efficient spellcasting, sustaining concentration on complex spells, and potentially modifying spell effects subtly (e.g., range, duration).",
        "governing_stats": ["WIL", "AUR", "PrimaryCastingStat", "LOG"]
    },
    "spell_research": {
        "name": "Spell Research",
        "type": "Magic - Knowledge",
        "desc": "The scholarly pursuit of understanding magical theory, creating new spells, or modifying existing ones. Requires deep arcane knowledge, logical deduction, and experimentation.",
        "governing_stats": ["INT", "LOG", "AUR", "WIS"]
    },
    "elemental_lore": {
        "name": "Elemental Lore",
        "type": "Magic - Knowledge",
        "desc": "In-depth knowledge of the classical elements (fire, water, air, earth), their interactions, associated spirits or creatures, and the principles of elemental magic. Improves effectiveness and understanding of elemental spells and resistances.",
        "governing_stats": ["INT", "AUR", "WIS"]
    },
    "spiritual_lore": {
        "name": "Spiritual Lore",
        "type": "Magic - Knowledge",
        "desc": "Understanding of spirits, the soul, the afterlife, divine energies, and the practices of spiritual magic (e.g., healing, summoning, interacting with spiritual entities). Enhances interaction with spirits and the potency of spiritual abilities.",
        "governing_stats": ["INT", "AUR", "WIS", "CHA"] # CHA for dealing with entities
    },
    "sorcerous_lore": {
        "name": "Sorcerous Lore",
        "type": "Magic - Knowledge",
        "desc": "Knowledge pertaining to innate, instinctual, or chaotic forms of magic, often derived from bloodlines, pacts, or raw talent rather than formal study. Aids in controlling and understanding such unpredictable powers.",
        "governing_stats": ["INT", "CHA", "AUR", "WIL"]
    },
    "mental_lore": {
        "name": "Mental Lore",
        "type": "Magic - Knowledge/Psionics",
        "desc": "The study of the mind, consciousness, psionic abilities, illusions, and forms of mental influence or control. Enhances the use and resistance of mind-affecting abilities and understanding of psychological phenomena.",
        "governing_stats": ["INT", "WIS", "LOG", "WIL"]
    },
    "unarmed_combat": {
        "name": "Unarmed Combat",
        "type": "Combat - Melee",
        "desc": "Proficiency in fighting without weapons, utilizing structured martial arts techniques such as punches, kicks, blocks, and throws. Improves accuracy, damage, and defensive capabilities when fighting bare-handed.",
        "governing_stats": ["STR", "DEX", "AGI", "STA"]
    },
    "observe": {
        "name": "Observe",
        "type": "Utility - General",
        "desc": "The skill of conducting a focused and detailed examination of a specific target, object, or small area. Can reveal hidden properties, weaknesses, specific details, or intentions that casual perception might miss.",
        "governing_stats": ["PER", "INT", "LOG", "WIS"]
    },
    "basic_literacy": {
        "name": "Basic Literacy",
        "type": "General - Utility",
        "desc": "The fundamental ability to read and write in the common language. Allows for understanding signs, simple notes, books, and communicating through written text. A prerequisite for many knowledge-based skills.",
        "governing_stats": ["INT"]
    },
    "healing_arts": {
        "name": "Healing Arts",
        "type": "Healing - Magic/Utility",
        "desc": "Advanced knowledge and practice of treating wounds, diseases, and other ailments, potentially combining medical techniques with restorative magic. Greatly improves the effectiveness of healing actions and allows for more complex treatments.",
        "governing_stats": ["WIS", "INT", "AUR", "DEX"] # DEX for surgical precision
    }
}

INITIAL_SKILLS = {skill_name: 0 for skill_name in ALL_SKILLS_LIST}
INITIAL_SKILLS["unarmed_combat"] = 1
INITIAL_SKILLS["observe"] = 1
INITIAL_SKILLS["basic_literacy"] = 1
INITIAL_SKILLS["dodging"] = 1
INITIAL_SKILLS["physical_fitness"] = 1

# --- XP SYSTEM ---
# (Keep TICK_INTERVAL_SECONDS, XP_ABSORPTION_INTERVAL_SECONDS, XP_ABSORPTION_TICKS)
# XP_POINTS_ABSORBED_PER_INTERVAL will be fully dynamic.
MIN_XP_ABSORBED_PER_EVENT = 1 # Minimum XP to absorb if calculations result in less.

BASE_FIELD_XP_POOL_CAPACITY = 1000
FIELD_XP_POOL_LOGIC_BONUS_MULTIPLIER = 50 # Multiplier for Logic Bonus for pool size

# Divisors for Logic Bonus's contribution to XP absorption rate
XP_ABSORB_LOGIC_BONUS_DIVISOR_NODE_TOWN = 5
XP_ABSORB_LOGIC_BONUS_DIVISOR_OTHER = 7

# Pool Size Bonus for XP Absorption
XP_ABSORB_POOL_SIZE_BONUS_PER_XP_AMOUNT = 200
XP_ABSORB_POOL_SIZE_BONUS_POINT = 1
XP_ABSORB_POOL_SIZE_BONUS_CAP_XP = 2000
XP_ABSORB_POOL_SIZE_BONUS_MAX_POINTS = 10 # (2000 / 200 * 1)

# Other XP Absorption Bonuses
XP_ABSORB_SUPER_NODE_BONUS = 2
XP_ABSORB_GROUP_BONUS = 1

# Base XP Absorption Rates per pulse/event
XP_ABSORB_BASE_RATE_ON_NODE = 25
XP_ABSORB_BASE_RATE_IN_TOWN_OFF_NODE = 22
XP_ABSORB_BASE_RATE_OTHER_AREAS = 19

# --- PRONOUNS ---
PLAYER_PRONOUN_CONFIG = {
    "keys_to_set": [
        "subjective",
        "possessive_determiner",
        "objective",
        "possessive_pronoun",
        "reflexive",
        "gender_specific_noun",
        "gender_specific_young_noun"
    ],
    "male": {
        "subjective": "he",
        "possessive_determiner": "his",
        "objective": "him",
        "possessive_pronoun": "his",
        "reflexive": "himself",
        "gender_specific_noun": "man",
        "gender_specific_young_noun": "boy"
    },
    "female": {
        "subjective": "she",
        "possessive_determiner": "her",
        "objective": "her",
        "possessive_pronoun": "hers",
        "reflexive": "herself",
        "gender_specific_noun": "woman",
        "gender_specific_young_noun": "girl"
    },
    "other_prompts": [
        ("subjective", "Enter your preferred subjective pronoun (e.g., he, she, they, ze):"),
        ("possessive_determiner", "Enter your preferred possessive determiner (e.g., his, her, their, zir):"),
        ("objective", "Enter your preferred objective pronoun (e.g., him, her, them, zir):"),
        ("possessive_pronoun", "Enter your preferred possessive pronoun (e.g., his, hers, theirs, zirs):"),
        ("reflexive", "Enter your preferred reflexive pronoun (e.g., himself, herself, themself, zirself):"),
        ("gender_specific_noun", "Enter a gender-specific noun for an adult (e.g., man, woman, person, individual):"),
        ("gender_specific_young_noun", "Enter a gender-specific noun for a youth (e.g., boy, girl, child, youth):")
    ]
}

# --- EQUIPMENT SLOTS ---
# Based on your provided list, mapped to usable keys
EQUIPMENT_SLOTS = {

    # Combat specific slots (often distinct from armor/clothing slots)
    "mainhand": "Main Hand (Weapon/Tool)",
    "offhand": "Off Hand (Weapon/Shield/Tool)",

    # --- ARMOR SPECIFIC ---
    "legs_upper": "Legs (Pulled Over)", # 7 (Pants, Trousers) - Main leg armor
    "torso": "Torso",               # 8 (Shirt, Tunic, Breastplate) - Main body armor
    "arms": "Arms",                 # 14 (Sleeves, Armguards if separate)
    "legs_attached": "Legs (Attached To)", # 15 (Greaves, Shin Guards - if separate from upper)
    "hands_gloves": "Hands (Gloves)",# 20 (Gloves, Gauntlets)
    "feet_slipon": "Feet (Slip On)",# 21 (Sandals, Slippers - alternative footwear)


    "trinket_pin": "General (Pin)", # 1
    "back": "Back",                 # 2 (Cloak, Backpack)
    "waist_sash": "Waist",          # 3 (Sash, secondary belt)
    "head": "Head",                 # 4
    "shoulder_slung_l": "Shoulder", # 5.1 (Bandolier, Quiver Strap)
    "shoulder_slung_r": "Shoulder", # 5.2 (Bandolier, Quiver Strap)
    "shoulders_draped": "Shoulders)", # 6 (Mantle, Shawl)
    "wrists": "Wrist",              # 9 (Bracers - plural for both)
    "finger_l": "Finger (Left)",    # 10 (Left Hand Finger)
    "finger_r": "Finger (Right)",   # 10 (Right Hand Finger)
    "feet_boots": "Feet (Put On)",  # 11 (Boots, Shoes) - Main footwear
    "neck": "Neck",                 # 12 (Amulet)
    "belt": "Belt",                 # 13 (Main Belt)
    "ear_l": "Earlobe (Left)",      # 16
    "ear_r": "Earlobe (Right)",     # 17 (Assuming two distinct earring slots)
    "ankles": "Ankle",              # 18 (Anklets - plural for both)
    "front_worn": "Front (Worn)",   # 19 (Tabard, Apron)
    "hair_adorn": "Hair (Adornment)",# 22
    "undershirt": "Undershirt",      # 23
    "leggings_under": "Leggings (Under)",# 24

}

EQUIPMENT_SLOT_CAPACITY = {

    # Combat specific slots (often distinct from armor/clothing slots)
    "mainhand": 1,
    "offhand": 1,

    # --- ARMOR SPECIFIC ---
    "legs_upper": 1, # 7 (Pants, Trousers) - Main leg armor
    "torso": 1,               # 8 (Shirt, Tunic, Breastplate) - Main body armor
    "arms": 1,                 # 14 (Sleeves, Armguards if separate)
    "legs_attached": 1, # 15 (Greaves, Shin Guards - if separate from upper)
    "hands_gloves": 1,# 20 (Gloves, Gauntlets)
    "feet_boots": 1,  # 11 (Boots, Shoes) - Main footwear
    "trinket_pin": 1000, # 1
    "back": 3,                 # 2 (Cloak, Backpack)
    "waist_sash": 3,          # 3 (Sash, secondary belt)
    "head": 1,                 # 4
    "shoulder_slung_l": 2, # 5.1 (Bandolier, Quiver Strap)
    "shoulder_slung_r": 2, # 5.2 (Bandolier, Quiver Strap)
    "shoulders_draped": 1, # 6 (Mantle, Shawl)
    "wrists": 2,              # 9 (Bracers - plural for both)
    "finger_l": 5,    # 10 (Left Hand Finger)
    "finger_r": 5,   # 10 (Right Hand Finger)
    "feet_slipon": 1, # 21 (Sandals, Slippers - alternative footwear)
    "neck": 2,                 # 12 (Amulet)
    "belt": 1,                 # 13 (Main Belt)
    "ear_l": 2,      # 16
    "ear_r": 2,     # 17 (Assuming two distinct earring slots)
    "ankles": 2,              # 18 (Anklets - plural for both)
    "front_worn": 1,   # 19 (Tabard, Apron)
    "hair_adorn": 2, # 22
    "undershirt": 1,      # 23
    "leggings_under": 1, # 24

}
# A simplified list for common usage, ensure your items use these keys:
# head, neck, torso, undershirt, back, shoulders_draped, arms, wrists, hands_gloves,
# finger_l, finger_r, belt, waist_sash, legs_upper, leggings_under, feet_boots,
# mainhand, offhand, trinket_pin


FACTION_DISPLAY_NAMES = {
    "OakhavenCivilian": "Oakhaven Civilians",
    "GreenSkinMarauders": "Greenskin Marauders",
    "ScaleScourgeClan": "Scalescourge Clan",
    # Add other faction IDs and their display names
}
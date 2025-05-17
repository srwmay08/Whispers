# mud_project/game_logic/character_creation.py
import random
import time 

try:
    import config 
except ImportError:
    # ... (your MockConfig, ensure RACES_DEFAULT is removed if it was there)
    class MockConfig:
        PLAYER_PRONOUN_CONFIG = {
            "male": {"subjective": "he", "objective": "him", "possessive_determiner": "his", "possessive_pronoun": "his", "reflexive": "himself", "gender_specific_noun": "man", "gender_specific_young_noun": "boy"},
            "female": {"subjective": "she", "objective": "her", "possessive_determiner": "her", "possessive_pronoun": "hers", "reflexive": "herself", "gender_specific_noun": "woman", "gender_specific_young_noun": "girl"},
            "they_them": {"subjective": "they", "objective": "them", "possessive_determiner": "their", "possessive_pronoun": "theirs", "reflexive": "themself", "gender_specific_noun": "person", "gender_specific_young_noun": "youth"},
            "other_prompts": [ # (key_to_set, prompt_text)
                ("subjective", "Subjective pronoun (e.g., he, she, they, ze):"),
                ("objective", "Objective pronoun (e.g., him, her, them, zir):"),
                ("possessive_determiner", "Possessive determiner (e.g., his, her, their, zir):"),
                ("possessive_pronoun", "Possessive pronoun (e.g., his, hers, theirs, zirs):"),
                ("reflexive", "Reflexive pronoun (e.g., himself, herself, themself, zirself):"),
                ("gender_specific_noun", "Term for an adult (e.g., man, woman, person, individual):"),
                ("gender_specific_young_noun", "Term for a youth (e.g., boy, girl, child, kid):")
            ]
        }
        ALL_STATS_ORDERED = ["strength", "stamina", "dexterity", "agility", "constitution",
                             "charisma", "intelligence", "wisdom", "logic", "perception",
                             "aura", "willpower"]
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
        STAT_ABBR_TO_FULL = {v["abbr"].lower(): k for k, v in STAT_DESCRIPTIONS.items()} # Fill from config
        MIN_STAT_VALUE = 1
        MAX_STAT_VALUE = 100
        DEBUG_MODE = True
    config = MockConfig()


# ... (generate_stat_pool, start_character_creation are fine from your uploaded file) ...
def generate_stat_pool(quick_creation=False):
    if quick_creation:
        return [60] * len(config.ALL_STATS_ORDERED) # All stats at 60 for quick
    # Your existing stat rolling logic
    pool = [random.randint(20, 90)] 
    for _ in range(3): pool.append(random.randint(60, 80)) 
    for _ in range(4): pool.append(random.randint(49, 73))
    for _ in range(4): pool.append(random.randint(35, 70))
    random.shuffle(pool)
    return pool[:len(config.ALL_STATS_ORDERED)]


def start_character_creation(player_shell):
    player_shell.creation_phase = "intro_narrative"
    player_shell.creation_data = {
        "name": player_shell.name, "gender_choice": None, "pronouns_custom_step": 0,
        "race": None, "stat_pool": [],
        "assigned_stats": {stat: None for stat in config.ALL_STATS_ORDERED},
        "stat_assignment_step": 0, "quick_assigned": False
    }
    player_shell.pronouns = {} 
    player_shell.add_message({"text": "Darkness... then a dim, throbbing light behind your eyelids.", "effect": "typewriter_slow", "container": "center_fullscreen_box"}, "narrative_emotive")
    player_shell.add_message({"text": "Your mind feels like a whirlwind of scattered thoughts, slowly coalescing.", "effect": "typewriter_medium", "delay": 1500, "container": "center_fullscreen_box"}, "narrative_emotive")
    player_shell.add_message({"text": f"A faint voice seems to echo... '{player_shell.name}... is that... your name?' (yes/no, or type a new name)", "effect": "typewriter_medium", "delay": 3000, "container": "center_fullscreen_box", "prompt": True}, "prompt")
    player_shell.creation_phase = "awaiting_name_confirmation"


def _send_race_information(player_shell, game_races_data: dict): # Accepts game_races_data
    """Sends detailed race information to the client for display."""
    races_payload = []
    if not game_races_data: # Check if the passed data is empty or None
        player_shell.add_message({"text": "Race information is currently unavailable.", "type": "error"}, "error")
        player_shell.add_message("Please contact an administrator if this issue persists.", "system_warning")
        # Potentially halt creation or offer a default/retry
        return

    for key, data in game_races_data.items():
        if data.get("playable", False): 
            races_payload.append({
                "key": key, # The internal key like "dark_elf"
                "name": data.get("name", key.title()),
                "description": data.get("description", "No further details."),
                "stat_modifiers_display": {stat: f"{mod:+}" for stat, mod in data.get("stat_modifiers", {}).items()}, # For client display
                "notes": data.get("notes", "") 
            })
    
    if not races_payload: # No playable races found in game_races_data
        player_shell.add_message({"text": "No playable races are currently defined in the game data.", "type": "error"}, "error")
        return

    player_shell.add_message(
        {"races": sorted(races_payload, key=lambda x: x['name']), 
         "prompt_text": f"What is your heritage, {player_shell.name}?"},
        "display_race_options" # This message type should trigger UI update on client
    )
    player_shell.add_message("Please choose from the list.", "prompt")


def _send_stat_information_and_prompt(player_shell):
    # (Your existing implementation is fine)
    stats_payload = []
    # Make sure STAT_DESCRIPTIONS and STAT_ABBR_TO_FULL are properly populated in config.py
    for stat_key in config.ALL_STATS_ORDERED:
        desc_data = config.STAT_DESCRIPTIONS.get(stat_key, {})
        stats_payload.append({ 
            "key": stat_key, 
            "name": desc_data.get("name", stat_key.title()), 
            "abbr": desc_data.get("abbr", stat_key[:3].upper()), 
            "description": desc_data.get("description", "No further details.") 
        })
    player_shell.add_message({"stats_info": stats_payload}, "display_stat_details") # For client UI
    data = player_shell.creation_data
    player_shell.add_message({"text": f"Your available stat scores to assign are: {', '.join(map(str, data['stat_pool']))}", "container": "stat_assignment_info"}, "feedback_highlight")
    player_shell.add_message({"text": "Assign scores using: 'assign <score> <stat_abbreviation>' (e.g., 'assign 75 str'). Type 'stats' for a list of abbreviations.", "container": "stat_assignment_prompt", "prompt": True}, "prompt")
    unassigned_stats_display = [config.STAT_DESCRIPTIONS.get(s,{}).get('abbr',s[:3].upper()) for s in config.ALL_STATS_ORDERED if data['assigned_stats'].get(s) is None]
    if unassigned_stats_display:
        player_shell.add_message({"text": "Unassigned Stats: " + ", ".join(unassigned_stats_display), "container": "stat_assignment_info"}, "info")


# MODIFIED: Accepts game_races_data
def handle_creation_input(player_shell, command_input, player_handler=None, game_races_data=None):
    phase = player_shell.creation_phase
    data = player_shell.creation_data
    command_lower = command_input.lower().strip()

    # --- Name Confirmation ---
    if phase == "awaiting_name_confirmation":
        if command_lower == "yes" or (command_input.strip().title() == data['name'] and data['name']):
             player_shell.add_message({"text": f"'{data['name']}'... yes, that feels right, somehow.", "container": "center_fullscreen_box"}, "narrative_feedback")
             player_shell.creation_phase = "awaiting_gender"
             player_shell.add_message({"text": "How do you identify? (male, female, other, or type 'custom' for detailed pronoun setup)", "container": "center_fullscreen_box", "prompt": True}, "prompt")
        elif command_lower == "no":
            player_shell.add_message({"text": "Then, what is your name?", "container": "center_fullscreen_box", "prompt": True}, "prompt")
            player_shell.creation_phase = "awaiting_new_name"
        elif command_input.strip().title() != data['name'] : 
            new_name = command_input.strip().title()
            if not (3 <= len(new_name) <= 20 and new_name.replace(" ", "").isalpha()): # Allow spaces
                player_shell.add_message({"text": "An unsuitable name. It must be 3-20 letters, spaces allowed.", "container": "center_fullscreen_box"}, "error")
            elif player_handler and player_handler.player_exists(new_name):
                player_shell.add_message({"text": f"The name '{new_name}' is already whispered in the echoes. Choose another.", "container": "center_fullscreen_box"}, "error")
            else:
                data["name"] = new_name; player_shell.name = new_name
                player_shell.add_message({"text": f"You decide your name is {new_name}.", "container": "center_fullscreen_box"}, "feedback")
                player_shell.creation_phase = "awaiting_gender"
                player_shell.add_message({"text": "How do you identify? (male, female, other, or type 'custom')", "container": "center_fullscreen_box", "prompt": True}, "prompt")
        else: 
             player_shell.add_message({"text": f"Please answer 'yes' or 'no' if '{data['name']}' is your name, or type a completely new name.", "container": "center_fullscreen_box", "prompt": True}, "error")
    
    # --- New Name Input ---
    elif phase == "awaiting_new_name":
        new_name = command_input.strip().title()
        if not (3 <= len(new_name) <= 20 and new_name.replace(" ", "").isalpha()):
            player_shell.add_message({"text": "An unsuitable name. It must be 3-20 letters, spaces allowed. What is your name?", "container": "center_fullscreen_box", "prompt": True}, "error")
        elif player_handler and player_handler.player_exists(new_name):
            player_shell.add_message({"text": f"The name '{new_name}' is already whispered. Choose another.", "container": "center_fullscreen_box", "prompt": True}, "error")
        else:
            data["name"] = new_name; player_shell.name = new_name
            player_shell.add_message({"text": f"You decide your name is {new_name}.", "container": "center_fullscreen_box"}, "feedback")
            player_shell.creation_phase = "awaiting_gender"
            player_shell.add_message({"text": "How do you identify? (male, female, other, or type 'custom')", "container": "center_fullscreen_box", "prompt": True}, "prompt")

    # --- Gender Selection ---
    elif phase == "awaiting_gender":
        pronoun_config_map = getattr(config, 'PLAYER_PRONOUN_CONFIG', {})
        chosen_pronoun_set = None; gender_feedback_message = ""; next_phase_flag = False
        
        if command_lower == "male" and "male" in pronoun_config_map:
            chosen_pronoun_set = pronoun_config_map["male"].copy(); data["gender_choice"] = "male"
            gender_feedback_message = "You identify as Male."; next_phase_flag = True
        elif command_lower == "female" and "female" in pronoun_config_map:
            chosen_pronoun_set = pronoun_config_map["female"].copy(); data["gender_choice"] = "female"
            gender_feedback_message = "You identify as Female."; next_phase_flag = True
        elif command_lower == "other" and pronoun_config_map.get("they_them"): 
            chosen_pronoun_set = pronoun_config_map["they_them"].copy(); data["gender_choice"] = "other_they_them"
            gender_feedback_message = "You choose to identify with they/them pronouns."; next_phase_flag = True
        elif command_lower == "custom" and "other_prompts" in pronoun_config_map:
            player_shell.creation_phase = "awaiting_custom_pronoun"; data["pronouns_custom_step"] = 0
            if not player_shell.pronouns: player_shell.pronouns = {} # Initialize if not present
            key_to_set, prompt_text = pronoun_config_map["other_prompts"][0]
            player_shell.add_message({"text": prompt_text, "container": "center_fullscreen_box", "prompt": True}, "prompt")
        else:
            player_shell.add_message({"text": "Invalid choice. Please type 'male', 'female', 'other', or 'custom'.", "container": "center_fullscreen_box", "prompt": True}, "error")

        if next_phase_flag:
            player_shell.pronouns = chosen_pronoun_set
            player_shell.add_message({"text": gender_feedback_message, "container": "center_fullscreen_box"}, "feedback")
            player_shell.creation_phase = "awaiting_race_info_display" # Transition to race display
            _send_race_information(player_shell, game_races_data) # Pass game_races_data

    # --- Custom Pronoun Setup ---
    elif phase == "awaiting_custom_pronoun":
        pronoun_config_map = getattr(config, 'PLAYER_PRONOUN_CONFIG', {})
        custom_prompts = pronoun_config_map.get("other_prompts", [])
        current_step = data.get("pronouns_custom_step", 0)
        key_to_set, _ = custom_prompts[current_step]
        value = command_input.strip()
        if not value:
            player_shell.add_message({"text": "Please enter a value.", "container": "center_fullscreen_box", "prompt": True}, "error")
        else:
            if not player_shell.pronouns: player_shell.pronouns = {}
            player_shell.pronouns[key_to_set] = value
            player_shell.add_message({"text": f"{key_to_set.replace('_', ' ').title()} set to: '{value}'.", "container": "center_fullscreen_box"}, "feedback")
            current_step += 1; data["pronouns_custom_step"] = current_step
            if current_step < len(custom_prompts):
                next_key, next_prompt = custom_prompts[current_step]
                player_shell.add_message({"text": next_prompt, "container": "center_fullscreen_box", "prompt": True}, "prompt")
            else:
                player_shell.add_message({"text": "All custom pronouns set.", "container": "center_fullscreen_box"}, "event")
                data["gender_choice"] = "custom_set" # Mark that custom pronouns were used
                player_shell.creation_phase = "awaiting_race_info_display" # Transition to race display
                _send_race_information(player_shell, game_races_data) # Pass game_races_data

    # --- Race Selection (after info is displayed) ---
    elif phase == "awaiting_race_info_display": # This phase is for *choosing* the race
        chosen_race_key = command_lower.replace(" ", "_") # e.g. "dark elf" -> "dark_elf"
        
        if not game_races_data: # Should have been caught by _send_race_information, but double check
             player_shell.add_message({"text": "Critical error: Race data unavailable for selection.", "type": "error_critical"}, "error")
             return # Halt if no races

        if chosen_race_key in game_races_data and game_races_data[chosen_race_key].get("playable", False):
            data["race"] = chosen_race_key
            player_shell.race = chosen_race_key # Set on player object immediately
            race_name_display = game_races_data[chosen_race_key].get("name", chosen_race_key.title())
            player_shell.add_message({"text": f"You have chosen to be {race_name_display}.", "container": "center_fullscreen_box"}, "feedback")
            player_shell.add_message({"text": "Your form solidifies, memories of your people stirring within you.", "container": "center_fullscreen_box", "effect": "typewriter_medium"}, "narrative_emotive")
            player_shell.creation_phase = "stat_roll_method_choice"
            player_shell.add_message({"text": "Now, for your innate abilities. Do you wish to [ROLL] for your stats, or take a [QUICK] balanced start (all stats at 60)?", "container": "center_fullscreen_box", "prompt": True}, "prompt")
        else:
            player_shell.add_message({"text": f"That is not a recognized or playable heritage. Please choose from the list.", "container": "center_fullscreen_box", "prompt": True}, "error")
            _send_race_information(player_shell, game_races_data) # Resend options

    # --- Stat Roll Method Choice ---
    elif phase == "stat_roll_method_choice":
        if command_lower == "roll":
            data["stat_pool"] = generate_stat_pool(quick_creation=False)
            data["stat_pool"].sort(reverse=True) # Show highest rolls first
            player_shell.add_message({"text": "The threads of fate weave...", "container": "center_fullscreen_box", "effect":"typewriter_slow"}, "narrative_emotive")
            player_shell.creation_phase = "stat_assignment" # Changed from "stat_assignment_info_display"
            _send_stat_information_and_prompt(player_shell) # Send info and prompt for assignment
        elif command_lower == "quick":
            data["assigned_stats"] = {stat_key: 60 for stat_key in config.ALL_STATS_ORDERED}
            player_shell.stats.update(data["assigned_stats"]) # Apply base 60s
            apply_racial_modifiers(player_shell, data["race"], game_races_data) # Apply racial mods
            player_shell.add_message({"text": "A balanced form takes shape, stats set to 60, racial traits applied.", "container": "center_fullscreen_box"}, "feedback")
            display_assigned_stats(player_shell, player_shell.stats, "Your Final Base Stats (Quick Start):")
            player_shell.creation_phase = "review_character"
            player_shell.add_message({"text": "Review your character. Type 'finalize' or 'reroll'.", "container": "center_fullscreen_box", "prompt": True}, "prompt")
        else:
            player_shell.add_message({"text": "Please type 'roll' or 'quick'.", "container": "center_fullscreen_box", "prompt": True}, "error")

    # --- Stat Assignment ---
    elif phase == "stat_assignment": # This phase directly handles assignments now
        parts = command_lower.split()
        if parts[0] == "assign" and len(parts) == 3:
            try:
                score_to_assign = int(parts[1])
                stat_abbr_to_assign = parts[2].lower()
                # Ensure STAT_ABBR_TO_FULL is populated in your config.py
                stat_full_name = config.STAT_ABBR_TO_FULL.get(stat_abbr_to_assign)

                if stat_full_name is None: player_shell.add_message({"text": f"Unknown stat abbreviation: '{stat_abbr_to_assign}'. Type 'stats' for a list.", "container": "stat_assignment_prompt"}, "error")
                elif score_to_assign not in data["stat_pool"]: player_shell.add_message({"text": f"Score {score_to_assign} is not in your available pool or already used: {', '.join(map(str, data['stat_pool']))}.", "container": "stat_assignment_prompt"}, "error")
                elif data["assigned_stats"].get(stat_full_name) is not None: player_shell.add_message({"text": f"{config.STAT_DESCRIPTIONS.get(stat_full_name, {}).get('name', stat_full_name.title())} is already assigned.", "container": "stat_assignment_prompt"}, "error")
                else:
                    data["assigned_stats"][stat_full_name] = score_to_assign
                    data["stat_pool"].remove(score_to_assign)
                    player_shell.add_message({"text": f"{config.STAT_DESCRIPTIONS.get(stat_full_name, {}).get('name', stat_full_name.title())} set to {score_to_assign}.", "container": "stat_assignment_info"}, "feedback")
            except ValueError: player_shell.add_message({"text": "Invalid score. Must be a number (e.g., 'assign 75 str').", "container": "stat_assignment_prompt"}, "error")

            unassigned_stat_keys = [s for s, v in data["assigned_stats"].items() if v is None]
            if not unassigned_stat_keys: 
                player_shell.stats.update(data["assigned_stats"]) # Apply assigned base stats
                apply_racial_modifiers(player_shell, data["race"], game_races_data) # Then apply racial mods
                player_shell.add_message({"text": "All stats assigned! Racial modifiers applied.", "container": "stat_assignment_info"}, "event")
                display_assigned_stats(player_shell, player_shell.stats, "Your Final Base Stats:") 
                player_shell.creation_phase = "review_character"
                player_shell.add_message({"text": "Review your character. Type 'finalize' or 'reroll_stats'.", "container": "center_fullscreen_box", "prompt": True}, "prompt")
            else: 
                player_shell.add_message({"text": f"Remaining scores to assign: {', '.join(map(str, sorted(data['stat_pool'], reverse=True)))}", "container": "stat_assignment_info"}, "info")
                unassigned_display = [config.STAT_DESCRIPTIONS.get(s,{}).get('abbr',s[:3].upper()) for s in unassigned_stat_keys]
                player_shell.add_message({"text": "Unassigned Stats: " + ", ".join(unassigned_display), "container": "stat_assignment_info", "prompt": True}, "info")
        elif command_lower == "pool": player_shell.add_message({"text": f"Available scores: {', '.join(map(str, sorted(data['stat_pool'], reverse=True)))}", "container": "stat_assignment_info"}, "info")
        elif command_lower == "assigned": display_assigned_stats(player_shell, data["assigned_stats"], "Currently Assigned (pre-racial):")
        elif command_lower == "stats": _send_stat_information_and_prompt(player_shell) # Resend info
        elif command_lower == "reroll_stats":
            player_shell.add_message({"text": "Rerolling your stat pool...", "container": "stat_assignment_info"}, "feedback")
            data["stat_pool"] = generate_stat_pool(quick_creation=False); data["stat_pool"].sort(reverse=True)
            data["assigned_stats"] = {stat: None for stat in config.ALL_STATS_ORDERED} # Reset assignments
            _send_stat_information_and_prompt(player_shell) # Resend info with new pool
        else: player_shell.add_message({"text": "Use 'assign <score> <abbr>', 'pool', 'assigned', 'stats', or 'reroll_stats'.", "container": "stat_assignment_prompt", "prompt": True}, "prompt")

    # --- Review Character ---
    elif phase == "review_character":
        if command_lower == "finalize":
            player_shell.creation_phase = "completed" 
            player_shell.add_message({"text": "Your essence settles. You are ready to face the world.", "container": "center_fullscreen_box", "effect": "typewriter_slow_fadeout"}, "narrative_event")
        elif command_lower == "reroll_stats" or command_lower == "reroll":
            player_shell.add_message({"text": "Returning to stat method selection...", "container": "center_fullscreen_box"}, "feedback")
            player_shell.creation_phase = "stat_roll_method_choice"
            # Reset stats on player_shell and in creation_data
            player_shell.stats = {stat_name: getattr(config, 'DEFAULT_STAT_VALUE', 10) for stat_name in config.ALL_STATS_ORDERED} 
            data["assigned_stats"] = {stat: None for stat in config.ALL_STATS_ORDERED}; data["stat_pool"] = []
            player_shell.add_message({"text": "Do you wish to [ROLL] for your stats, or take a [QUICK] balanced start?", "container": "center_fullscreen_box", "prompt": True}, "prompt")
        elif command_lower == "show_stats": 
            display_assigned_stats(player_shell, player_shell.stats, "Current Final Base Stats:")
            player_shell.add_message({"text": "Type 'finalize' or 'reroll_stats'.", "container": "center_fullscreen_box", "prompt": True}, "prompt") # Re-prompt
        else: player_shell.add_message({"text": "Type 'finalize' to complete character creation, 'reroll' to restart stat selection, or 'show_stats'.", "container": "center_fullscreen_box", "prompt": True}, "prompt")


# MODIFIED: Accepts game_races_data
def apply_racial_modifiers(player_shell, race_key: str, game_races_data: dict):
    """Applies racial stat modifiers to the player_shell's stats."""
    if not game_races_data:
        if config.DEBUG_MODE: print("DEBUG apply_racial_modifiers: game_races_data is None or empty. Skipping.")
        return

    race_data = game_races_data.get(race_key)
    if not race_data:
        if config.DEBUG_MODE: print(f"DEBUG apply_racial_modifiers: No data found for race_key '{race_key}'. Skipping.")
        return
        
    stat_mods = race_data.get("stat_modifiers")
    if not stat_mods:
        if config.DEBUG_MODE: print(f"DEBUG apply_racial_modifiers: No 'stat_modifiers' found for race '{race_key}'. Skipping.")
        return

    player_shell.add_message({"text": f"Applying racial traits of the {race_data.get('name', race_key.title())}...", "container": "stat_assignment_info"}, "feedback")
    for stat, modifier in stat_mods.items():
        if stat in player_shell.stats:
            original_stat = player_shell.stats.get(stat, 0) # Get current stat, default to 0 if somehow not set
            player_shell.stats[stat] = original_stat + modifier
            
            # Clamp stats to min/max values from config
            min_stat_val = getattr(config, 'MIN_STAT_VALUE', 1) 
            max_stat_val = getattr(config, 'MAX_STAT_VALUE', 100)
            player_shell.stats[stat] = max(min_stat_val, min(player_shell.stats[stat], max_stat_val))
            
            if getattr(config, 'DEBUG_MODE', False) and original_stat != player_shell.stats[stat] :
                 player_shell.add_message({"text": f"DEBUG: {stat.title()} changed from {original_stat} to {player_shell.stats[stat]} (modifier: {modifier:+})", "container": "debug_info"}, "debug")


def display_assigned_stats(player_shell, stats_to_display: dict, title="Assigned Stats:"):
    # (Your existing implementation is fine)
    player_shell.add_message({"text": f"--- {title} ---", "container": "stat_display_area"}, "header_info_block")
    lines = []
    for stat_key in config.ALL_STATS_ORDERED: # Iterate in defined order
        score = stats_to_display.get(stat_key) # Get the score for the current stat
        desc_data = config.STAT_DESCRIPTIONS.get(stat_key, {})
        abbr = desc_data.get('abbr', stat_key[:3].upper())
        name = desc_data.get('name', stat_key.title())
        lines.append(f"{name} ({abbr}): {score if score is not None else '---'}")
    player_shell.add_message({"text": "\n".join(lines), "container": "stat_display_area"}, "info_block_content")
# mud_project/game_logic/combat.py
import random
import time
import re 
import math 

try:
    import config
    from classes import player as player_class 
except ImportError:
    # Mock config and player_class for isolated testing or if imports fail
    class MockConfigCombat:
        DEBUG_MODE = True; STAT_BONUS_BASELINE = 50; MELEE_AS_STAT_BONUS_DIVISOR = 20
        WEAPON_SKILL_AS_BONUS_DIVISOR = 50; BAREHANDED_BASE_AS = 0; DEFAULT_UNARMORED_TYPE = "unarmored"
        MELEE_DS_STAT_BONUS_DIVISOR = 10; UNARMORED_BASE_DS = 0; SHIELD_SKILL_DS_BONUS_DIVISOR = 10
        COMBAT_ADVANTAGE_FACTOR = 40; COMBAT_HIT_THRESHOLD = 0 # Gemstone uses 100, adjust based on your formula
        COMBAT_DAMAGE_MODIFIER_DIVISOR = 10
        ROUNDTIME_DEFAULTS = {'roundtime_attack': 3.0, 'roundtime_look': 0.2}
        EQUIPMENT_SLOTS = {"torso": "Torso", "mainhand": "Main Hand", "offhand": "Off Hand"}
        PLAYER_DEATH_ROOM_ID = 1 
        BAREHANDED_FLAT_DAMAGE = 1
        DEBUG_COMBAT_ROLLS = True # Ensure this is True to see detailed logs
    config = MockConfigCombat()
    if 'player_class' not in globals() or player_class is None: 
        class MockPlayer: # Basic mock for type hinting
            def __init__(self, name="MockPlayer"): self.name = name; self.stats = {}; self.skills = {}; self.equipped_items = {}; self.hp = 100; self.max_hp = 100; self.current_room_id = 1
            def add_message(self, text, type): print(f"PLAYER_MSG ({type}): {text}")
            def get_equipped_item_data(self, slot, items): return None
            def get_armor_type(self, items): return config.DEFAULT_UNARMORED_TYPE
        player_class = MockPlayer

# Stores current HP for non-player entities in combat. Key: entity_runtime_id, Value: current_hp
RUNTIME_ENTITY_HP = {} 
# Tracks entities recently defeated in a room to prevent immediate re-targeting or duplicate death processing.
# Key: entity_runtime_id, Value: True (or timestamp if needed for more complex logic)
RECENTLY_DEFEATED_TARGETS_IN_ROOM = {} 

def parse_and_roll_dice(dice_string: str) -> int:
    """Parses a dice string (e.g., '2d6+3') and returns the rolled total."""
    if not isinstance(dice_string, str): return 0
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_string.lower())
    if not match:
        try: return int(dice_string) # Handle flat numbers
        except ValueError: return 0
    num_dice, dice_sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    if num_dice <= 0 or dice_sides <= 0: return modifier # Avoid rolling 0 dice or 0-sided dice
    return sum(random.randint(1, dice_sides) for _ in range(num_dice)) + modifier

def get_stat_bonus(stat_value: int, baseline: int, divisor: int) -> int:
    """Calculates a bonus based on a stat value, a baseline, and a divisor."""
    if divisor == 0: return 0
    return (stat_value - baseline) // divisor 

def get_skill_bonus(skill_value: int, divisor: int) -> int:
    """Calculates a bonus based on a skill value and a divisor."""
    if divisor == 0: return 0
    return skill_value // divisor 

def get_entity_armor_type(entity_data_runtime, game_items_global: dict) -> str:
    """Determines the armor type of an entity (player, NPC, or monster)."""
    equipped_items_dict = {}
    if isinstance(entity_data_runtime, player_class.Player): 
        equipped_items_dict = entity_data_runtime.equipped_items
    elif isinstance(entity_data_runtime, dict): # For NPC/Monster templates
        equipped_items_dict = entity_data_runtime.get("equipped", {})
    
    # Find the torso slot key from config (e.g., "torso", "chest", etc.)
    torso_slot_key = next((key for key, val in config.EQUIPMENT_SLOTS.items() if "torso" in key.lower() or "chest" in key.lower()), "torso")
    
    chest_item_id = equipped_items_dict.get(torso_slot_key)
    if chest_item_id and game_items_global:
        chest_item_data = game_items_global.get(chest_item_id)
        if chest_item_data and chest_item_data.get("type") == "armor":
            return chest_item_data.get("armor_type", config.DEFAULT_UNARMORED_TYPE)
            
    # Fallback for entities that might have an innate armor type not from equipped items
    if isinstance(entity_data_runtime, dict):
        return entity_data_runtime.get("innate_armor_type", config.DEFAULT_UNARMORED_TYPE)
        
    return config.DEFAULT_UNARMORED_TYPE

def calculate_attack_strength(attacker_name: str, attacker_stats: dict, attacker_skills: dict, 
                              weapon_item_data: dict | None, target_armor_type: str) -> int:
    """Calculates the Attack Strength (AS) for an attacker."""
    as_val = 0
    as_components = [] # For detailed roll string
    weapon_name_display = "Barehanded"

    if not weapon_item_data or weapon_item_data.get("type") != "weapon": # Barehanded
        strength_barehanded = attacker_stats.get("strength", config.STAT_BONUS_BASELINE)
        str_bonus_barehanded = get_stat_bonus(strength_barehanded, config.STAT_BONUS_BASELINE, config.MELEE_AS_STAT_BONUS_DIVISOR)
        as_val += str_bonus_barehanded
        as_components.append(f"Str({str_bonus_barehanded})")

        brawling_skill = attacker_skills.get("brawling", 0) # Assuming "brawling" for unarmed
        brawling_bonus = get_skill_bonus(brawling_skill, config.WEAPON_SKILL_AS_BONUS_DIVISOR)
        as_val += brawling_bonus
        as_components.append(f"Brawl({brawling_bonus})")
        
        base_barehanded_as = getattr(config, 'BAREHANDED_BASE_AS', 0)
        as_val += base_barehanded_as
        if base_barehanded_as != 0: as_components.append(f"BaseAS({base_barehanded_as})")
    else: # Using a weapon
        weapon_name_display = weapon_item_data.get("name", "Unknown Weapon")
        
        strength = attacker_stats.get("strength", config.STAT_BONUS_BASELINE)
        str_bonus = get_stat_bonus(strength, config.STAT_BONUS_BASELINE, config.MELEE_AS_STAT_BONUS_DIVISOR)
        as_val += str_bonus
        as_components.append(f"Str({str_bonus})")

        weapon_skill_name = weapon_item_data.get("skill") # e.g., "edged_weapons"
        skill_bonus_val = 0
        if weapon_skill_name:
            skill_rank = attacker_skills.get(weapon_skill_name, 0)
            skill_bonus_val = get_skill_bonus(skill_rank, config.WEAPON_SKILL_AS_BONUS_DIVISOR)
            as_val += skill_bonus_val
            as_components.append(f"Skill({skill_bonus_val})") # Shorten for display
        
        weapon_base_as = weapon_item_data.get("weapon_as_bonus", 0) 
        as_val += weapon_base_as
        as_components.append(f"WpnAS({weapon_base_as})")
        
        enchant_as = weapon_item_data.get("enchantment_as_bonus", 0)
        as_val += enchant_as
        if enchant_as != 0: as_components.append(f"EnchAS({enchant_as})")
        
        # Attack vs. Defense (AvD) modifier based on weapon vs armor type
        avd_mods = weapon_item_data.get("avd_modifiers", {})
        avd_bonus = avd_mods.get(target_armor_type, avd_mods.get(config.DEFAULT_UNARMORED_TYPE, 0)) # Fallback to unarmored if specific type not found
        # This AvD is part of AS calculation before the global COMBAT_ADVANTAGE_FACTOR
        as_val += avd_bonus 
        if avd_bonus != 0: as_components.append(f"ItemAvD({avd_bonus})")

    # Placeholder for future CM/Stance bonuses to AS
    # as_components.append("CM(0)"); as_components.append("Stance(0)") 
    
    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False):
        # This log is for server console
        print(f"DEBUG AS CALC for {attacker_name} (Wpn: {weapon_name_display}): Factors = {' + '.join(as_components)} => Raw AS = {as_val}")
    return as_val


def calculate_defense_strength(defender_name: str, defender_stats: dict, defender_skills: dict, 
                               armor_item_data: dict | None, shield_item_data: dict | None, 
                               defender_stance=None) -> int: # defender_stance not used yet
    """Calculates the Defensive Strength (DS) for a defender."""
    ds_val = 0
    ds_components = [] # For detailed roll string
    armor_name_display = "Unarmored"; shield_name_display = "No Shield"

    agility_stat = defender_stats.get("agility", config.STAT_BONUS_BASELINE)
    ds_stat_divisor = getattr(config, 'MELEE_DS_STAT_BONUS_DIVISOR', 10) 
    agi_bonus = get_stat_bonus(agility_stat, config.STAT_BONUS_BASELINE, ds_stat_divisor)
    ds_val += agi_bonus
    ds_components.append(f"Agi({agi_bonus})")

    armor_ds_bonus = 0
    if armor_item_data and armor_item_data.get("type") == "armor":
        armor_ds_bonus = armor_item_data.get("armor_ds_bonus", 0)
        armor_name_display = armor_item_data.get("name", "Unknown Armor")
        ds_val += armor_ds_bonus
        ds_components.append(f"Armor({armor_ds_bonus})")
    else: # Unarmored
        unarmored_ds = getattr(config, 'UNARMORED_BASE_DS', 0)
        ds_val += unarmored_ds
        if unarmored_ds !=0: ds_components.append(f"BaseDS({unarmored_ds})")

    shield_base_bonus = 0
    if shield_item_data and shield_item_data.get("type") == "shield":
        shield_base_bonus = shield_item_data.get("shield_ds_bonus", 0)
        shield_name_display = shield_item_data.get("name", "Unknown Shield")
        ds_val += shield_base_bonus
        ds_components.append(f"Shield({shield_base_bonus})")

        shield_skill_rank = defender_skills.get("shield_use", 0) # Assuming "shield_use" skill
        shield_skill_divisor = getattr(config, 'SHIELD_SKILL_DS_BONUS_DIVISOR', 10)
        shield_skill_bonus = get_skill_bonus(shield_skill_rank, shield_skill_divisor)
        ds_val += shield_skill_bonus
        if shield_skill_bonus !=0: ds_components.append(f"ShSkill({shield_skill_bonus})")
    
    # Placeholder for future Dodge/Stance/Spell bonuses to DS
    # ds_components.append("DodgeSkill(0)"); ds_components.append("Stance(0)"); ds_components.append("SpellDS(0)")

    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False):
        # This log is for server console
        print(f"DEBUG DS CALC for {defender_name if defender_name else 'entity'} (Armor: {armor_name_display}, Shield: {shield_name_display}): Factors = {' + '.join(ds_components)} => Raw DS = {ds_val}")
    return ds_val

def handle_player_attack(player: player_class.Player, target_data: dict, target_type: str,
                         target_name_raw_from_player: str, game_items_global: dict,
                         monster_runtime_id: str | None = None, monster_instance_index: int | None = None):
    """Handles a player attacking an NPC or Monster."""
    GAME_ITEMS = game_items_global # Use passed game_items_data
    
    template_key = target_data.get("_id", target_data.get("key", "unknown_key")) # _id is preferred from DB
    target_display_name = target_data.get("name", "the creature")
    
    # Determine the correct runtime_id for the target
    entity_runtime_id = monster_runtime_id # This should be pre-calculated and passed in
    if not entity_runtime_id: # Fallback if not passed (less ideal)
        if target_type == "npc": entity_runtime_id = template_key 
        elif target_type == "monster":
             # This requires monster_instance_index if multiple non-unique monsters of same type in room
             entity_runtime_id = f"{player.current_room_id}_{template_key}_{monster_instance_index if monster_instance_index is not None else 0}"


    if config.DEBUG_MODE: print(f"DEBUG COMBAT: {player.name} attacking {target_display_name} (Type: {target_type}, TplKey: {template_key}). RuntimeID: {entity_runtime_id}.")

    if RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(entity_runtime_id):
        player.add_message(f"The {target_display_name} is already defeated!", "feedback")
        return {'hit': False, 'damage': 0, 'defeated': True, 'already_defeated': True, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    max_hp_from_template = target_data.get("max_hp", target_data.get("hp", 25))
    if entity_runtime_id not in RUNTIME_ENTITY_HP: RUNTIME_ENTITY_HP[entity_runtime_id] = max_hp_from_template
    current_hp = RUNTIME_ENTITY_HP[entity_runtime_id]

    if current_hp <= 0: 
        player.add_message(f"The {target_display_name} is already incapacitated!", "feedback")
        RECENTLY_DEFEATED_TARGETS_IN_ROOM[entity_runtime_id] = True 
        return {'hit': False, 'damage': 0, 'defeated': True, 'already_defeated': True, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    attacker_weapon_data = player.get_equipped_item_data("mainhand", GAME_ITEMS)
    weapon_name_for_msg = attacker_weapon_data.get("name", "your fist") if attacker_weapon_data else "your fist"
    player.add_message(f"You swing your {weapon_name_for_msg} at the {target_display_name}!", "combat_action_player") # More flavour

    target_armor_type_str = get_entity_armor_type(target_data, GAME_ITEMS)
    torso_slot_key = next((k for k,v in config.EQUIPMENT_SLOTS.items() if "torso" in k.lower()), "torso")
    offhand_slot_key = next((k for k,v in config.EQUIPMENT_SLOTS.items() if "offhand" in k.lower()), "offhand")
    target_armor_item_id = target_data.get("equipped", {}).get(torso_slot_key)
    target_armor_data = GAME_ITEMS.get(target_armor_item_id) if target_armor_item_id else None
    target_shield_item_id = target_data.get("equipped", {}).get(offhand_slot_key)
    target_shield_data = GAME_ITEMS.get(target_shield_item_id) if target_shield_item_id else None

    attacker_as = calculate_attack_strength(player.name, player.stats, player.skills, attacker_weapon_data, target_armor_type_str)
    defender_ds = calculate_defense_strength(target_display_name, target_data.get("stats", {}), target_data.get("skills", {}), target_armor_data, target_shield_data, target_data.get("current_stance"))
    
    d100_roll = random.randint(1, 100)
    # AvD here is the global combat advantage factor from config
    combat_roll_result = (attacker_as - defender_ds) + config.COMBAT_ADVANTAGE_FACTOR + d100_roll
    
    # Send detailed roll to the attacker
    roll_string = f"  AS: {attacker_as:+} vs DS: {defender_ds:+} with AvD: {config.COMBAT_ADVANTAGE_FACTOR:+} + d100: {d100_roll:+} = {combat_roll_result:+}"
    player.add_message(roll_string, "combat_roll_details") # New message type for specific formatting

    broadcast_msg_base = f"{player.name} attacks the {target_display_name} with their {weapon_name_for_msg}."
    combat_results_dict = {'hit': False, 'damage': 0, 'defeated': False, 'already_defeated': False, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    if combat_roll_result > config.COMBAT_HIT_THRESHOLD:
        combat_results_dict['hit'] = True
        flat_base_damage_component = 0
        if attacker_weapon_data:
            flat_base_damage_component = attacker_weapon_data.get("weapon_as_bonus", 0) + attacker_weapon_data.get("enchantment_as_bonus", 0)
        else:
            flat_base_damage_component = getattr(config, 'BAREHANDED_FLAT_DAMAGE', 1)
        
        damage_bonus_from_roll = max(0, (combat_roll_result - config.COMBAT_HIT_THRESHOLD) // config.COMBAT_DAMAGE_MODIFIER_DIVISOR)
        total_damage = max(1, flat_base_damage_component + damage_bonus_from_roll)
        
        combat_results_dict['damage'] = total_damage
        player.add_message(f"  ...and HIT the {target_display_name} for {total_damage} damage!", "combat_hit_player") # Indented hit message
        broadcast_msg_base += f" and HITS for {total_damage} damage!"
        
        current_hp -= total_damage
        RUNTIME_ENTITY_HP[entity_runtime_id] = current_hp

        if current_hp <= 0:
            player.add_message(f"  The {target_display_name} collapses, defeated!", "combat_defeat_player") # Indented
            broadcast_msg_base += f" The {target_display_name} is DEFEATED!"
            combat_results_dict['defeated'] = True
            RECENTLY_DEFEATED_TARGETS_IN_ROOM[entity_runtime_id] = True 
            if config.DEBUG_MODE: print(f"DEBUG COMBAT: {target_display_name} (RuntimeID: {entity_runtime_id}) DEFEATED by {player.name}. HP: {current_hp}/{max_hp_from_template}")
        else:
            player.add_message(f"  The {target_display_name} looks wounded. (Est. HP: {current_hp}/{max_hp_from_template})", "combat_status_target") # Indented
            broadcast_msg_base += f" The {target_display_name} is wounded."
    else:
        player.add_message(f"  ...but you MISS the {target_display_name}!", "combat_miss_player") # Indented
        broadcast_msg_base += " and MISSES!"
        
    combat_results_dict['broadcast_message'] = broadcast_msg_base
    player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
    player.add_message(f"Roundtime: {config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0):.1f} sec.", "system_info") # RT message
    return combat_results_dict

def handle_entity_attack(attacker_entity_data: dict, attacker_entity_type: str, attacker_runtime_id: str, 
                         defender_player: player_class.Player, game_items_global: dict):
    """Handles an NPC or Monster attacking a Player."""
    GAME_ITEMS = game_items_global
    attacker_display_name = attacker_entity_data.get("name", "A creature")

    if defender_player.hp <= 0: 
        if config.DEBUG_MODE: print(f"DEBUG ENTITY_ATTACK: Target player {defender_player.name} already defeated.")
        return {'hit': False, 'damage': 0, 'defender_defeated': True, 'already_defeated': True, 'attacker_message':"", 'defender_message':None, 'broadcast_message':""}

    attacker_weapon_data = None
    mainhand_item_id = attacker_entity_data.get("equipped", {}).get("mainhand")
    if mainhand_item_id: attacker_weapon_data = GAME_ITEMS.get(mainhand_item_id)
    weapon_name_for_msg = attacker_weapon_data.get("name", "its natural weapons") if attacker_weapon_data else "its natural weapons"
    
    # Message for the player being attacked (attacker action)
    defender_player.add_message(f"The {attacker_display_name} swings its {weapon_name_for_msg} at you!", "combat_action_opponent") # New type

    defender_armor_type_str = defender_player.get_armor_type(GAME_ITEMS)
    defender_armor_data = defender_player.get_equipped_item_data("torso", GAME_ITEMS)
    defender_shield_data = defender_player.get_equipped_item_data("offhand", GAME_ITEMS)

    attacker_as = calculate_attack_strength(attacker_display_name, attacker_entity_data.get("stats", {}), attacker_entity_data.get("skills", {}), attacker_weapon_data, defender_armor_type_str)
    defender_ds = calculate_defense_strength(defender_player.name, defender_player.stats, defender_player.skills, defender_armor_data, defender_shield_data, None) # Player stance not implemented yet
    
    d100_roll = random.randint(1, 100)
    combat_roll_result = (attacker_as - defender_ds) + config.COMBAT_ADVANTAGE_FACTOR + d100_roll
    
    # This is the server-side log string for the entity's attack roll.
    # We generally don't send this to the player unless they are debugging or it's a special ability.
    entity_roll_log_string = f"ENTITY_ATTACK_ROLL: {attacker_display_name} (AS:{attacker_as}) vs {defender_player.name} (DS:{defender_ds}) + AvD:{config.COMBAT_ADVANTAGE_FACTOR} + d100:{d100_roll} = {combat_roll_result}"
    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False):
        print(entity_roll_log_string)

    results = {'hit': False, 'damage': 0, 'defender_defeated': False, 
               'attacker_message': {"text": entity_roll_log_string, "type": "internal_combat_roll"}, # For server/dev
               'defender_message': None, 'broadcast_message': ""}

    if combat_roll_result > config.COMBAT_HIT_THRESHOLD:
        results['hit'] = True
        flat_base_damage_component = 0
        if attacker_weapon_data and attacker_weapon_data.get("type") == "weapon":
            flat_base_damage_component = attacker_weapon_data.get("weapon_as_bonus", 0) + attacker_weapon_data.get("enchantment_as_bonus", 0)
        else:
            flat_base_damage_component = getattr(config, 'BAREHANDED_FLAT_DAMAGE', 1)
            # More advanced: check monster template for "natural_weapon_damage_bonus" or similar
            flat_base_damage_component += attacker_entity_data.get("natural_attack_bonus_damage", 0)


        damage_bonus_from_roll = max(0, (combat_roll_result - config.COMBAT_HIT_THRESHOLD) // config.COMBAT_DAMAGE_MODIFIER_DIVISOR)
        total_damage = max(1, flat_base_damage_component + damage_bonus_from_roll)
        results['damage'] = total_damage

        defender_player.hp -= total_damage
        results['defender_message'] = {"text": f"  The {attacker_display_name} HITS you for {total_damage} damage! (HP: {defender_player.hp}/{defender_player.max_hp})", "type": "combat_hit_by_opponent"} # Indented
        results['broadcast_message'] = {"text": f"The {attacker_display_name} HITS {defender_player.name} with its {weapon_name_for_msg} for {total_damage} damage!", "type": "ambient_combat"}


        if defender_player.hp <= 0:
            results['defender_defeated'] = True
            defender_player.hp = 0 # Ensure HP doesn't go negative for display
            results['defender_message'] = {"text": f"  The {attacker_display_name}'s blow lands true! You have been DEFEATED!", "type": "event_defeat_major"} # Indented
            results['broadcast_message'] = {"text": f"{defender_player.name} has been struck down by the {attacker_display_name}!", "type": "ambient_defeat"}
            
            # Handle player death (e.g., move to death room, apply penalties)
            defender_player.current_room_id = getattr(config, 'PLAYER_DEATH_ROOM_ID', 1) # Move to default death room
            defender_player.hp = 1 # Or some other logic for respawn HP
            # No need to call send_room_description or send_player_stats_update here,
            # the game_tick_loop will handle it for the player if they are still connected,
            # or main.py's player processing loop after AI tick.
    else:
        results['defender_message'] = {"text": f"  The {attacker_display_name} MISSES you!", "type": "combat_miss_by_opponent"} # Indented
        results['broadcast_message'] = {"text": f"The {attacker_display_name} attacks {defender_player.name} with its {weapon_name_for_msg} but MISSES!", "type": "ambient_combat"}
    
    return results

def handle_player_attack_pvp(attacker_player: player_class.Player, defender_player: player_class.Player, game_items_global: dict):
    """Handles a player attacking another player."""
    GAME_ITEMS = game_items_global
    
    if defender_player.hp <= 0:
        attacker_player.add_message(f"{defender_player.name} is already defeated.", "feedback")
        return {"attacker_message": None, "defender_message": None, "broadcast_message": "", "defender_defeated": True, "already_defeated": True}

    attacker_weapon_data = attacker_player.get_equipped_item_data("mainhand", GAME_ITEMS)
    weapon_name_for_msg = attacker_weapon_data.get("name", "their fist") if attacker_weapon_data else "their fist" # For broadcast
    attacker_weapon_name_for_msg = attacker_weapon_data.get("name", "your fist") if attacker_weapon_data else "your fist" # For attacker's message

    attacker_player.add_message(f"You swing your {attacker_weapon_name_for_msg} at {defender_player.name}!", "combat_action_player")

    defender_armor_type_str = defender_player.get_armor_type(GAME_ITEMS)
    defender_armor_data = defender_player.get_equipped_item_data("torso", GAME_ITEMS)
    defender_shield_data = defender_player.get_equipped_item_data("offhand", GAME_ITEMS)

    attacker_as = calculate_attack_strength(attacker_player.name, attacker_player.stats, attacker_player.skills, attacker_weapon_data, defender_armor_type_str)
    defender_ds = calculate_defense_strength(defender_player.name, defender_player.stats, defender_player.skills, defender_armor_data, defender_shield_data, None)
    
    d100_roll = random.randint(1, 100)
    combat_roll_result = (attacker_as - defender_ds) + config.COMBAT_ADVANTAGE_FACTOR + d100_roll
    
    # Send detailed roll to the attacker
    roll_string = f"  AS: {attacker_as:+} vs DS: {defender_ds:+} with AvD: {config.COMBAT_ADVANTAGE_FACTOR:+} + d100: {d100_roll:+} = {combat_roll_result:+}"
    attacker_player.add_message(roll_string, "combat_roll_details")

    results = {'hit': False, 'damage': 0, 'defender_defeated': False, 
               'attacker_message': None, 'defender_message': None, 'broadcast_message': ""}
    
    broadcast_msg_text = f"{attacker_player.name} attacks {defender_player.name} with {weapon_name_for_msg}."

    if combat_roll_result > config.COMBAT_HIT_THRESHOLD:
        results['hit'] = True
        flat_base_damage_component = 0
        if attacker_weapon_data:
            flat_base_damage_component = attacker_weapon_data.get("weapon_as_bonus", 0) + attacker_weapon_data.get("enchantment_as_bonus", 0)
        else:
            flat_base_damage_component = getattr(config, 'BAREHANDED_FLAT_DAMAGE', 1)
        
        damage_bonus_from_roll = max(0, (combat_roll_result - config.COMBAT_HIT_THRESHOLD) // config.COMBAT_DAMAGE_MODIFIER_DIVISOR)
        total_damage = max(1, flat_base_damage_component + damage_bonus_from_roll)
        results['damage'] = total_damage

        defender_player.hp -= total_damage
        
        # Attacker's hit confirmation
        results['attacker_message'] = {"text": f"  ...and HIT {defender_player.name} for {total_damage} damage!", "type": "combat_hit_player"}
        # Defender's message about being hit
        results['defender_message'] = {"text": f"{attacker_player.name} HITS you with their {weapon_name_for_msg} for {total_damage} damage! (HP: {defender_player.hp}/{defender_player.max_hp})", "type": "combat_hit_by_opponent"}
        broadcast_msg_text += f" and HITS for {total_damage} damage!"

        if defender_player.hp <= 0:
            results['defender_defeated'] = True
            defender_player.hp = 0 # Prevent negative HP display
            results['attacker_message'] = {"text": f"  You have DEFEATED {defender_player.name} in combat!", "type": "event_pvp_victory"} # Attacker's victory
            results['defender_message'] = {"text": f"You have been DEFEATED by {attacker_player.name}!", "type": "event_pvp_defeat_major"} # Defender's defeat
            broadcast_msg_text += f" {defender_player.name} has been defeated!"
            
            # Handle defender's "death"
            defender_player.current_room_id = getattr(config, 'PLAYER_DEATH_ROOM_ID', 1)
            defender_player.hp = 1 # Or a small fraction of max_hp
            # Player handler save will be called by main loop or disconnect logic
        else: # Defender wounded but not defeated
            results['attacker_message'] = {"text": f"  {defender_player.name} looks wounded. (Est. HP: {defender_player.hp}/{defender_player.max_hp})", "type": "combat_status_target"}
            broadcast_msg_text += f" {defender_player.name} is wounded."
    else: # Miss
        results['attacker_message'] = {"text": f"  ...but you MISS {defender_player.name}!", "type": "combat_miss_player"}
        results['defender_message'] = {"text": f"{attacker_player.name} attacks you with their {weapon_name_for_msg} but MISSES!", "type": "combat_miss_by_opponent"}
        broadcast_msg_text += " and MISSES!"
    
    results['broadcast_message'] = broadcast_msg_text
    attacker_player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
    attacker_player.add_message(f"Roundtime: {config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0):.1f} sec.", "system_info")
    return results


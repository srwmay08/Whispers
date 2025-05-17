# mud_project/game_logic/combat.py
import random
import time
import re 
import math # For math.floor if used

try:
    import config
    from classes import player as player_class 
    # GAME_ITEMS will be passed directly to handle_player_attack
except ImportError as e:
    # ... (your existing mock config, ensure it has DEFAULT_UNARMORED_TYPE, EQUIPMENT_SLOTS) ...
    pass

RUNTIME_ENTITY_HP = {} 
RECENTLY_DEFEATED_TARGETS_IN_ROOM = {}

def parse_and_roll_dice(dice_string):
    # ... (your existing function) ...
    if not isinstance(dice_string, str): return 0
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_string.lower())
    if not match:
        try: return int(dice_string)
        except ValueError: return 0
    num_dice, dice_sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    return sum(random.randint(1, dice_sides) for _ in range(num_dice)) + modifier

def get_stat_bonus(stat_value, baseline, divisor):
    if divisor == 0: return 0
    return (stat_value - baseline) // divisor # Integer division

def get_skill_bonus(skill_value, divisor):
    if divisor == 0: return 0
    return skill_value // divisor # Integer division

def get_entity_armor_type(entity_data_runtime, game_items_global):
    """
    Determines the primary armor type of an entity based on equipped torso armor.
    Args:
        entity_data_runtime (dict): The runtime data for the entity (NPC/Monster or Player object).
                                     For NPCs/Monsters, this is their dict from GAME_NPCS/GAME_MONSTER_TEMPLATES (after processing).
                                     For Players, this is the player object itself.
        game_items_global (dict): The global GAME_ITEMS dictionary.
    Returns:
        str: The armor type (e.g., "plate", "leather", "unarmored").
    """
    equipped_items_dict = {}
    if isinstance(entity_data_runtime, player_class.Player): # Check if it's a Player object
        equipped_items_dict = entity_data_runtime.equipped_items
    elif isinstance(entity_data_runtime, dict): # For NPC/Monster dicts
        equipped_items_dict = entity_data_runtime.get("equipped", {})
    
    # Determine the key for the torso slot from config
    # This assumes a simple string comparison. A more robust way is to iterate config.EQUIPMENT_SLOTS.items()
    # For simplicity, let's assume "torso" is the direct key used in config.EQUIPMENT_SLOTS for the torso.
    # If your config.EQUIPMENT_SLOTS uses descriptive values like "Torso Armor", you'd need to find the key.
    # Example: torso_slot_key = "torso" 
    torso_slot_key = next((key for key, val in config.EQUIPMENT_SLOTS.items() if "torso" in key.lower() or "chest" in key.lower()), "torso")


    chest_item_id = equipped_items_dict.get(torso_slot_key)
    if chest_item_id:
        chest_item_data = game_items_global.get(chest_item_id)
        if chest_item_data and chest_item_data.get("type") == "armor":
            return chest_item_data.get("armor_type", config.DEFAULT_UNARMORED_TYPE)
    
    # Fallback for entities that might have an innate armor type in their base template
    if isinstance(entity_data_runtime, dict):
        return entity_data_runtime.get("innate_armor_type", config.DEFAULT_UNARMORED_TYPE)
    return config.DEFAULT_UNARMORED_TYPE


def calculate_attack_strength(attacker_name, attacker_stats, attacker_skills, weapon_item_data, target_armor_type):
    # (Using the version from your last message, with attacker_name added)
    as_val = 0
    as_components = [] 
    weapon_name_display = "Barehanded"

    if not weapon_item_data or weapon_item_data.get("type") != "weapon":
        strength_barehanded = attacker_stats.get("strength", config.STAT_BONUS_BASELINE)
        str_bonus_barehanded = get_stat_bonus(strength_barehanded, config.STAT_BONUS_BASELINE, config.MELEE_AS_STAT_BONUS_DIVISOR)
        as_val += str_bonus_barehanded
        as_components.append(f"StrBonus({strength_barehanded} = {str_bonus_barehanded})")
        brawling_skill = attacker_skills.get("brawling", 0)
        brawling_bonus = get_skill_bonus(brawling_skill, config.WEAPON_SKILL_AS_BONUS_DIVISOR)
        as_val += brawling_bonus
        as_components.append(f"BrawlingSkill({brawling_skill} = {brawling_bonus})")
        base_barehanded_as = getattr(config, 'BAREHANDED_BASE_AS', 0)
        as_val += base_barehanded_as
        if base_barehanded_as != 0: as_components.append(f"BaseBarehandedAS({base_barehanded_as})")
    else:
        weapon_name_display = weapon_item_data.get("name", "Unknown Weapon")
        strength = attacker_stats.get("strength", config.STAT_BONUS_BASELINE)
        str_bonus = get_stat_bonus(strength, config.STAT_BONUS_BASELINE, config.MELEE_AS_STAT_BONUS_DIVISOR)
        as_val += str_bonus
        as_components.append(f"StrBonus({strength} = {str_bonus})")
        weapon_skill_name = weapon_item_data.get("skill")
        skill_bonus_val = 0
        if weapon_skill_name:
            skill_rank = attacker_skills.get(weapon_skill_name, 0)
            skill_bonus_val = get_skill_bonus(skill_rank, config.WEAPON_SKILL_AS_BONUS_DIVISOR)
            as_val += skill_bonus_val
            as_components.append(f"Skill({weapon_skill_name}:{skill_rank} = {skill_bonus_val})")
        else: as_components.append("Skill(None = 0)")
        weapon_base_as = weapon_item_data.get("weapon_as_bonus", 0)
        as_val += weapon_base_as
        as_components.append(f"WpnBaseAS({weapon_base_as})")
        enchant_as = weapon_item_data.get("enchantment_as_bonus", 0)
        as_val += enchant_as
        as_components.append(f"EnchantAS({enchant_as})")
        avd_mods = weapon_item_data.get("avd_modifiers", {})
        avd_bonus = avd_mods.get(target_armor_type, avd_mods.get(config.DEFAULT_UNARMORED_TYPE, 0))
        as_val += avd_bonus
        as_components.append(f"AvDMod({target_armor_type} = {avd_bonus})")

    as_components.append("CMBonus(TODO:0)") 
    as_components.append("StanceBonus(TODO:0)")
    
    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False):
        formula_str = " + ".join(as_components)
        print(f"DEBUG AS CALC for {attacker_name} (Weapon: {weapon_name_display}): Formula = {formula_str} => Final AS = {as_val}")
    return as_val

def calculate_defense_strength(defender_name, defender_stats, defender_skills, armor_item_data, shield_item_data, defender_stance=None):
    # (Using the version from your last message, with defender_name added)
    ds_val = 0
    ds_components = []
    armor_name_display = "Unarmored"; shield_name_display = "No Shield"
    base_ds_value = 0

    agility_stat = defender_stats.get("agility", config.STAT_BONUS_BASELINE)
    ds_stat_divisor = getattr(config, 'MELEE_DS_STAT_BONUS_DIVISOR', 10) 
    agi_bonus = get_stat_bonus(agility_stat, config.STAT_BONUS_BASELINE, ds_stat_divisor)
    base_ds_value += agi_bonus
    ds_components.append(f"AgiBonus({agility_stat} = {agi_bonus})")

    armor_ds_bonus = 0
    if armor_item_data and armor_item_data.get("type") == "armor":
        armor_ds_bonus = armor_item_data.get("armor_ds_bonus", 0)
        armor_name_display = armor_item_data.get("name", "Unknown Armor")
        base_ds_value += armor_ds_bonus
        ds_components.append(f"Armor({armor_name_display}:{armor_ds_bonus})")
    else:
        unarmored_ds = getattr(config, 'UNARMORED_BASE_DS', 0)
        base_ds_value += unarmored_ds
        ds_components.append(f"UnarmoredBase({unarmored_ds})")

    shield_base_bonus = 0; shield_skill_bonus = 0
    if shield_item_data and shield_item_data.get("type") == "shield":
        shield_base_bonus = shield_item_data.get("shield_ds_bonus", 0)
        shield_name_display = shield_item_data.get("name", "Unknown Shield")
        base_ds_value += shield_base_bonus
        ds_components.append(f"ShieldBase({shield_name_display}:{shield_base_bonus})")
        shield_skill_rank = defender_skills.get("shield_use", 0)
        shield_skill_divisor = getattr(config, 'SHIELD_SKILL_DS_BONUS_DIVISOR', 10)
        shield_skill_bonus = get_skill_bonus(shield_skill_rank, shield_skill_divisor)
        base_ds_value += shield_skill_bonus
        ds_components.append(f"ShieldSkill({shield_skill_rank} = {shield_skill_bonus})")
    else:
        ds_components.append("Shield(None = 0)")

    ds_components.append("DodgeSkill(TODO:0)")
    ds_components.append("StanceBonus(TODO:0)")
    ds_components.append("SpellDS(TODO:0)")
    ds_val = base_ds_value

    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False):
        formula_str = " + ".join(ds_components)
        print(f"DEBUG DS CALC for {defender_name if defender_name else 'entity'} (Armor: {armor_name_display}, Shield: {shield_name_display}): Formula = {formula_str} => Final DS = {ds_val}")
    return ds_val


def handle_player_attack(player: player_class.Player, target_data: dict, target_type: str, 
                         target_name_raw_from_player: str, game_items_global: dict, 
                         monster_instance_index: int | None = None):
    GAME_ITEMS = game_items_global # Make it available locally

    template_key = target_data.get("_id", target_data.get("key", "unknown_key"))
    target_display_name = target_data.get("name", "the creature")
    is_unique_template = target_data.get("is_unique", False)
    
    entity_runtime_id = ""
    if target_type == "npc":
        entity_runtime_id = template_key # NPCs often use their template key if unique or for simpler tracking
    elif target_type == "monster":
        if monster_runtime_id: # Prioritize the runtime_id passed from main.py
            entity_runtime_id = monster_runtime_id
        # Fallback if monster_runtime_id wasn't passed (should ideally always be passed from main.py now)
        elif not is_unique_template and monster_instance_index is not None:
            entity_runtime_id = f"{player.current_room_id}_{template_key}_{monster_instance_index}"
        else: # Fallback for unique monsters or if index is not applicable
            entity_runtime_id = template_key
    else: 
        entity_runtime_id = f"unknown_target_type_{template_key}" # Should not happen with current target types
    if config.DEBUG_MODE:
        print(f"DEBUG COMBAT: {player.name} attacking {target_display_name} (Type: {target_type}, TemplateKey: {template_key}). RuntimeID: {entity_runtime_id}. Player Input: '{target_name_raw_from_player}'")

    if RECENTLY_DEFEATED_TARGETS_IN_ROOM.get(entity_runtime_id):
        player.add_message(f"The {target_display_name} is already defeated!", "feedback")
        return {'hit': False, 'damage': 0, 'defeated': True, 'already_defeated': True, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    max_hp_from_template = target_data.get("max_hp", target_data.get("hp", 25))
    if entity_runtime_id not in RUNTIME_ENTITY_HP: RUNTIME_ENTITY_HP[entity_runtime_id] = max_hp_from_template
    current_hp = RUNTIME_ENTITY_HP[entity_runtime_id]

    if current_hp <= 0: 
        player.add_message(f"The {target_display_name} is already incapacitated!", "feedback")
        RECENTLY_DEFEATED_TARGETS_IN_ROOM[entity_runtime_id] = True # Mark as defeated
        return {'hit': False, 'damage': 0, 'defeated': True, 'already_defeated': True, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    # --- Attacker's Setup (Player) ---
    # Use the player's new method to get equipped item data
    attacker_weapon_data = player.get_equipped_item_data("mainhand", GAME_ITEMS)
    weapon_name_for_msg = attacker_weapon_data.get("name", "your fist") if attacker_weapon_data else "your fist"
    player.add_message(f"You swing {weapon_name_for_msg} at {target_name_raw_from_player}!", "combat_action_player")

    # --- Defender's Setup (NPC/Monster) ---
    # target_data is the runtime data which should now include an "equipped" dictionary
    target_equipped_dict = target_data.get("equipped", {})
    target_armor_type_str = get_entity_armor_type(target_data, GAME_ITEMS) # Pass runtime target_data
    
    target_armor_item_id = target_equipped_dict.get(next((k for k,v in config.EQUIPMENT_SLOTS.items() if "torso" in k.lower()), "torso"))
    target_armor_data = GAME_ITEMS.get(target_armor_item_id) if target_armor_item_id else None
    
    target_shield_item_id = target_equipped_dict.get(next((k for k,v in config.EQUIPMENT_SLOTS.items() if "offhand" in k.lower()), "offhand"))
    target_shield_data = GAME_ITEMS.get(target_shield_item_id) if target_shield_item_id else None
    
    # --- Calculate AS and DS ---
    attacker_as = calculate_attack_strength(player.name, player.stats, player.skills, attacker_weapon_data, target_armor_type_str)
    defender_ds = calculate_defense_strength(target_display_name, target_data.get("stats", {}), target_data.get("skills", {}), target_armor_data, target_shield_data, target_data.get("current_stance"))

    # --- Combat Roll ---
    d100_roll = random.randint(1, 100)
    combat_roll_result = (attacker_as - defender_ds) + config.COMBAT_ADVANTAGE_FACTOR + d100_roll
    
    if config.DEBUG_MODE and getattr(config, 'DEBUG_COMBAT_ROLLS', False): # Check flag
        combat_roll_message = f"Roll: AS({attacker_as}) - DS({defender_ds}) + AvD({config.COMBAT_ADVANTAGE_FACTOR}) + d100({d100_roll}) = {combat_roll_result}"
        player.add_message(combat_roll_message, "combat_roll_info_debug") # Use a distinct type for debug
    
    broadcast_msg_base = f"{player.name} attacks {target_display_name} with {weapon_name_for_msg}."
    combat_results_dict = {'hit': False, 'damage': 0, 'defeated': False, 'already_defeated': False, 'target_name': target_display_name, 'target_key': template_key, 'target_runtime_id': entity_runtime_id, 'broadcast_message': ""}

    if combat_roll_result > config.COMBAT_HIT_THRESHOLD:
        combat_results_dict['hit'] = True
        base_weapon_damage_roll = parse_and_roll_dice(attacker_weapon_data.get("damage", "1d1")) if attacker_weapon_data else parse_and_roll_dice("1d2")
        damage_bonus_from_roll = max(0, (combat_roll_result - config.COMBAT_HIT_THRESHOLD) // config.COMBAT_DAMAGE_MODIFIER_DIVISOR)
        total_damage = max(1, base_weapon_damage_roll + damage_bonus_from_roll)
        combat_results_dict['damage'] = total_damage
        player.add_message(f"You HIT {target_display_name} for {total_damage} damage!", "combat_hit_player") # Use target_display_name for consistency
        broadcast_msg_base += f" and HITS for {total_damage} damage!"
        
        current_hp -= total_damage
        RUNTIME_ENTITY_HP[entity_runtime_id] = current_hp

        if current_hp <= 0:
            player.add_message(f"{target_display_name} collapses, defeated!", "combat_defeat_player")
            broadcast_msg_base += f" {target_display_name} is DEFEATED!"
            combat_results_dict['defeated'] = True
            RECENTLY_DEFEATED_TARGETS_IN_ROOM[entity_runtime_id] = True # Mark as defeated
            if config.DEBUG_MODE: print(f"DEBUG COMBAT: {target_display_name} (RuntimeID: {entity_runtime_id}) DEFEATED by {player.name}. HP: {current_hp}/{max_hp_from_template}")
        else:
            player.add_message(f"{target_display_name} looks wounded. (Est. HP: {current_hp}/{max_hp_from_template})", "combat_status_target")
            broadcast_msg_base += f" {target_display_name} is wounded."
    else:
        player.add_message(f"You MISS {target_display_name}!", "combat_miss_player") # Use target_display_name
        broadcast_msg_base += " and MISSES!"

    combat_results_dict['broadcast_message'] = broadcast_msg_base
    # player.next_action_time = time.time() + getattr(config.ROUNDTIME_DEFAULTS, 'roundtime_attack', 3.0) # This was causing an error
    player.next_action_time = time.time() + config.ROUNDTIME_DEFAULTS.get('roundtime_attack', 3.0)
    return combat_results_dict

# ... (if __name__ == '__main__': block) ...

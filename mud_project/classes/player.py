# classes/player.py
import sys
import os
import math
import random

try:
    import config
except ImportError:
    class MockConfigForPlayer:
        DEBUG_MODE = True
        ALL_STATS_ORDERED = ["strength", "stamina", "dexterity", "agility", "constitution", "charisma", "intelligence", "wisdom", "logic", "perception", "aura", "willpower"]
        DEFAULT_START_ROOM_ID = 1; INITIAL_SKILLS = {"brawling": 1}; DEFAULT_STAT_VALUE = 10
        STAT_PRIMARY_BONUS_DIVISOR = 50; BASE_FIELD_XP_POOL_CAPACITY = 1000
        FIELD_XP_POOL_LOGIC_BONUS_MULTIPLIER = 50; MIND_STATUS_THRESHOLDS = []
        MIN_XP_ABSORBED_PER_EVENT = 1; XP_ABSORB_LOGIC_BONUS_CONTRIBUTION_DIVISOR_NODE_TOWN = 5
        XP_ABSORB_LOGIC_BONUS_CONTRIBUTION_DIVISOR_OTHER = 7; XP_ABSORB_POOL_SIZE_BONUS_PER_XP_AMOUNT = 200
        XP_ABSORB_POOL_SIZE_BONUS_POINT = 1; XP_ABSORB_POOL_SIZE_BONUS_MAX_POINTS = 10
        XP_ABSORB_SUPER_NODE_BONUS = 2; XP_ABSORB_GROUP_BONUS = 1
        XP_ABSORB_BASE_RATE_ON_NODE = 25; XP_ABSORB_BASE_RATE_IN_TOWN_OFF_NODE = 22
        XP_ABSORB_BASE_RATE_OTHER_AREAS = 19; EQUIPMENT_SLOTS = {"torso": "Torso", "mainhand": "Main Hand", "offhand": "Off Hand", "head": "Head"}
        DEFAULT_UNARMORED_TYPE = "unarmored"; MAX_INVENTORY_SIZE = 20
        HP_PER_CON_POINT = 2; HP_PER_PRIMARY_CON_BONUS = 25; HP_PER_LEVEL = 5
        TRAINING_POINTS_PER_LEVEL = 5
    config = MockConfigForPlayer()

class Player:
    def __init__(self, sid, name="Unnamed Character"):
        self.sid = sid
        self.name = name
        self._queued_messages = []
        self.creation_phase = None
        self.creation_data = {}
        self.pronouns = {}
        self.race = None # Stores the race key (e.g., "human")
        self.gold = 0


        self.stats = {stat_name: getattr(config, 'DEFAULT_STAT_VALUE', 10) for stat_name in getattr(config, 'ALL_STATS_ORDERED', [])}
        self.skills = getattr(config, 'INITIAL_SKILLS', {}).copy()
        
        self.inventory = [] 
        self.equipped_items = {slot_key: [] for slot_key in config.EQUIPMENT_SLOTS.keys()}
        
        self.current_room_id = getattr(config, 'DEFAULT_START_ROOM_ID', 1)
        self.hp = 0; self.max_hp = 0; self.mp = 0; self.max_mp = 0; self.sp = 0; self.max_sp = 0
        self.level = 1; self.xp = 0; self.unabsorbed_xp = 0
        self.factions = {}; self.last_mind_status = ""; self.next_action_time = 0
        self.is_in_group = False; self.db_id = None
        self.training_points = 0 # Initialize training points

        if config.DEBUG_MODE:
            print(f"DEBUG PLAYER ({self.name}, SID: {self.sid}): Initialized with {len(self.equipped_items)} equipment slots.")

    def add_message(self, text_or_payload, message_type="info"):
        if not hasattr(self, '_queued_messages') or self._queued_messages is None: self._queued_messages = []
        if isinstance(text_or_payload, dict):
            if 'type' not in text_or_payload and message_type: text_or_payload['type'] = message_type
            self._queued_messages.append(text_or_payload)
        else: self._queued_messages.append({"text": str(text_or_payload), "type": str(message_type)})

    def get_queued_messages(self):
        if not hasattr(self, '_queued_messages') or self._queued_messages is None: self._queued_messages = []; return []
        messages = list(self._queued_messages); self._queued_messages.clear(); return messages

    def calculate_derived_stats(self, game_races_data=None, game_items_data=None):
        """
        Calculates derived statistics like max_hp, max_mp, max_sp.
        Considers base stats, racial bonuses, level, and potentially bonuses from equipped items.
        """
        effective_stats = self.stats.copy() # Start with base stats

        # --- Apply Stat Bonuses from Equipped Items (Example) ---
        if game_items_data:
            for slot_key, item_id in self.equipped_items.items():
                if item_id:
                    item_data = game_items_data.get(item_id)
                    if item_data and isinstance(item_data.get("stat_bonuses"), dict):
                        for stat_aff, bonus_val in item_data["stat_bonuses"].items():
                            if stat_aff in effective_stats:
                                effective_stats[stat_aff] += bonus_val
                                if config.DEBUG_MODE:
                                    print(f"DEBUG PLAYER {self.name}: Item '{item_data.get('name')}' applied {bonus_val} to {stat_aff}. New effective: {effective_stats[stat_aff]}")
        # --- End Item Stat Bonuses ---

        base_con = effective_stats.get("constitution", 10)
        con_primary_bonus = 0
        if game_races_data and self.race:
            current_race_data = game_races_data.get(self.race)
            if current_race_data:
                con_primary_bonus_mod = current_race_data.get("constitution_primary_bonus_mod", 0)
                con_primary_bonus = (base_con // getattr(config, 'STAT_PRIMARY_BONUS_DIVISOR', 50)) + con_primary_bonus_mod
        
        base_hp_from_con = base_con * getattr(config, 'HP_PER_CON_POINT', 2)
        primary_bonus_hp = con_primary_bonus * getattr(config, 'HP_PER_PRIMARY_CON_BONUS', 25)
        level_bonus_hp = self.level * getattr(config, 'HP_PER_LEVEL', 5)
        self.max_hp = base_hp_from_con + primary_bonus_hp + level_bonus_hp
        
        # Example for Max MP (Intelligence based)
        base_int = effective_stats.get("intelligence", 10)
        int_primary_bonus = 0
        if game_races_data and self.race:
            current_race_data = game_races_data.get(self.race)
            if current_race_data:
                int_primary_bonus_mod = current_race_data.get("intelligence_primary_bonus_mod", 0) # Check your race_tables for this key
                int_primary_bonus = (base_int // getattr(config, 'STAT_PRIMARY_BONUS_DIVISOR', 50)) + int_primary_bonus_mod
        self.max_mp = (base_int * getattr(config, 'MP_PER_INT_POINT', 2)) + \
                      (int_primary_bonus * getattr(config, 'MP_PER_PRIMARY_CASTINGSTAT_BONUS', 15)) + \
                      (self.level * getattr(config, 'MP_PER_LEVEL', 3)) # Example values

        # Example for Max SP (Stamina based)
        base_sta = effective_stats.get("stamina", 10)
        sta_primary_bonus = 0
        if game_races_data and self.race:
            current_race_data = game_races_data.get(self.race)
            if current_race_data:
                sta_primary_bonus_mod = current_race_data.get("stamina_primary_bonus_mod", 0) # Check your race_tables
                sta_primary_bonus = (base_sta // getattr(config, 'STAT_PRIMARY_BONUS_DIVISOR', 50)) + sta_primary_bonus_mod
        self.max_sp = (base_sta * getattr(config, 'SP_PER_STA_POINT', 2)) + \
                      (sta_primary_bonus * getattr(config, 'SP_PER_PRIMARY_SPIRITSTAT_BONUS', 15)) + \
                      (self.level * getattr(config, 'SP_PER_LEVEL', 2)) # Example values


        if config.DEBUG_MODE:
            print(f"DEBUG PLAYER {self.name}: Derived Stats Calculated. MaxHP: {self.max_hp} (CON:{base_con}), MaxMP: {self.max_mp} (INT:{base_int}), MaxSP: {self.max_sp} (STA:{base_sta})")

    def calculate_training_points(self, game_races_data=None):
        base_points = self.level * getattr(config, 'TRAINING_POINTS_PER_LEVEL', 5)
        racial_bonus_tp = 0
        if game_races_data and self.race:
            current_race_data = game_races_data.get(self.race)
            if current_race_data: racial_bonus_tp = current_race_data.get("bonus_training_points", 0)
        self.training_points = getattr(self, 'training_points', 0) + base_points + racial_bonus_tp # Accumulate on level up
        if config.DEBUG_MODE: print(f"DEBUG PLAYER {self.name}: Training points calculated/updated: {self.training_points}")

    def get_stat_primary_bonus(self, stat_name: str, game_races_data=None):
        stat_value = self.stats.get(stat_name, 0)
        divisor = getattr(config, 'STAT_PRIMARY_BONUS_DIVISOR', 50)
        base_stat_contribution = stat_value // divisor if divisor > 0 else 0
        racial_modifier = 0
        if self.race and game_races_data:
            race_data = game_races_data.get(self.race)
            if race_data: racial_modifier = race_data.get(f"{stat_name}_primary_bonus_mod", 0)
        return base_stat_contribution + racial_modifier

    def get_field_xp_pool_capacity(self, game_races_data=None):
        base_capacity = getattr(config, 'BASE_FIELD_XP_POOL_CAPACITY', 1000)
        logic_bonus_multiplier = getattr(config, 'FIELD_XP_POOL_LOGIC_BONUS_MULTIPLIER', 50)
        logic_primary_bonus = self.get_stat_primary_bonus("logic", game_races_data)
        capacity = base_capacity + (logic_bonus_multiplier * logic_primary_bonus)
        return max(100, capacity)

    def get_xp_absorption_amount_per_event(self, current_room_data=None, game_races_data=None):
        # ... (Your existing detailed logic, ensure it uses self.get_stat_primary_bonus correctly) ...
        if current_room_data is None: current_room_data = {}
        base_rate = 0; logic_bonus_divisor = getattr(config, 'XP_ABSORB_LOGIC_BONUS_DIVISOR_OTHER', 7)
        is_node = current_room_data.get("is_node", False) or current_room_data.get("is_sanctuary", False)
        is_town = current_room_data.get("is_town", False)
        is_super = current_room_data.get("is_super_node", False)
        if is_node:
            base_rate = getattr(config, 'XP_ABSORB_BASE_RATE_ON_NODE', 25)
            logic_bonus_divisor = getattr(config, 'XP_ABSORB_LOGIC_BONUS_DIVISOR_NODE_TOWN', 5)
            if is_super: base_rate += getattr(config, 'XP_ABSORB_SUPER_NODE_BONUS', 2)
        elif is_town:
            base_rate = getattr(config, 'XP_ABSORB_BASE_RATE_IN_TOWN_OFF_NODE', 22)
            logic_bonus_divisor = getattr(config, 'XP_ABSORB_LOGIC_BONUS_DIVISOR_NODE_TOWN', 5)
        else: base_rate = getattr(config, 'XP_ABSORB_BASE_RATE_OTHER_AREAS', 19)
        logic_bonus = self.get_stat_primary_bonus("logic", game_races_data)
        logic_absorb_contrib = logic_bonus // logic_bonus_divisor if logic_bonus_divisor > 0 else 0
        pool_bonus = 0; unabsorbed = getattr(self, 'unabsorbed_xp', 0)
        bonus_per_amt = getattr(config, 'XP_ABSORB_POOL_SIZE_BONUS_PER_XP_AMOUNT', 200)
        pt_per_bonus = getattr(config, 'XP_ABSORB_POOL_SIZE_BONUS_POINT', 1)
        max_bonus_pts = getattr(config, 'XP_ABSORB_POOL_SIZE_BONUS_MAX_POINTS', 10)
        if bonus_per_amt > 0: pool_bonus = min(max_bonus_pts, (unabsorbed // bonus_per_amt) * pt_per_bonus)
        group_bonus = getattr(config, 'XP_ABSORB_GROUP_BONUS', 1) if getattr(self, 'is_in_group', False) else 0
        total_absorb = base_rate + logic_absorb_contrib + pool_bonus + group_bonus
        min_absorb = getattr(config, 'MIN_XP_ABSORBED_PER_EVENT', 1)
        final_amount = math.floor(total_absorb)
        # ... (Your debug print for this function) ...
        return max(min_absorb, final_amount)


    def get_current_mind_status(self, game_races_data=None):
        # ... (Your existing logic) ...
        capacity = self.get_field_xp_pool_capacity(game_races_data)
        current_unabsorbed_xp = getattr(self, 'unabsorbed_xp', 0)
        if capacity <= 0: return "Clear as a bell" if current_unabsorbed_xp == 0 else "Muddled"
        if current_unabsorbed_xp == 0: return "Clear as a bell"
        ratio = current_unabsorbed_xp / capacity
        thresholds = sorted(getattr(config, 'MIND_STATUS_THRESHOLDS', []), key=lambda x: x['threshold'], reverse=True)
        for status_info in thresholds:
            if status_info['phrase'] == "Clear as a bell" and ratio == 0.0 and status_info['threshold'] <= 0: return status_info['phrase']
            elif status_info['phrase'] != "Clear as a bell" and ratio >= status_info['threshold']: return status_info['phrase']
        # Fallback if no threshold met (should be caught by "Fresh and clear" or "Clear as a bell")
        return "Unknown Mind State"


    def _check_and_send_mind_status(self, game_races_data=None, force_send=False):
        if not hasattr(self, 'last_mind_status'): self.last_mind_status = ""
        current_status = self.get_current_mind_status(game_races_data)
        if current_status and (current_status != self.last_mind_status or force_send):
            self.add_message(f"Mind state: {current_status}.", "mind_status")
            self.last_mind_status = current_status

    def add_xp_to_pool(self, amount: int, game_races_data=None):
        # ... (Your existing logic) ...
        if amount <= 0: return
        capacity = self.get_field_xp_pool_capacity(game_races_data)
        current_unabsorbed = getattr(self, 'unabsorbed_xp', 0)
        space_available = capacity - current_unabsorbed
        amount_to_add = min(amount, max(0, space_available))
        if amount_to_add > 0:
            self.unabsorbed_xp += amount_to_add
            self.add_message(f"You gain {amount_to_add} experience (to be absorbed).", "xp_gain")
            if config.DEBUG_MODE: print(f"DEBUG PLAYER ({self.name}): Added {amount_to_add} XP to pool. Total pool: {self.unabsorbed_xp}/{capacity}")
        if amount_to_add < amount and amount > 0 :
            self.add_message("Your mind feels too full to absorb all of that experience right now.", "xp_pool_full")
        self._check_and_send_mind_status(game_races_data, force_send=(amount_to_add > 0))

    def get_faction_display_str(self, faction_display_names_config: dict) -> str:
        if not hasattr(self, 'factions') or not self.factions:
            return "You are not currently aligned with any factions."

        display_lines = ["--- Your Faction Standings ---"]
        for faction_id, standing in self.factions.items():
            display_name = faction_display_names_config.get(faction_id, faction_id.replace("_", " ").title())
            # You can add descriptive tiers based on standing value here
            # e.g., Hated, Disliked, Neutral, Liked, Honored
            standing_desc = "" # Placeholder for descriptive tier
            if standing <= -1000: standing_desc = " (Hated)"
            elif standing <= -100: standing_desc = " (Disliked)"
            elif standing < 100: standing_desc = " (Neutral)"
            elif standing < 1000: standing_desc = " (Liked)"
            else: standing_desc = " (Honored)"

            display_lines.append(f"{display_name}: {standing}{standing_desc}")

        if len(display_lines) == 1: # Only header was added
            return "You have no specific faction standings to display yet."
        return "\n".join(display_lines)

    def update_faction(self, faction_id: str, amount_change: int):
        # ... (Your existing logic) ...
        if not hasattr(self, 'factions') or not isinstance(self.factions, dict): self.factions = {}
        current_standing = self.factions.get(faction_id, 0)
        new_standing = current_standing + amount_change
        new_standing = max(getattr(config, 'MIN_FACTION_STANDING', -25000), min(getattr(config, 'MAX_FACTION_STANDING', 25000), new_standing))
        self.factions[faction_id] = new_standing
        display_faction_name_config = getattr(config, 'FACTION_DISPLAY_NAMES', {})
        display_faction_name = display_faction_name_config.get(faction_id, faction_id.replace("_", " ").title())
        if amount_change < 0: self.add_message(f"Your standing with {display_faction_name} has worsened.", "faction_update_negative")
        elif amount_change > 0: self.add_message(f"Your standing with {display_faction_name} has improved.", "faction_update_positive")
        if config.DEBUG_MODE: print(f"DEBUG PLAYER ({self.name}): Faction '{faction_id}' changed by {amount_change}. New standing: {new_standing}.")


    def equip_item(self, item_id_to_equip: str, target_slot_key: str, game_items_data: dict, game_races_data=None):
        if config.DEBUG_MODE: print(f"DEBUG EQUIP: Attempting to equip '{item_id_to_equip}' to slot '{target_slot_key}'")
        if item_id_to_equip not in self.inventory:
            self.add_message(f"You don't have '{game_items_data.get(item_id_to_equip, {}).get('name', item_id_to_equip)}' to equip.", "error")
            if config.DEBUG_MODE: print(f"DEBUG EQUIP: Fail - Not in inventory.")
            return False
        item_template = game_items_data.get(item_id_to_equip)
        if not item_template:
            self.add_message(f"Cannot find item data for '{item_id_to_equip}'.", "error_critical")
            if config.DEBUG_MODE: print(f"DEBUG EQUIP: Fail - No item template.")
            return False

        item_allowed_slots = item_template.get("slot", [])
        if not isinstance(item_allowed_slots, list): item_allowed_slots = [item_allowed_slots]
        if target_slot_key not in config.EQUIPMENT_SLOTS.keys(): # Check against actual slot keys
            self.add_message(f"Invalid equipment slot key: {target_slot_key}.", "error")
            if config.DEBUG_MODE: print(f"DEBUG EQUIP: Fail - Invalid target_slot_key '{target_slot_key}'.")
            return False

        actual_slot_name_for_msg = config.EQUIPMENT_SLOTS.get(target_slot_key, target_slot_key)
        if target_slot_key not in item_allowed_slots:
            self.add_message(f"The {item_template.get('name', 'item')} cannot be equipped to {actual_slot_name_for_msg}.", "error")
            if config.DEBUG_MODE: print(f"DEBUG EQUIP: Fail - Item cannot go in slot. Item slots: {item_allowed_slots}")
            return False

        currently_equipped_id = self.equipped_items.get(target_slot_key)
        if currently_equipped_id: self.unequip_item(target_slot_key, game_items_data, game_races_data, silent=True)

        is_two_handed_weapon = "twohand" in item_allowed_slots or item_template.get("is_two_handed", False)
        if is_two_handed_weapon:
            if target_slot_key == "mainhand" and self.equipped_items.get("offhand"):
                offhand_item_id = self.equipped_items["offhand"]
                self.add_message(f"Your {game_items_data.get(offhand_item_id,{}).get('name','offhand item')} is unequipped for the two-handed weapon.", "feedback")
                self.unequip_item("offhand", game_items_data, game_races_data, silent=True)
            # If trying to equip a two-hander to offhand, it implicitly means mainhand is also used by it.
            elif target_slot_key == "offhand" and self.equipped_items.get("mainhand"):
                 self.add_message(f"Your {game_items_data.get(self.equipped_items['mainhand'],{}).get('name','mainhand item')} is unequipped as this requires two hands.", "feedback")
                 self.unequip_item("mainhand", game_items_data, game_races_data, silent=True)
                 # If equipping a 2H to offhand, also occupy mainhand conceptually, or disallow. For now, assume it means "use both hands"
                 self.equipped_items["mainhand"] = item_id_to_equip # Also mark mainhand

        self.equipped_items[target_slot_key] = item_id_to_equip
        self.inventory.remove(item_id_to_equip)
        self.add_message(f"You equip the {item_template.get('name', 'item')} to your {actual_slot_name_for_msg}.", "feedback_equip")
        self.calculate_derived_stats(game_races_data, game_items_data)
        return True

    def unequip_item(self, slot_key_to_unequip: str, game_items_data: dict, game_races_data=None, silent=False):
        actual_slot_name_for_msg = config.EQUIPMENT_SLOTS.get(slot_key_to_unequip, slot_key_to_unequip)
        if slot_key_to_unequip not in self.equipped_items or self.equipped_items[slot_key_to_unequip] is None:
            if not silent: self.add_message(f"You have nothing equipped in your {actual_slot_name_for_msg}.", "error")
            return False
        item_id_unequipped = self.equipped_items[slot_key_to_unequip]
        item_template = game_items_data.get(item_id_unequipped)
        max_inv_size = getattr(config, 'MAX_INVENTORY_SIZE', 20)
        if len(self.inventory) >= max_inv_size:
            if not silent: self.add_message("Your inventory is full. Cannot unequip.", "error")
            return False
        self.inventory.append(item_id_unequipped)
        self.equipped_items[slot_key_to_unequip] = None
        # If it was a two-handed weapon, ensure both slots are cleared if one was a conceptual link
        if item_template and ("twohand" in item_template.get("slot", []) or item_template.get("is_two_handed")):
            if slot_key_to_unequip == "mainhand" and self.equipped_items.get("offhand") == item_id_unequipped:
                self.equipped_items["offhand"] = None
            elif slot_key_to_unequip == "offhand" and self.equipped_items.get("mainhand") == item_id_unequipped:
                self.equipped_items["mainhand"] = None

        if not silent: self.add_message(f"You unequip the {item_template.get('name', 'item') if item_template else 'item'} from your {actual_slot_name_for_msg}.", "feedback_unequip")
        self.calculate_derived_stats(game_races_data, game_items_data)
        return True
    
    def get_equipped_item_data(self, slot_key: str, game_items_data: dict):
        item_id = self.equipped_items.get(slot_key)
        return game_items_data.get(item_id) if item_id else None

    def get_armor_type(self, game_items_data: dict):
        torso_slot_key = next((key for key, val in config.EQUIPMENT_SLOTS.items() if "torso" in key.lower() or "chest" in key.lower()), "torso")
        torso_item_data = self.get_equipped_item_data(torso_slot_key, game_items_data)
        if torso_item_data and torso_item_data.get("type") == "armor":
            return torso_item_data.get("armor_type", config.DEFAULT_UNARMORED_TYPE)
        return config.DEFAULT_UNARMORED_TYPE

    def to_dict(self):
        return {"sid": self.sid, "name": self.name, "race": self.race, "pronouns": self.pronouns, "stats": self.stats, "skills": self.skills, "inventory": self.inventory, "equipped_items": self.equipped_items, "current_room_id": self.current_room_id, "hp": self.hp, "max_hp": self.max_hp, "mp": self.mp, "max_mp": self.max_mp, "sp": self.sp, "max_sp": self.max_sp, "level": self.level, "xp": self.xp, "creation_phase": self.creation_phase, "unabsorbed_xp": getattr(self, 'unabsorbed_xp', 0), "factions": getattr(self, 'factions', {}), "last_mind_status": getattr(self, 'last_mind_status', ""), "is_in_group": getattr(self, 'is_in_group', False), "training_points": getattr(self, 'training_points', 0)}

    @classmethod
    def from_dict(cls, data, sid_on_load=None, game_races_data=None, game_items_data=None): # Added game_items_data
        player = cls(sid_on_load if sid_on_load else data.get("sid", "restored_sid"), data.get("name", "Restored Character"))
        player.db_id = data.get("_id") # Store MongoDB _id
        player.race = data.get("race")
        player.pronouns = data.get("pronouns", {})
        loaded_stats = data.get("stats", {})
        for stat_key in config.ALL_STATS_ORDERED: player.stats[stat_key] = loaded_stats.get(stat_key, config.DEFAULT_STAT_VALUE)
        player.skills = data.get("skills", getattr(config, 'INITIAL_SKILLS', {}).copy())
        player.inventory = data.get("inventory", [])
        loaded_equipped = data.get("equipped_items", {})
        player.equipped_items = {slot_key: loaded_equipped.get(slot_key) for slot_key in config.EQUIPMENT_SLOTS.keys()}
        player.current_room_id = data.get("current_room_id", config.DEFAULT_START_ROOM_ID)
        player.max_hp = data.get("max_hp", 10); player.hp = data.get("hp", player.max_hp)
        player.max_mp = data.get("max_mp", 0); player.mp = data.get("mp", player.max_mp)
        player.max_sp = data.get("max_sp", 0); player.sp = data.get("sp", player.max_sp)
        player.level = data.get("level", 1); player.xp = data.get("xp", 0)
        player.unabsorbed_xp = data.get('unabsorbed_xp', 0)
        player.factions = data.get('factions', {})
        player.last_mind_status = data.get('last_mind_status', "")
        player.is_in_group = data.get('is_in_group', False)
        player.creation_phase = data.get("creation_phase")
        player.training_points = data.get("training_points", 0)
        
        # Crucial: Recalculate derived stats after all base attributes and equipment are loaded
        player.calculate_derived_stats(game_races_data, game_items_data) # Pass game_items_data
        
        # Ensure HP/MP/SP are not exceeding new max values after recalculation
        player.hp = min(player.hp, player.max_hp)
        player.mp = min(player.mp, player.max_mp)
        player.sp = min(player.sp, player.max_sp)

        if config.DEBUG_MODE: print(f"DEBUG PLAYER {player.name}: Loaded from dict. SID set to {player.sid}.")
        return player

    def get_client_data(self, game_races_data=None, game_items_data=None): # Added game_items_data
        race_display_name = self.race.title() if self.race else "Unknown"
        if game_races_data and self.race:
            race_data_entry = game_races_data.get(self.race)
            if race_data_entry: race_display_name = race_data_entry.get("name", self.race.title())
        
        equipped_display = {}
        if game_items_data:
            for slot_key, item_id in self.equipped_items.items():
                slot_display_name = config.EQUIPMENT_SLOTS.get(slot_key, slot_key) # Get descriptive name
                if item_id:
                    item_data = game_items_data.get(item_id)
                    equipped_display[slot_display_name] = item_data.get("name", item_id) if item_data else item_id
                else:
                    equipped_display[slot_display_name] = None # Or "Empty"
        
        return {
            "name": self.name, "race_key": self.race, "race_display_name": race_display_name,
            "hp": self.hp, "max_hp": self.max_hp, "mp": self.mp, "max_mp": self.max_mp,
            "sp": self.sp, "max_sp": self.max_sp, "level": self.level, "xp": self.xp,
            "unabsorbed_xp": getattr(self, 'unabsorbed_xp', 0),
            "stats": self.stats, 
            "inventory_count": len(self.inventory),
            "equipped_items_display": equipped_display,
            "current_room_id": self.current_room_id,
            "mind_status": self.get_current_mind_status(game_races_data)
        }

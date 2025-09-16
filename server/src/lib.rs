// server/src/lib.rs

use spacetimedb::{spacetimedb, ReducerContext, SpacetimeDB, Identity, Reducer, SpacetimeType};

// --- Game State Tables ---

#[spacetimedb(table)]
pub struct GameState {
    #[primarykey]
    pub id: u32, // Singleton table, always ID 0
    pub tick_count: u64,
    pub time_of_day: String,
    pub weather: String,
}

// --- Player and Component Tables ---

#[spacetimedb(table)]
pub struct Player {
    #[primarykey]
    pub identity: Identity,
    pub name: String,
    pub current_room_id: u32,
    pub hp: i32,
    pub max_hp: i32,
    // ... other core attributes
}

#[spacetimedb(table)]
pub struct PlayerStats {
    #[primarykey]
    pub player_identity: Identity,
    pub strength: u32,
    pub stamina: u32,
    // ... other stats
}

#[spacetimedb(table)]
pub struct PlayerInventory {
    #[primarykey]
    pub item_instance_id: u64,
    pub owner_identity: Identity,
    pub item_template_id: String,
}

// --- Game World Tables ---

#[spacetimedb(table)]
pub struct MonsterInstance {
    #[primarykey]
    pub instance_id: u64,
    pub template_id: String,
    pub room_id: u32,
    pub hp: i32,
    pub max_hp: i32,
}

#[spacetimedb(table)]
pub struct Room {
    #[primarykey]
    pub id: u32,
    pub name: String,
    pub description: String,
    // ... other room attributes
}

// --- Reducers (Game Logic) ---

#[spacetimedb(reducer)]
pub fn create_character(ctx: ReducerContext, name: String) -> Result<(), String> {
    // Logic from your character_creation.py
    Player::insert(Player {
        identity: ctx.sender,
        name,
        current_room_id: 1, // Starting room
        hp: 100,
        max_hp: 100,
    })?;

    PlayerStats::insert(PlayerStats {
        player_identity: ctx.sender,
        strength: 50,
        stamina: 50,
        // ... initial stats
    })?;

    Ok(())
}

#[spacetimedb(reducer)]
pub fn move_player(ctx: ReducerContext, direction: String) -> Result<(), String> {
    let player = Player::filter_by_identity(&ctx, ctx.sender).unwrap();
    let room = Room::filter_by_id(&ctx, player.current_room_id).unwrap();

    let new_room_id = match direction.as_str() {
        "north" => room.north_exit,
        "south" => room.south_exit,
        // ... handle all directions
        _ => return Err("Invalid direction".to_string()),
    };

    Player::update_by_identity(&ctx, ctx.sender, Player { current_room_id: new_room_id, ..player });
    Ok(())
}

#[spacetimedb(reducer)]
pub fn attack_monster(ctx: ReducerContext, monster_instance_id: u64) -> Result<(), String> {
    // This combines logic from your combat.py and loot_handler.py
    let player_stats = PlayerStats::filter_by_player_identity(&ctx, ctx.sender).unwrap();
    let monster = MonsterInstance::filter_by_instance_id(&ctx, monster_instance_id).unwrap();

    let damage = player_stats.strength / 2; // Simplified
    let new_hp = monster.hp - damage as i32;

    if new_hp <= 0 {
        // Monster is defeated, handle loot
        // (Simplified loot logic)
        PlayerInventory::insert(PlayerInventory {
            item_instance_id: ctx.timestamp, // Use timestamp for a unique ID
            owner_identity: ctx.sender,
            item_template_id: "rat_tail".to_string(),
        })?;
        MonsterInstance::delete_by_instance_id(&ctx, monster_instance_id);
    } else {
        MonsterInstance::update_by_instance_id(&ctx, monster_instance_id, MonsterInstance { hp: new_hp, ..monster });
    }

    Ok(())
}

#[spacetimedb(init)]
pub fn init() {
    // This runs once when the module is deployed
    GameState::insert(GameState {
        id: 0,
        tick_count: 0,
        time_of_day: "day".to_string(),
        weather: "clear".to_string(),
    }).unwrap();
}

#[spacetimedb(update)]
pub fn tick(_ctx: ReducerContext, _delta_time: f64) {
    // This runs on every tick of the game loop
    // It replaces your monster_respawn.py and environment.py logic
    let mut game_state = GameState::filter_by_id(&_ctx, 0).unwrap();
    game_state.tick_count += 1;

    // Simplified environment update
    if game_state.tick_count % 100 == 0 {
        game_state.time_of_day = "night".to_string();
    }

    GameState::update_by_id(&_ctx, 0, game_state);
}
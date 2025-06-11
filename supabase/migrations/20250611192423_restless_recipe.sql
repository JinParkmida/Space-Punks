/*
  # Star Trading RPG Database Schema

  1. New Tables
    - `players` - Core player data and statistics
    - `ships` - Player ship information and upgrades
    - `planets` - Game world locations with market data
    - `commodities` - Tradeable goods with base prices
    - `factions` - Player factions with bonuses
    - `market_prices` - Dynamic pricing system
    - `player_inventory` - Player cargo tracking
    - `achievements` - Achievement definitions
    - `player_achievements` - Player achievement progress
    - `faction_wars` - Weekly faction competition data
    - `trade_history` - Transaction logging
    - `jump_history` - Travel encounter logging

  2. Security
    - Enable RLS on all player-related tables
    - Add policies for authenticated users to access their own data
    - Public read access for game configuration tables

  3. Features
    - Dynamic market pricing system
    - Achievement tracking with progress
    - Faction bonuses and competition
    - Comprehensive player statistics
    - Transaction and travel history
*/

-- Core player data
CREATE TABLE IF NOT EXISTS players (
  user_id bigint PRIMARY KEY,
  username text NOT NULL,
  credits bigint DEFAULT 1000,
  fuel integer DEFAULT 100,
  current_planet text DEFAULT 'Terra Prime',
  faction_id integer DEFAULT NULL,
  total_trades integer DEFAULT 0,
  successful_jumps integer DEFAULT 0,
  total_jumps integer DEFAULT 0,
  net_worth bigint DEFAULT 1000,
  created_at timestamptz DEFAULT now(),
  last_active timestamptz DEFAULT now()
);

-- Player ships and upgrades
CREATE TABLE IF NOT EXISTS ships (
  user_id bigint PRIMARY KEY REFERENCES players(user_id) ON DELETE CASCADE,
  name text DEFAULT 'Starfarer',
  cargo_capacity integer DEFAULT 50,
  fuel_efficiency real DEFAULT 1.0,
  jump_success_bonus real DEFAULT 0.0,
  shield_strength integer DEFAULT 0,
  engine_speed integer DEFAULT 1,
  navigation_system integer DEFAULT 0,
  paint_job text DEFAULT 'Standard',
  total_upgrade_cost bigint DEFAULT 0
);

-- Game world planets
CREATE TABLE IF NOT EXISTS planets (
  name text PRIMARY KEY,
  danger_level integer NOT NULL CHECK (danger_level >= 1 AND danger_level <= 5),
  description text NOT NULL,
  market_modifier real DEFAULT 1.0,
  fuel_cost integer NOT NULL,
  special_bonus text DEFAULT NULL
);

-- Tradeable commodities
CREATE TABLE IF NOT EXISTS commodities (
  name text PRIMARY KEY,
  base_price integer NOT NULL,
  volatility real DEFAULT 0.1,
  description text NOT NULL
);

-- Player factions
CREATE TABLE IF NOT EXISTS factions (
  id serial PRIMARY KEY,
  name text UNIQUE NOT NULL,
  description text NOT NULL,
  trade_bonus real DEFAULT 0.0,
  jump_bonus real DEFAULT 0.0,
  fuel_bonus real DEFAULT 0.0,
  special_ability text DEFAULT NULL,
  member_count integer DEFAULT 0,
  total_contribution bigint DEFAULT 0
);

-- Dynamic market pricing
CREATE TABLE IF NOT EXISTS market_prices (
  planet text REFERENCES planets(name),
  commodity text REFERENCES commodities(name),
  current_price integer NOT NULL,
  supply_level integer DEFAULT 50 CHECK (supply_level >= 0 AND supply_level <= 100),
  demand_level integer DEFAULT 50 CHECK (demand_level >= 0 AND demand_level <= 100),
  last_updated timestamptz DEFAULT now(),
  PRIMARY KEY (planet, commodity)
);

-- Player inventory/cargo
CREATE TABLE IF NOT EXISTS player_inventory (
  user_id bigint REFERENCES players(user_id) ON DELETE CASCADE,
  commodity text REFERENCES commodities(name),
  quantity integer DEFAULT 0 CHECK (quantity >= 0),
  average_buy_price real DEFAULT 0,
  PRIMARY KEY (user_id, commodity)
);

-- Achievement definitions
CREATE TABLE IF NOT EXISTS achievements (
  id serial PRIMARY KEY,
  name text UNIQUE NOT NULL,
  description text NOT NULL,
  requirement_type text NOT NULL, -- 'credits', 'trades', 'jumps', 'net_worth', etc.
  requirement_value bigint NOT NULL,
  badge_emoji text DEFAULT '🏆',
  reward_credits integer DEFAULT 0
);

-- Player achievement progress
CREATE TABLE IF NOT EXISTS player_achievements (
  user_id bigint REFERENCES players(user_id) ON DELETE CASCADE,
  achievement_id integer REFERENCES achievements(id),
  unlocked_at timestamptz DEFAULT now(),
  PRIMARY KEY (user_id, achievement_id)
);

-- Weekly faction wars
CREATE TABLE IF NOT EXISTS faction_wars (
  id serial PRIMARY KEY,
  week_start date NOT NULL,
  week_end date NOT NULL,
  winning_faction_id integer REFERENCES factions(id),
  total_participants integer DEFAULT 0,
  is_active boolean DEFAULT true
);

-- Trade transaction history
CREATE TABLE IF NOT EXISTS trade_history (
  id serial PRIMARY KEY,
  user_id bigint REFERENCES players(user_id) ON DELETE CASCADE,
  planet text REFERENCES planets(name),
  commodity text REFERENCES commodities(name),
  action text NOT NULL CHECK (action IN ('buy', 'sell')),
  quantity integer NOT NULL,
  price_per_unit integer NOT NULL,
  total_value bigint NOT NULL,
  profit_loss bigint DEFAULT 0,
  timestamp timestamptz DEFAULT now()
);

-- Jump/travel encounter history
CREATE TABLE IF NOT EXISTS jump_history (
  id serial PRIMARY KEY,
  user_id bigint REFERENCES players(user_id) ON DELETE CASCADE,
  from_planet text REFERENCES planets(name),
  to_planet text REFERENCES planets(name),
  encounter_type text NOT NULL,
  encounter_result text NOT NULL,
  credits_gained bigint DEFAULT 0,
  fuel_cost integer NOT NULL,
  success boolean NOT NULL,
  timestamp timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE ships ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE jump_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for player data
CREATE POLICY "Players can manage own data"
  ON players
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "Ships can manage own data"
  ON ships
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "Inventory can manage own data"
  ON player_inventory
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "Achievements can manage own data"
  ON player_achievements
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "Trade history can manage own data"
  ON trade_history
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "Jump history can manage own data"
  ON jump_history
  FOR ALL
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::bigint);

-- Public read access for game configuration
CREATE POLICY "Public read planets"
  ON planets FOR SELECT TO authenticated USING (true);

CREATE POLICY "Public read commodities"
  ON commodities FOR SELECT TO authenticated USING (true);

CREATE POLICY "Public read factions"
  ON factions FOR SELECT TO authenticated USING (true);

CREATE POLICY "Public read market prices"
  ON market_prices FOR SELECT TO authenticated USING (true);

CREATE POLICY "Public read achievements"
  ON achievements FOR SELECT TO authenticated USING (true);

CREATE POLICY "Public read faction wars"
  ON faction_wars FOR SELECT TO authenticated USING (true);

-- Insert initial game data
INSERT INTO planets (name, danger_level, description, market_modifier, fuel_cost, special_bonus) VALUES
('Terra Prime', 1, 'The safe capital world with stable markets', 1.0, 10, 'Safe Haven'),
('New Shanghai', 2, 'Industrial hub with tech manufacturing', 1.1, 15, 'Tech Bonus'),
('Kepler Station', 2, 'Mining colony rich in ore deposits', 1.1, 15, 'Ore Bonus'),
('Spice Gardens', 3, 'Agricultural world famous for exotic spices', 1.2, 20, 'Spice Bonus'),
('Luxury Resort', 3, 'High-end destination for luxury goods', 1.2, 20, 'Luxury Bonus'),
('Frontier Post', 4, 'Dangerous border world with high rewards', 1.4, 30, 'High Risk/Reward'),
('Pirate Haven', 4, 'Lawless system with black market deals', 1.4, 30, 'Black Market'),
('Unknown Space', 5, 'Mysterious region with extreme dangers and rewards', 1.6, 40, 'Extreme Risk/Reward');

INSERT INTO commodities (name, base_price, volatility, description) VALUES
('Ore', 100, 0.15, 'Essential minerals for construction and manufacturing'),
('Spice', 200, 0.20, 'Exotic seasonings and medicinal compounds'),
('Tech', 500, 0.25, 'Advanced technology and electronic components'),
('Luxuries', 800, 0.30, 'High-end goods for wealthy consumers');

INSERT INTO factions (id, name, description, trade_bonus, jump_bonus, fuel_bonus, special_ability) VALUES
(1, 'Pilots League', 'Elite pilots focused on safe travel and exploration', 0.0, 0.15, 0.10, 'Enhanced navigation systems'),
(2, 'Merchant Cartel', 'Trade-focused organization maximizing profits', 0.20, 0.0, 0.0, 'Market price predictions'),
(3, 'Smuggler Syndicate', 'Risk-takers who thrive in dangerous situations', 0.10, 0.10, 0.05, 'Black market access'),
(4, 'Peacekeepers', 'Balanced faction maintaining galactic order', 0.05, 0.05, 0.05, 'Diplomatic immunity');

INSERT INTO achievements (name, description, requirement_type, requirement_value, badge_emoji, reward_credits) VALUES
('First Steps', 'Complete your first trade', 'trades', 1, '👶', 100),
('Space Legs', 'Make your first interstellar jump', 'jumps', 1, '🚀', 100),
('Trader', 'Complete 10 successful trades', 'trades', 10, '💼', 500),
('Explorer', 'Visit 5 different planets', 'planets_visited', 5, '🌍', 500),
('Wealthy', 'Accumulate 10,000 credits', 'credits', 10000, '💰', 1000),
('Faction Member', 'Join a faction', 'faction_joined', 1, '🏛️', 200),
('Veteran Trader', 'Complete 100 trades', 'trades', 100, '📈', 2000),
('Millionaire', 'Reach 1,000,000 credits net worth', 'net_worth', 1000000, '💎', 10000),
('Daredevil', 'Successfully jump to Unknown Space', 'dangerous_jumps', 1, '⚡', 1500),
('Faction Champion', 'Contribute 100,000 credits to faction wars', 'faction_contribution', 100000, '👑', 5000);

-- Initialize market prices for all planet-commodity combinations
INSERT INTO market_prices (planet, commodity, current_price, supply_level, demand_level)
SELECT 
  p.name as planet,
  c.name as commodity,
  FLOOR(c.base_price * p.market_modifier * (0.8 + random() * 0.4)) as current_price,
  FLOOR(30 + random() * 40) as supply_level,
  FLOOR(30 + random() * 40) as demand_level
FROM planets p
CROSS JOIN commodities c;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_players_faction ON players(faction_id);
CREATE INDEX IF NOT EXISTS idx_market_prices_planet ON market_prices(planet);
CREATE INDEX IF NOT EXISTS idx_trade_history_user ON trade_history(user_id);
CREATE INDEX IF NOT EXISTS idx_jump_history_user ON jump_history(user_id);
CREATE INDEX IF NOT EXISTS idx_player_inventory_user ON player_inventory(user_id);
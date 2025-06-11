# StarTradingBot - Multiplayer Star-Trading RPG

A Discord bot that functions as a multiplayer star-trading RPG where every chat command feels like a high-stakes space venture.

## Features

### Galactic Market Trading
- `!market scan` shows real-time prices on four core commodities (Ore, Spice, Tech, Luxuries)
- Prices shift every hour based on randomized "sector events" and player activity

### Interstellar Jumps & Random Encounters
- `!jump <planet>` consumes fuel and credits, then rolls for encounters
- Six encounter types: pirate ambush, cosmic storm, hidden cache, merchant convoy, derelict salvage, peaceful dock

### Ship Upgrades & Customization
- Earn "Bolts" (in-game currency) to buy upgrades via `!buy <upgrade>`
- Larger cargo bays, faster engines, enhanced shields, cosmetic paint jobs
- Upgrades affect success chances and cargo capacity

### Factions & Guild Wars
- Join one of four factions with `!join <faction>`
- Pilots' League, Merchant Cartel, Smuggler Syndicate, Peacekeepers
- Weekly "Fleet Skirmishes" with faction-wide bonuses

### Leaderboards & Achievements
- `!leaderboard` ranks top traders by net worth, jump success rate, faction contributions
- Collect achievements for profile badges

### Dynamic Events & Seasonal Campaigns
- Monthly story arcs with limited-time missions
- Special "Comeback Missions" for lapsed players

## Setup

1. Install dependencies: `poetry install` or `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your bot token and database credentials
3. Set up PostgreSQL database
4. Run the bot: `python main.py`

## Database Setup

The bot requires a PostgreSQL database. Create the necessary tables using the SQL scripts in the `database/` directory (to be created).

## Contributing

This is a complete rewrite focused on the star-trading RPG concept. The old game systems have been removed and replaced with space trading mechanics.
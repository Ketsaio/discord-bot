# 🤖 Discord Bot

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Library](https://img.shields.io/badge/discord.py-2.0%2B-purple)
![Database](https://img.shields.io/badge/MongoDB-Ready-green)
![Music](https://img.shields.io/badge/Lavalink-Music-red)
![License](https://img.shields.io/badge/license-MIT-orange)
![Status](https://img.shields.io/badge/status-Stable-green)

A robust, modular Discord bot written in Python using `discord.py`, `MongoDB` and `LavaLink`. Focused on moderation, economy, ticket systems, and fun features.

## ✨ Features

- **Economy System:** Balance check, shop, and currency management.
- **Ticket System:** Button-based support tickets with transcript options.
- **Dynamic Views:** Interactive buttons and menus (Persistent Views).
- **Database Integration:** Persistent data storage using MongoDB (async).
- **Admin Tools:** Sync commands globally or locally for testing via `/sync`.

## 🚀 Roadmap

- [x] Auto Moderation
- [x] Economy System (Basic)
- [x] Gambling Mini-games
- [x] Global Leveling System
- [x] Pet System
- [x] Advanced Logging
- [x] Music Player

## 🛠️ Installation & Setup

### Prerequisites
- Python **3.12** or higher
- [MongoDB](https://www.mongodb.com/) (Local or Atlas) installed and running
- [Lavalink](https://github.com/lavalink-devs/Lavalink) Server (Required for Music)
- A Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))

### Step-by-Step Guide

1. **Clone the repository:**
	```bash
   git clone [https://github.com/Ketsaio/discord-bot.git](https://github.com/Ketsaio/discord-bot.git)
   cd discord-bot
	```

2. **Create a virtual environment (Recommended):**
    #### Windows
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
	```
    #### Linux/macOS
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
	```

3. **Install libraries:**
	```bash
    pip install -r requirements.txt
	```
4. **Configuration (.env):**
    Create a file named .env in the root directory and fill in your details:
   	```env
	  DISCORD_TOKEN=your_discord_bot_token_here
	  MONGO_URL=mongodb://localhost:27017/
	  DEV_ID=your_discord_user_id
	  TENOR = your_tenor_api_token_here
	  LAVALINK_CLIENT = your_lavalink_password_here
      ```
5. **Run the bot:**
	```bash
	python3 main.py
	```
## 🤝 Contributing & Credits
  This project was created by Ketsaio.
  If you use this code for your own bot, please leave a reference to the original author!

## 📄 License
  This project is licensed under the MIT License - see the LICENSE file for details.
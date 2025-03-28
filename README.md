# Telegram Slave Bot

A Telegram bot that allows users to participate in a virtual "slave" game, where they can collect and upgrade slaves, earn income, and compete on the leaderboard.

## Features

- User profile with balance and stats
- Referral system for collecting "slaves"
- Economy system with earnings from your slaves
- Upgrade mechanics to increase income
- Leaderboard with top users
- Admin commands for managing the bot

## Setup

1. Clone this repository
```bash
git clone https://github.com/l1v0n1/slavery-bot-telegram.git
cd telegram-slave-bot
```

2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure your bot
   - Create a `config.ini` file based on this template:
```ini
[main]
token = YOUR_TELEGRAM_BOT_TOKEN
mongourl = mongodb://localhost:27017/slaves
admin = YOUR_TELEGRAM_USER_ID
```

5. Set up MongoDB
   - Make sure MongoDB is installed and running on your machine
   - The bot will automatically create the required database and collections

6. Start the bot
```bash
python bot.py
```

## Requirements

- Python 3.7+
- MongoDB
- Required Python packages (see requirements.txt)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
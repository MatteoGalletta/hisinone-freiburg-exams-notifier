AI is scary. Vibe-coded in half an hour.

# Uni-Freiburg HISinOne Exam Notifier

Automatic exam structure checker for HISinOne Freiburg portal with Telegram notifications.

## Features

- ✅ Automatic login and session management
- 📊 Exam structure extraction with grades
- 🔔 Telegram notifications on changes
- 💾 JSON caching for change detection
- 🔄 Detects added/removed exams and grade changes

## Setup

### 1. Install Dependencies

```bash
pip install requests beautifulsoup4
```

### 2. Configure Credentials

1. Copy the example config file:
   ```bash
   cp config.example.json config.json
   ```

2. Edit `config.json` with your credentials:
   ```json
   {
     "hisinone": {
       "username": "YOUR_USERNAME",
       "password": "YOUR_PASSWORD"
     },
     "telegram": {
       "bot_token": "YOUR_BOT_TOKEN",
       "chat_id": "YOUR_CHAT_ID"
     }
   }
   ```

#### Getting Telegram Bot Token and Chat ID

1. **Create a bot**: Message [@BotFather](https://t.me/BotFather) on Telegram and send `/newbot`
2. **Get Chat ID**: 
   - Send a message to your bot
   - Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
   - Find the `"chat":{"id":NUMBER}` field

### 3. Run

```bash
python check_exams.py
```

## Files

- `check_exams.py` - Main script
- `config.json` - Your credentials (ignored by Git)
- `config.example.json` - Template for configuration
- `exams_structure.json` - Cached exam data (auto-generated)
- `.gitignore` - Git ignore rules

## How It Works

1. Logs into HISinOne portal
2. Extracts exam tree structure with grades
3. Compares with previous run (cached in JSON)
4. Sends Telegram notification if changes detected
5. Saves current structure for next comparison

## Automation

Set up a cron job to run automatically:

```bash
# Run every 10 minutes
*/10 * * * * cd /path/to/hisinone-check-update && python check_exams.py
```

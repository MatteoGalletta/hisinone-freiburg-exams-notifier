AI is scary. Vibe-coded in half an hour.

# Uni-Freiburg HISinOne Exam Notifier

Automatic exam structure checker for HISinOne Freiburg portal with Telegram notifications.

## Features

- ✅ Automatic login and session management
- 📊 Exam structure extraction with grades
- 🔔 Telegram notifications on changes
- 💾 JSON caching for change detection
- 🔄 Detects added/removed exams and grade changes
- 🤖 Interactive Telegram bot with commands
- ⏰ Automatic periodic checks every 10 minutes (bot mode)
- 📱 On-demand exam tree fetching via `/fetch` command

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

The script supports two modes of operation:

#### Check Mode (Default)
Checks for changes, saves data, and sends notifications:
```bash
python check_exams.py
# or explicitly:
python check_exams.py check
```

#### Bot Mode
Starts an interactive Telegram bot that listens for commands **and automatically checks for exam updates every 10 minutes**:
```bash
python check_exams.py bot
```

**Important**: The bot only responds to the user specified in `config.json` (chat_id). Other users will receive an "unauthorized" message.

**Automatic Checks**: The bot performs periodic exam checks every 10 minutes and sends notifications if changes are detected. This means you don't need a separate cron job when running in bot mode.

Once the bot is running, you can interact with it via Telegram:
- `/start` - Welcome message with available commands
- `/help` - Show help and available commands
- `/fetch` - Fetch and display current exam structure on-demand

## Files

- `check_exams.py` - Main script with CLI and bot functionality
- `config.json` - Your credentials (ignored by Git)
- `config.example.json` - Template for configuration
- `exams_structure.json` - Cached exam data (auto-generated)
- `last_update_id.json` - Bot state for message tracking (auto-generated)
- `.gitignore` - Git ignore rules

## How It Works

### Check Mode (Default)
1. Logs into HISinOne portal
2. Extracts exam tree structure with grades
3. Compares with previous run (cached in JSON)
4. Saves current structure to `exams_structure.json`
5. Sends Telegram notification if changes detected

### Bot Mode
1. Starts a Telegram bot that listens for incoming messages
2. Verifies user authorization (only configured chat_id can use the bot)
3. Responds to user commands in real-time
4. **Automatically checks for exam updates every 10 minutes**
5. Compares with cached data and sends notifications if changes are detected
6. Each `/fetch` command triggers an immediate on-demand data fetch

## Telegram Bot Usage

The bot mode enables both interactive queries and automatic monitoring via Telegram. This is useful for:
- 📱 Checking exam status on-the-go with commands
- 🔒 Secure access (only authorized user can interact)
- 🔄 Getting fresh data without server access
- ⏰ Automatic periodic checks every 10 minutes (no cron job needed)
- 🔔 Instant notifications when changes are detected

**Security Note**: The bot only responds to the chat_id configured in `config.json`. Any other user attempting to interact with the bot will receive an "unauthorized" message.

### Running the Bot

```bash
# Start the bot (it will run continuously)
python check_exams.py bot
```

The bot will stay active and respond to commands. Press `Ctrl+C` to stop.

### Available Bot Commands

- `/start` - Welcome message and command list
- `/help` - Show available commands
- `/fetch` - Fetch and display current exam structure

### Running Bot as a Service

For continuous operation, set up the bot as a systemd service:

1. **Create a systemd service file**:
   ```bash
   sudo nano /etc/systemd/system/hisinone-bot.service
   ```

2. **Add the following configuration** (adjust paths as needed):
   ```ini
   [Unit]
   Description=HISinOne Exam Notifier Bot
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USERNAME
   WorkingDirectory=/path/to/hisinone-check-update
   ExecStart=/usr/bin/python3 /path/to/hisinone-check-update/check_exams.py bot
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hisinone-bot.service
   sudo systemctl start hisinone-bot.service
   ```

4. **Check service status**:
   ```bash
   sudo systemctl status hisinone-bot.service
   ```

5. **View logs**:
   ```bash
   sudo journalctl -u hisinone-bot.service -f
   ```

## Automation

### Option 1: Bot Mode (Recommended)

**The bot mode already includes automatic checks every 10 minutes**, so if you're running the bot as a systemd service, you don't need a separate cron job.

Set up the bot as a systemd service (see "Running Bot as a Service" section above):
```bash
sudo systemctl enable hisinone-bot.service
sudo systemctl start hisinone-bot.service
```

This gives you **both**:
- ⏰ Automatic exam checks every 10 minutes with notifications
- 💬 Interactive Telegram commands for on-demand queries

### Option 2: Check Mode Only (Cron Job)

If you only want automatic checks without the interactive bot functionality, use check mode with a cron job:

```bash
# Add to crontab
crontab -e

# Run every 10 minutes
*/10 * * * * cd /path/to/hisinone-check-update && python3 check_exams.py check
```

**Note**: With this option, you won't be able to use interactive commands like `/fetch`.

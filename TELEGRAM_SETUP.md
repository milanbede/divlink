# Telegram Bot Setup Guide

This guide explains how to set up the Telegram bot feature for Divine Link.

## Prerequisites

1. **Create a Telegram Bot**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command and follow the prompts
   - Save the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Set Environment Variable**
   - Add your bot token to `.env` file:
   ```
   TELEGRAM_BOT_TOKEN="your-bot-token-here"
   ```

## Local Development

For local development, you can test the bot without webhooks by temporarily using polling (not included in this implementation but can be added).

## Cloud Run Deployment

### 1. Deploy to Cloud Run
Deploy your app to Google Cloud Run as usual. Make sure the `TELEGRAM_BOT_TOKEN` environment variable is set in Cloud Run.

### 2. Set Up Webhook
After deployment, use the setup script to configure the webhook:

```bash
python setup_telegram_bot.py
```

Choose option 1 and enter your Cloud Run URL (e.g., `https://your-app.run.app`).

### 3. Alternative: Manual Webhook Setup
You can also set the webhook manually using cURL:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://your-app.run.app/telegram/webhook"}'
```

## Testing the Bot

1. Find your bot on Telegram using the username you gave it
2. Send `/start` to begin
3. Try asking spiritual questions like:
   - "I'm feeling anxious about the future"
   - "How should I forgive someone?"
   - "I need strength for difficult times"
4. Use `/psalm` for a random powerful Psalm

## Bot Features

### Commands
- `/start` - Welcome message and instructions
- `/help` - Show help and examples
- `/psalm` - Get a random Psalm
- Any other text - Treated as a spiritual question

### Special Features
- **Idle Timer**: If no activity for 60 seconds, automatically sends a Psalm
- **Bible Links**: Verse references become clickable links to BibleGateway
- **Typing Indicators**: Shows "typing..." while processing
- **Perfect Score Highlighting**: Special formatting for highly relevant responses
- **Divine Name Emphasis**: LORD and GOD are emphasized with bold formatting

## Troubleshooting

### Check Webhook Status
```bash
python setup_telegram_bot.py
```
Choose option 2 to see webhook information.

### Common Issues

1. **Bot not responding**
   - Check webhook is set correctly
   - Verify `TELEGRAM_BOT_TOKEN` in environment
   - Check Cloud Run logs for errors

2. **"Telegram bot not configured" error**
   - Ensure `TELEGRAM_BOT_TOKEN` is set in Cloud Run environment variables
   - Redeploy after adding the token

3. **Webhook errors**
   - Ensure your Cloud Run service is publicly accessible
   - Webhook URL must use HTTPS
   - Check Cloud Run service logs for webhook processing errors

### Remove Webhook (for testing)
To remove the webhook (e.g., for local development):
```bash
python setup_telegram_bot.py
```
Choose option 3.

## Architecture Notes

- **Stateless Design**: Compatible with Cloud Run's serverless architecture
- **Session Management**: User sessions tracked in memory (consider Redis for production)
- **Webhook-based**: More efficient than polling for serverless deployment
- **Async Processing**: Uses asyncio for handling Telegram API calls
- **Shared Components**: Reuses existing LLM and Bible parsing logic

## Security Considerations

- Bot token is stored in environment variables
- Webhook endpoint validates incoming updates
- No user data is permanently stored
- All external API calls are logged

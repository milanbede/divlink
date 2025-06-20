#!/usr/bin/env python3
"""
Script to set up Telegram bot webhook for Cloud Run deployment
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def setup_telegram_webhook():
    """Set up Telegram bot webhook"""

    # Get configuration
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print("Please add your bot token to the .env file:")
        print('TELEGRAM_BOT_TOKEN="your-bot-token-here"')
        return False

    # Get webhook URL from user
    webhook_url = input(
        "Enter your Cloud Run webhook URL (e.g., https://your-app.run.app/telegram/webhook): "
    )
    if not webhook_url:
        print("❌ Webhook URL is required")
        return False

    # Ensure webhook URL ends with /telegram/webhook
    if not webhook_url.endswith("/telegram/webhook"):
        if webhook_url.endswith("/"):
            webhook_url += "telegram/webhook"
        else:
            webhook_url += "/telegram/webhook"

    print(f"🔧 Setting webhook to: {webhook_url}")

    # Set webhook using Telegram Bot API
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": webhook_url, "allowed_updates": ["message", "callback_query"]}

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            print("✅ Webhook set successfully!")
            print(f"📍 Webhook URL: {webhook_url}")

            # Get webhook info to verify
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            info_response = requests.get(info_url)
            if info_response.ok:
                info_data = info_response.json()
                if info_data.get("ok"):
                    webhook_info = info_data["result"]
                    print("📊 Webhook Status:")
                    print(f"   URL: {webhook_info.get('url', 'Not set')}")
                    print(
                        f"   Pending updates: {webhook_info.get('pending_update_count', 0)}"
                    )
                    if webhook_info.get("last_error_message"):
                        print(f"   Last error: {webhook_info['last_error_message']}")

            return True
        else:
            print(
                f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error setting webhook: {e}")
        return False


def remove_webhook():
    """Remove webhook (useful for local development)"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False

    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"

    try:
        response = requests.post(api_url)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            print("✅ Webhook removed successfully!")
            return True
        else:
            print(
                f"❌ Failed to remove webhook: {result.get('description', 'Unknown error')}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error removing webhook: {e}")
        return False


def get_webhook_info():
    """Get current webhook information"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False

    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    try:
        response = requests.get(api_url)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            webhook_info = result["result"]
            print("📊 Current Webhook Information:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(
                f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}"
            )
            print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(
                f"   Max connections: {webhook_info.get('max_connections', 'Not set')}"
            )

            if webhook_info.get("last_error_date"):
                print(f"   Last error date: {webhook_info['last_error_date']}")
            if webhook_info.get("last_error_message"):
                print(f"   Last error: {webhook_info['last_error_message']}")

            return True
        else:
            print(
                f"❌ Failed to get webhook info: {result.get('description', 'Unknown error')}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting webhook info: {e}")
        return False


def main():
    """Main function"""
    print("🤖 Telegram Bot Setup Script")
    print("=" * 40)

    while True:
        print("\nChoose an option:")
        print("1. Set webhook URL")
        print("2. Get webhook info")
        print("3. Remove webhook")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            setup_telegram_webhook()
        elif choice == "2":
            get_webhook_info()
        elif choice == "3":
            remove_webhook()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()

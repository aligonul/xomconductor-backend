#!/usr/bin/env python3
"""
Slack Connection Test Script for XomConductor

Run this script to verify your Slack credentials are working
before deploying the full backend.

Usage:
    python test_slack_connection.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def check_env_vars():
    """Check that required environment variables are set."""
    print("\n🔍 Checking environment variables...\n")

    required = {
        "SLACK_BOT_TOKEN": "Bot token (starts with xoxb-)",
        "SLACK_APP_TOKEN": "App token for Socket Mode (starts with xapp-)",
        "ALI_SLACK_CHANNEL_ID": "Your private channel ID (starts with C)",
    }

    optional = {
        "ANTHROPIC_API_KEY": "Claude API key (starts with sk-ant-)",
    }

    missing = []
    invalid = []

    for var, desc in required.items():
        value = os.environ.get(var)
        if not value:
            missing.append(f"  ❌ {var} - {desc}")
        else:
            prefix = value[:5] if len(value) > 5 else value
            print(f"  ✅ {var} = {prefix}...")

            # Validate prefixes
            if var == "SLACK_BOT_TOKEN" and not value.startswith("xoxb-"):
                invalid.append(f"  ⚠️  {var} should start with 'xoxb-', got '{prefix}'")
            elif var == "SLACK_APP_TOKEN" and not value.startswith("xapp-"):
                invalid.append(f"  ⚠️  {var} should start with 'xapp-', got '{prefix}'")
            elif var == "ALI_SLACK_CHANNEL_ID" and not value.startswith("C"):
                invalid.append(f"  ⚠️  {var} should start with 'C', got '{prefix}'")

    print()
    for var, desc in optional.items():
        value = os.environ.get(var)
        if value:
            prefix = value[:7] if len(value) > 7 else value
            print(f"  ✅ {var} = {prefix}... (optional)")
        else:
            print(f"  ⏭️  {var} not set (optional)")

    if missing:
        print("\n❌ Missing required variables:")
        for m in missing:
            print(m)
        return False

    if invalid:
        print("\n⚠️  Potentially invalid values:")
        for i in invalid:
            print(i)

    print("\n✅ All required environment variables are set!")
    return True


def test_bot_token():
    """Test the bot token using auth.test."""
    print("\n🔍 Testing Slack Bot Token...\n")

    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        print("  ❌ slack_sdk not installed. Run: pip install slack-sdk")
        return False

    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

    try:
        response = client.auth_test()
        print(f"  ✅ Bot authenticated successfully!")
        print(f"     Team: {response['team']}")
        print(f"     Bot User: {response['user']}")
        print(f"     Bot ID: {response['user_id']}")
        return True
    except SlackApiError as e:
        print(f"  ❌ Authentication failed: {e.response['error']}")
        if e.response['error'] == 'invalid_auth':
            print("     → Your bot token is invalid. Generate a new one in OAuth & Permissions.")
        return False


def test_channel_access():
    """Test that the bot can access the target channel."""
    print("\n🔍 Testing Channel Access...\n")

    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel_id = os.environ.get("ALI_SLACK_CHANNEL_ID")

    try:
        response = client.conversations_info(channel=channel_id)
        channel = response['channel']
        print(f"  ✅ Channel found: #{channel.get('name', channel_id)}")
        print(f"     Is Private: {channel.get('is_private', False)}")
        return True
    except SlackApiError as e:
        if e.response['error'] == 'channel_not_found':
            print(f"  ❌ Channel {channel_id} not found")
            print("     → Make sure the bot is invited to this channel")
            print("     → Right-click channel → 'View channel details' → Integrations → Add your bot")
        else:
            print(f"  ❌ Error: {e.response['error']}")
        return False


def test_post_message():
    """Test posting a message to the channel."""
    print("\n🔍 Testing Message Post...\n")

    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    channel_id = os.environ.get("ALI_SLACK_CHANNEL_ID")

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text="🧪 *XomConductor Test* - Slack connection verified!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🧪 *XomConductor Connection Test*\n\nYour Slack integration is working correctly!"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "This is a test message. You can delete it."
                        }
                    ]
                }
            ]
        )
        print(f"  ✅ Message posted successfully!")
        print(f"     Message timestamp: {response['ts']}")
        return True
    except SlackApiError as e:
        print(f"  ❌ Failed to post message: {e.response['error']}")
        if e.response['error'] == 'not_in_channel':
            print("     → Bot is not in the channel. Invite it first!")
        elif e.response['error'] == 'channel_not_found':
            print("     → Channel ID is incorrect or bot doesn't have access")
        return False


def test_socket_mode():
    """Test Socket Mode connection."""
    print("\n🔍 Testing Socket Mode...\n")

    try:
        from slack_sdk.socket_mode import SocketModeClient
        from slack_sdk import WebClient
    except ImportError:
        print("  ❌ slack_sdk not installed. Run: pip install slack-sdk")
        return False

    app_token = os.environ.get("SLACK_APP_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    try:
        client = SocketModeClient(
            app_token=app_token,
            web_client=WebClient(token=bot_token)
        )
        client.connect()
        print("  ✅ Socket Mode connection successful!")
        client.disconnect()
        return True
    except Exception as e:
        print(f"  ❌ Socket Mode connection failed: {str(e)}")
        print("     → Make sure Socket Mode is enabled in your Slack app settings")
        print("     → Generate an App-Level Token with 'connections:write' scope")
        return False


def main():
    print("=" * 50)
    print("  XomConductor Slack Connection Test")
    print("=" * 50)

    # Step 1: Check env vars
    if not check_env_vars():
        print("\n⛔ Fix the missing environment variables and try again.")
        print("   Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    # Step 2: Test bot token
    if not test_bot_token():
        print("\n⛔ Bot token test failed. Check your SLACK_BOT_TOKEN.")
        sys.exit(1)

    # Step 3: Test channel access
    if not test_channel_access():
        print("\n⚠️  Channel access failed, but continuing...")

    # Step 4: Ask about posting test message
    response = input("\n📝 Send a test message to your channel? (y/N): ").strip().lower()
    if response == 'y':
        if not test_post_message():
            print("\n⚠️  Message post failed.")

    # Step 5: Test Socket Mode
    response = input("\n🔌 Test Socket Mode connection? (y/N): ").strip().lower()
    if response == 'y':
        test_socket_mode()

    print("\n" + "=" * 50)
    print("  ✅ Connection tests complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. If all tests passed, run: python main.py")
    print("  2. Trigger from your Chrome extension")
    print("  3. Check your Slack channel for the draft message")
    print()


if __name__ == "__main__":
    main()

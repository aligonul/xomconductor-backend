#!/usr/bin/env python3
"""Test Slack connection and permissions."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_env_vars():
    """Check that all required environment variables are set."""
    required = {
        "SLACK_BOT_TOKEN": "xoxb-",
        "SLACK_APP_TOKEN": "xapp-",
        "ALI_SLACK_CHANNEL_ID": "C",
    }

    missing = []
    invalid = []

    for var, prefix in required.items():
        value = os.getenv(var)
        if not value:
            missing.append(var)
        elif not value.startswith(prefix):
            invalid.append(f"{var} should start with '{prefix}', got '{value[:10]}...'")

    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your values")
        return False

    if invalid:
        print("Invalid environment variables:")
        for msg in invalid:
            print(f"  - {msg}")
        return False

    print("All required environment variables are set")
    return True


def test_slack_connection():
    """Test connection to Slack using Socket Mode."""
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    # Test auth
    try:
        auth = client.auth_test()
        print(f"Connected as: {auth['user']} (bot_id: {auth['bot_id']})")
        print(f"Workspace: {auth['team']}")
    except SlackApiError as e:
        print(f"Auth failed: {e.response['error']}")
        return False

    # Test channel access
    channel_id = os.getenv("ALI_SLACK_CHANNEL_ID")
    try:
        info = client.conversations_info(channel=channel_id)
        channel_name = info["channel"]["name"]
        print(f"Channel access OK: #{channel_name} ({channel_id})")
    except SlackApiError as e:
        error = e.response["error"]
        if error == "channel_not_found":
            print(f"Channel {channel_id} not found. Make sure the bot is added to the channel.")
        elif error == "not_in_channel":
            print(f"Bot is not in channel {channel_id}. Add the bot via channel settings > Integrations > Add apps")
        else:
            print(f"Channel access failed: {error}")
        return False

    return True


def test_socket_mode():
    """Test Socket Mode connection."""
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.socket_mode.request import SocketModeRequest

    app_token = os.getenv("SLACK_APP_TOKEN")
    bot_token = os.getenv("SLACK_BOT_TOKEN")

    print("Testing Socket Mode connection...")

    try:
        client = SocketModeClient(
            app_token=app_token,
            web_client=__import__("slack_sdk").WebClient(token=bot_token)
        )
        client.connect()
        print("Socket Mode connection OK")
        client.close()
        return True
    except Exception as e:
        print(f"Socket Mode connection failed: {e}")
        print("Make sure Socket Mode is enabled in your app settings")
        return False


def test_send_message():
    """Send a test message to the channel."""
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    channel_id = os.getenv("ALI_SLACK_CHANNEL_ID")

    try:
        result = client.chat_postMessage(
            channel=channel_id,
            text="XomConductor connection test successful!"
        )
        print(f"Test message sent (ts: {result['ts']})")
        return True
    except SlackApiError as e:
        print(f"Failed to send message: {e.response['error']}")
        return False


def main():
    print("=" * 50)
    print("XomConductor Slack Connection Test")
    print("=" * 50)
    print()

    # Step 1: Check env vars
    print("[1/4] Checking environment variables...")
    if not check_env_vars():
        sys.exit(1)
    print()

    # Step 2: Test Slack connection
    print("[2/4] Testing Slack API connection...")
    if not test_slack_connection():
        sys.exit(1)
    print()

    # Step 3: Test Socket Mode
    print("[3/4] Testing Socket Mode...")
    if not test_socket_mode():
        sys.exit(1)
    print()

    # Step 4: Send test message
    print("[4/4] Sending test message...")
    if not test_send_message():
        sys.exit(1)
    print()

    print("=" * 50)
    print("All tests passed! Your Slack integration is ready.")
    print("=" * 50)


if __name__ == "__main__":
    main()

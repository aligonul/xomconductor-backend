"""Configuration management."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    slack_bot_token: str
    slack_app_token: str
    slack_channel_id: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
            slack_app_token=os.environ["SLACK_APP_TOKEN"],
            slack_channel_id=os.environ["ALI_SLACK_CHANNEL_ID"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        )


config = Config.from_env() if os.getenv("SLACK_BOT_TOKEN") else None

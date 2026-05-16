"""Main Slack Bolt application."""

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import config
from .handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> App:
    """Create and configure the Slack Bolt app."""
    app = App(token=config.slack_bot_token)
    register_handlers(app)
    return app


def main():
    """Run the bot in Socket Mode."""
    app = create_app()
    handler = SocketModeHandler(app, config.slack_app_token)

    logger.info("Starting XomConductor bot in Socket Mode...")
    logger.info(f"Posting to channel: {config.slack_channel_id}")

    handler.start()


if __name__ == "__main__":
    main()

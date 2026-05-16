import threading
import logging
from app import run_flask
from bolt_app import start_bolt_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main entry point that runs both Flask and Slack Bolt concurrently.

    - Flask runs in a background thread for HTTP endpoints
    - Slack Bolt runs in the main thread for Socket Mode
    """
    logger.info("Starting XomConductor Backend...")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server started in background thread")

    start_bolt_app()


if __name__ == "__main__":
    main()

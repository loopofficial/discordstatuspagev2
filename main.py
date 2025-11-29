#!/usr/bin/env python3
import logging
import sys
from config import load_config
from bot import create_bot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        logger.info("Loading configuration...")
        config = load_config()
        logger.info("Starting Discord Service Monitor Bot...")
        bot = create_bot(config)
        bot.run(config.discord.token, log_handler=None)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Helios Trading Bot - Main Entry Point

This script orchestrates the entire lifecycle of the trading bot, including:
- Loading configuration
- Initializing services (database, Redis, etc.)
- Starting the market data pipeline
- Graceful shutdown of all components
"""

import asyncio
import logging

from src.core.config import load_configuration
from src.data.connection_managers import close_connections
from src.data.market_data_pipeline import MarketDataPipeline
from src.utils.logging import setup_logging


async def main() -> None:
    """Main execution function for the Helios Trading Bot."""
    # 1. Load configuration and setup logging
    config = load_configuration()
    # Initialize logging with full configuration (includes log level)
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting Helios Trading Bot...")

    pipeline = None
    try:
        # 2. Initialize and start the market data pipeline (handles DB/schema/conn setup)
        pipeline = MarketDataPipeline()
        await (
            pipeline.initialize()
        )  # Note: This will now use the globally managed connections

        logger.info("✅ Pipeline initialized. Starting real-time data stream.")
        # In a real application, this would run indefinitely.
        # For this example, we'll just run it for a short period.
        # You would replace this with the main trading loop.
        await pipeline.start_realtime_pipeline()

    except asyncio.CancelledError:
        logger.info("Bot shutdown requested.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        logger.info("🔌 Shutting down bot...")
        if pipeline and pipeline.is_running:
            await pipeline.stop_pipeline()

        # 4. Close all connections
        await close_connections()
        logger.info("✅ Bot has been shut down gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown signal received from keyboard.")

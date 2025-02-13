#!/usr/bin/env python
# scripts/run_discovery.py

import argparse
import json
import logging
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
import queue
import sys
import os
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.parse

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import OperationalError
import psutil
from sqlalchemy import text

from src.clients.semantic_scholar import SemanticScholarClient
from src.clients.gpt import GPTClient
from src.database.manager import DatabaseManager
from src.services.paper_discovery import PaperDiscoveryService
from src.config.settings import settings


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[38;5;46m"

    def __init__(self, fmt, error_fmt):
        super().__init__()
        self.fmt = fmt
        self.error_fmt = error_fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.error_fmt + self.reset,
            logging.ERROR: self.red + self.error_fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset,
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.fmt)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class GracefulKiller:
    """Handle graceful shutdown on SIGINT/SIGTERM"""

    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def setup_logging(log_level: str) -> logging.Logger:
    """Set up logging to both file and console"""

    def info_filter(record):
        return record.levelno in (logging.INFO, logging.WARNING)

    # Create logger
    logger = logging.getLogger()

    # Only setup handlers if they haven't been set up already
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level.upper()))

        # Create formatters
        save_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        formatter = CustomFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            error_fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]",
        )

        suffix = "%Y-%m-%d_%H"

        # Setup queue for thread-safe logging
        log_queue = queue.Queue()
        queue_handler = QueueHandler(log_queue)

        # Create handlers
        # Handler for INFO and above logs
        info_handler = TimedRotatingFileHandler(
            "logs/info.log", when="H", interval=1, backupCount=168
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(save_formatter)
        info_handler.suffix = suffix
        info_handler.addFilter(info_filter)

        # Handler for ERROR logs
        error_handler = TimedRotatingFileHandler(
            "logs/error.log", when="H", interval=1, backupCount=336
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(save_formatter)
        error_handler.suffix = suffix

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Add all handlers
        logger.addHandler(queue_handler)
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)

        # Setup queue listener
        listener = QueueListener(
            log_queue, info_handler, error_handler, console_handler
        )
        listener.start()

    return logger


def create_neon_engine(url: str) -> Engine:
    """Create SQLAlchemy engine with Neon DB configuration"""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params.update(
        {
            "sslmode": ["require"],
            "connect_timeout": ["10"],
            "application_name": ["paper_discovery"],
        }
    )

    new_url = urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urllib.parse.urlencode(query_params, doseq=True),
            parsed.fragment,
        )
    )

    return create_engine(
        new_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


def test_database_connection(engine: Engine) -> bool:
    """Test database connection and verify it's working"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as e:
        logging.error(f"Database connection failed: {str(e)}")
        return False


def validate_api_keys() -> bool:
    """Validate that required API keys are set"""
    required_keys = {"OPENAI_API_KEY": settings.OPENAI_API_KEY}

    missing_keys = [key for key, value in required_keys.items() if not value]

    if missing_keys:
        logging.error(f"Missing required API keys: {', '.join(missing_keys)}")
        return False
    return True


def load_additional_topics(file_path: Optional[str]) -> list:
    """Load additional topics from JSON file if specified"""
    if not file_path:
        return []

    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load topics file: {str(e)}")
        return []


def init_clients(engine: Engine) -> Dict[str, Any]:
    """Initialize API clients and database manager"""
    semantic_scholar = SemanticScholarClient()

    gpt = GPTClient(api_key=settings.OPENAI_API_KEY, model=settings.GPT_MODEL)

    db = DatabaseManager(settings.DATABASE_URL)

    return {"semantic_scholar": semantic_scholar, "gpt": gpt, "db": db}


def monitor_resources():
    """Monitor system resource usage"""
    process = psutil.Process()
    memory_used = process.memory_info().rss / 1024 / 1024  # MB
    cpu_percent = process.cpu_percent()
    logging.info(f"Memory usage: {memory_used:.2f} MB, CPU usage: {cpu_percent}%")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run paper discovery process")

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check database connection and exit",
    )

    parser.add_argument(
        "--topics-file",
        type=str,
        help="Path to JSON file containing additional search topics",
    )

    parser.add_argument(
        "--max-papers",
        type=int,
        default=settings.MAX_PAPERS_PER_SEARCH,
        help="Maximum papers to process per search",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=settings.MAX_REFERENCE_DEPTH,
        help="Maximum reference depth to traverse",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.LOG_LEVEL,
        help="Logging level",
    )

    parser.add_argument(
        "--filter-papers",
        action="store_true",
        help="Filter existing papers based on PhD research support",
    )

    parser.add_argument(
        "--support-threshold",
        type=float,
        default=6.0,  # Changed default threshold to 6.0 for 0-10 scale
        help="Minimum support level threshold for paper filtering (0-10)",
    )

    parser.add_argument(
        "--enrich-papers",
        action="store_true",
        help="Enrich existing papers with additional metadata"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point"""
    args = parse_args()
    start_time = time.time()

    # Set up logging
    logger = setup_logging(args.log_level)
    logger.info("Starting paper discovery process...")

    # Create graceful shutdown handler
    killer = GracefulKiller()

    try:
        # Validate API keys
        if not validate_api_keys():
            logger.error("Missing required API keys")
            sys.exit(1)

        # Create database engine
        logger.info("Connecting to database...")
        engine = create_neon_engine(settings.DATABASE_URL)

        # Test database connection
        if not test_database_connection(engine):
            logger.error("Failed to connect to database")
            sys.exit(1)

        if args.check_only:
            logger.info("Database connection check successful")
            sys.exit(0)

        # Initialize clients
        logger.info("Initializing API clients...")
        clients = init_clients(engine)

        if args.filter_papers:
            from src.services.paper_filter import PaperFilterService

            logger.info("Starting paper filtering process...")

            filter_service = PaperFilterService(
                gpt_client=clients["gpt"],
                db_manager=clients["db"],
                support_threshold=args.support_threshold,
            )

            stats = filter_service.filter_papers()

            logger.info("\nPaper Filtering Complete")
            logger.info("=" * 40)
            logger.info(f"Papers processed: {stats['processed']}")
            logger.info(f"Papers filtered out: {stats['filtered_out']}")
            logger.info(f"Errors encountered: {stats['errors']}")

            sys.exit(0)

        if args.enrich_papers:
            from src.services.paper_enrichment import PaperEnrichmentService
            
            logger.info("Starting paper enrichment process...")
            
            enrichment_service = PaperEnrichmentService(
                semantic_scholar_client=clients["semantic_scholar"],
                db_manager=clients["db"],
                support_threshold=args.support_threshold
            )
            
            stats = enrichment_service.enrich_papers()
            
            logger.info("\nPaper Enrichment Complete")
            logger.info("=" * 40)
            logger.info(f"Papers processed: {stats['processed']}")
            logger.info(f"Papers enriched: {stats['enriched']}")
            logger.info(f"Errors encountered: {stats['errors']}")
            
            sys.exit(0)

        # Load topics
        topics = list(settings.SEARCH_TOPICS)
        if args.topics_file:
            logger.info(f"Loading additional topics from {args.topics_file}")
            additional_topics = load_additional_topics(args.topics_file)
            topics.extend(additional_topics)

        logger.info(f"Loaded {len(topics)} topics for processing")

        # Create discovery service
        discovery_service = PaperDiscoveryService(
            semantic_scholar_client=clients["semantic_scholar"],
            gpt_client=clients["gpt"],
            db_manager=clients["db"],
            max_papers_per_search=args.max_papers,
            max_reference_depth=args.max_depth,
        )

        # Run discovery process with monitoring
        logger.info("Starting paper discovery...")
        total_papers = 0
        last_monitor_time = time.time()
        monitor_interval = 300  # Monitor every 5 minutes

        try:
            for i, topic in enumerate(topics, 1):
                if killer.kill_now:
                    logger.info("Received shutdown signal, stopping gracefully...")
                    break

                logger.info(f"Processing topic {i}/{len(topics)}: {topic}")

                # Process topic
                discovery_service.discover_papers([topic])
                total_papers = len(discovery_service.processed_papers)

                # Periodic resource monitoring
                current_time = time.time()
                if current_time - last_monitor_time >= monitor_interval:
                    monitor_resources()
                    last_monitor_time = current_time

                logger.info(f"Processed {total_papers} papers so far")

        except KeyboardInterrupt:
            logger.info("Interrupted by user, stopping gracefully...")
        except Exception as e:
            logger.error(f"Error during paper discovery: {str(e)}", exc_info=True)
            raise

        # Print final statistics
        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info("\nPaper Discovery Process Complete")
        logger.info("=" * 40)
        logger.info(f"Total runtime: {elapsed_time/3600:.2f} hours")
        logger.info(f"Total papers processed: {total_papers}")
        logger.info(f"Topics processed: {i}/{len(topics)}")

        # Final resource usage
        monitor_resources()

    except Exception as e:
        logger.error(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info("Paper discovery process completed successfully")


if __name__ == "__main__":
    main()

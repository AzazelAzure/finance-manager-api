import os
import sys
from pathlib import Path
from loguru import logger


def logging_config():
    """
    Configure Loguru with file sinks per log level and a console sink.

    File locations and log level can be overridden via environment variables:
      DEBUG_LOG_PATH, INFO_LOG_PATH, WARN_LOG_PATH, ERR_LOG_PATH, CRIT_LOG_PATH, LOG_LEVEL
    """
    # Remove any existing handlers so configuration is idempotent
    logger.remove()

    # Use the current entrypoint (e.g. manage.py) as the base log filename
    script_name = Path(sys.argv[0]).stem

    # logs/ directory lives one level above this app (backend root)
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    default_log = logs_dir / f"{script_name}.log"

    config = {
        "DEBUG": os.getenv("DEBUG_LOG_PATH", default_log),
        "INFO": os.getenv("INFO_LOG_PATH", default_log),
        "WARNING": os.getenv("WARN_LOG_PATH", default_log),
        "ERROR": os.getenv("ERR_LOG_PATH", default_log),
        "CRITICAL": os.getenv("CRIT_LOG_PATH", default_log),
    }

    base_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )


    if os.getenv("DEBUG", "false").lower() == "true":
        logger.add(sys.stderr, format=base_fmt, level=os.getenv("LOG_LEVEL", "INFO"))


    logger.add(
        config["DEBUG"],
        rotation="10 MB",
        level="DEBUG",
        filter=lambda record: record["level"].name == "DEBUG",
        format=base_fmt,
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        config["INFO"],
        rotation="5 MB",
        level="INFO",
        filter=lambda record: record["level"].name == "INFO",
        format=base_fmt,
    )

    logger.add(
        config["WARNING"],
        rotation="5 MB",
        level="WARNING",
        filter=lambda record: record["level"].name == "WARNING",
        format=base_fmt,
    )

    logger.add(
        config["ERROR"],
        rotation="10 MB",
        level="ERROR",
        filter=lambda record: record["level"].name == "ERROR",
        format=base_fmt,
        backtrace=True,
    )

    logger.add(
        config["CRITICAL"],
        rotation="10 MB",
        level="CRITICAL",
        filter=lambda record: record["level"].name == "CRITICAL",
        format=base_fmt,
        backtrace=True,
        diagnose=True,
    )

    return logger


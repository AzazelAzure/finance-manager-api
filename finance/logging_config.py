import os
import sys
from pathlib import Path
from loguru import logger

def logging_config():
    """
    Configures the Loguru logger with distinct sinks per level.
    Returns the configured logger instance.
    """
    # 1. Clear default handlers to prevent duplicate printing
    logger.remove()

    # 2. Determine Paths
    # Current script name (e.g., 'accountant') used for default filename
    script_name = Path(sys.argv[0]).stem
    
    # Define root relative to this file's location
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parent 
    logs_dir = root_dir / "logs"
    
    # Ensure logs directory exists (Safety Check)
    logs_dir.mkdir(exist_ok=True)

    default_log = logs_dir / f"{script_name}.log"

    # 3. Load Environment Variables (with Default Fallbacks)
    config = {
        "DEBUG": os.getenv("DEBUG_LOG_PATH", default_log),
        "INFO": os.getenv("INFO_LOG_PATH", default_log),
        "WARNING": os.getenv("WARN_LOG_PATH", default_log),
        "ERROR": os.getenv("ERR_LOG_PATH", default_log),
        "CRITICAL": os.getenv("CRIT_LOG_PATH", default_log),
    }

    # 4. Define Common Format (Don't repeat yourself)
    # Note fixed time format: HH:mm:ss
    base_fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # 5. Add Standard Error (Terminal Output)
    # Default to INFO so DEBUG noise doesn't flood the terminal
    logger.add(sys.stderr, format=base_fmt, level=os.getenv("LOG_LEVEL", "INFO"))

    # 6. Add Sinks via Loop (Cleaner than 5 repeating blocks)
    # This maintains the logic: "If env not set, all go to default_log"
    
    # DEBUG
    logger.add(
        config["DEBUG"],
        rotation="10 MB",
        level="DEBUG",
        filter=lambda record: record["level"].name == "DEBUG",
        format=base_fmt,
        backtrace=True,
        diagnose=True
    )

    # INFO
    logger.add(
        config["INFO"],
        rotation="5 MB",
        level="INFO",
        filter=lambda record: record["level"].name == "INFO",
        format=base_fmt
    )

    # WARNING
    logger.add(
        config["WARNING"],
        rotation="5 MB",
        level="WARNING",
        filter=lambda record: record["level"].name == "WARNING",
        format=base_fmt
    )

    # ERROR
    logger.add(
        config["ERROR"],
        rotation="10 MB",
        level="ERROR",
        filter=lambda record: record["level"].name == "ERROR",
        format=base_fmt,
        backtrace=True
    )

    # CRITICAL
    logger.add(
        config["CRITICAL"],
        rotation="10 MB",
        level="CRITICAL",
        filter=lambda record: record["level"].name == "CRITICAL",
        format=base_fmt,
        backtrace=True,
        diagnose=True # Diagnosis on critical failure is vital
    )

    return logger
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
    import loguru._file_sink
    from loguru._file_sink import FileSink

    original_write = FileSink.write

    def custom_write(self, message):
        record = message.record
        uid = record["extra"].get("uid", "default")
        
        # Format the path for this message
        from loguru._file_sink import FileDateFormatter
        time_formatter = FileDateFormatter(record["time"])
        expected_path = self._path.replace("{extra[uid]}", str(uid)).format_map({"time": time_formatter})
        expected_path = os.path.abspath(expected_path)
        
        # If the currently open file path is different, close it first!
        if self._file is not None and self._file_path != expected_path:
            self._terminate_file(is_rotating=False)
            
        self._current_message_path = expected_path
        original_write(self, message)

    def custom_create_path(self):
        if getattr(self, "_current_message_path", None):
            return self._current_message_path
        path = self._path.replace("{extra[uid]}", "default")
        from loguru._file_sink import FileDateFormatter
        path = path.format_map({"time": FileDateFormatter()})
        return os.path.abspath(path)

    FileSink.write = custom_write
    FileSink._create_path = custom_create_path

    # Remove any existing handlers so configuration is idempotent
    logger.remove()
    logger.configure(extra={"uid": "n/a", "username": "n/a"})

    # Use the current entrypoint (e.g. manage.py) as the base log filename
    script_name = Path(sys.argv[0]).stem

    # logs/ directory lives two levels above this app's package (backend root)
    current_dir = Path(__file__).resolve().parent
    logs_dir = current_dir.parent.parent / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        logs_dir = current_dir.parent / "logs"
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
        "uid=<magenta>{extra[uid]}</magenta> user=<cyan>{extra[username]}</cyan> | "
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

    class UserDiagnosticSink:
        def __init__(self, logs_dir):
            self.logs_dir = logs_dir

        def __call__(self, message):
            record = message.record
            uid = record["extra"].get("uid")
            if not uid or uid in ("n/a", "anonymous"):
                return
            import uuid
            try:
                uuid.UUID(str(uid))
            except ValueError:
                return
            if record["level"].no < 20:
                return
            
            log_dir = self.logs_dir / "diagnostic"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{uid}.log"

            # Check rotation: 10 MB
            if log_path.exists() and log_path.stat().st_size >= 10 * 1024 * 1024:
                try:
                    rotated = log_path.with_suffix(".log.1")
                    if rotated.exists():
                        rotated.unlink()
                    log_path.rename(rotated)
                except Exception:
                    pass

            # Clean up old files (retention 14 days) - randomly 1% of the time to avoid overhead
            import random
            if random.random() < 0.01:
                try:
                    import time
                    now = time.time()
                    for f_path in log_dir.glob("*.log*"):
                        if f_path.is_file() and (now - f_path.stat().st_mtime) > 14 * 86400:
                            f_path.unlink()
                except Exception:
                    pass

            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(message)
            except Exception:
                pass

    logger.add(
        UserDiagnosticSink(logs_dir),
        level="INFO",
        format=base_fmt,
    )

    return logger


import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import sys
sys.path.append('')
class CustomFormatter(logging.Formatter):
    """
    Custom log formatter.
    """

    BLACK = '\x1b[30m'
    RED = '\x1b[31m'
    GREEN = '\x1b[32m'
    YELLOW = '\x1b[33m'
    BLUE = '\x1b[34m'
    MAGENTA = '\x1b[35m'
    CYAN = '\x1b[36m'
    WHITE = '\x1b[37m'
    RESET = '\x1b[0m'

    def format(self, record):
        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")  # Log creation time
        log_level = f"[{record.levelname}]"  # Log level
        logger_name = f"[{record.name}]"  # Logger name
        log_message = record.getMessage()  # Log message

        log_format = f"{log_time} {log_level:<9} {logger_name} > {log_message}"
        color_format = self.apply_color(record.levelno, log_format)
        return color_format

    def apply_color(self, levelno, log_format):
        if levelno >= logging.CRITICAL:
            return f"{self.RED}{log_format}{self.RESET}"
        elif levelno >= logging.ERROR:
            return f"{self.RED}{log_format}{self.RESET}"
        elif levelno >= logging.WARNING:
            return f"{self.YELLOW}{log_format}{self.RESET}"
        elif levelno >= logging.INFO:
            return f"{self.GREEN}{log_format}{self.RESET}"
        elif levelno >= logging.DEBUG:
            return f"{self.BLUE}{log_format}{self.RESET}"
        else:
            return log_format



class CustomRotatingFileHandler(RotatingFileHandler):
    """
    Custom rotating file handler for logging.
    """

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None):
        if os.path.isfile(filename):
            old_log_file = f"{os.path.splitext(filename)[0]}_old.log"
            if os.path.isfile(old_log_file):
                with open(old_log_file, "a", encoding="utf-8") as f:
                    with open(filename, "r", encoding="utf-8") as f2:
                        f.write(f2.read())
                os.remove(filename)
            else:
                os.rename(filename, old_log_file)

        super().__init__(filename, mode, maxBytes, backupCount, encoding)

    def emit(self, record):
        try:
            msg = self.format(record)
            with open(self.baseFilename, "a", encoding="utf-8") as f:
                f.write(msg + self.terminator)
        except Exception:
            self.handleError(record)


class CustomLogger(logging.Logger):
    """
    Custom logger class.
    """

    def __init__(self, name, log_file, level="DEBUG", maxBytes=10000000, backupCount=1):
        super().__init__(name, level)
        self.log_file = log_file
        self.level = level
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        self.setup_logger()

    def setup_logger(self):
        file_handler = CustomRotatingFileHandler(
            self.log_file, mode='a', maxBytes=self.maxBytes, backupCount=self.backupCount, encoding='utf-8'
        )
        file_handler.setFormatter(CustomFormatter())

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter())

        self.setLevel(self.level)
        file_handler.setLevel(self.level)
        console_handler.setLevel(self.level)

        self.addHandler(file_handler)
        self.addHandler(console_handler)

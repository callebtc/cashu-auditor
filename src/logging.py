import logging
import sys

from loguru import logger

DEBUG = True
LOG_LEVEL = "DEBUG"


def configure_logger() -> None:
    class Formatter:
        def __init__(self):
            self.padding = 0
            self.minimal_fmt = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SS}</green> |"
                " <level>{level}</level> | <level>{message}</level>\n"
            )
            if DEBUG:
                self.fmt = (
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SS}</green> | <level>{level:"
                    " <4}</level> |"
                    " <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
                    " | <level>{message}</level>\n"
                )
            else:
                self.fmt = self.minimal_fmt

        def format(self, record):
            function = "{function}".format(**record)
            if function == "emit":  # uvicorn logs
                return self.minimal_fmt
            return self.fmt

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.log(level, record.getMessage())

    logger.remove()
    log_level = LOG_LEVEL
    if DEBUG and log_level == "INFO":
        log_level = "DEBUG"
    formatter = Formatter()
    logger.add(sys.stderr, level=log_level, format=formatter.format)

    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

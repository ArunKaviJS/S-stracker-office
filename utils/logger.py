import logging

logger = logging.getLogger()

logger.setLevel(logging.INFO)

def log(msg):
    logger.info(msg)
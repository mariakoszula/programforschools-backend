import logging.handlers
import logging
from os import getenv

handler = logging.handlers.RotatingFileHandler('rykosystem.log', maxBytes=10 * 1024 * 1024, backupCount=1)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

logger = logging.getLogger()
logger.addHandler(handler)
if int(getenv("DEBUG_MODE")):
    logger.addHandler(logging.StreamHandler())

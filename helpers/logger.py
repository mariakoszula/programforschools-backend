import logging.handlers
from os import getenv, path, getcwd

app_logger = logging.getLogger("app")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
LOG_FILE = path.join(getcwd(), "programforschools.log")
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=1)

if int(getenv("DEBUG_MODE", 0)):
    app_logger.setLevel(logging.DEBUG)
    handlerStream = logging.StreamHandler()
    handlerStream.setLevel(logging.DEBUG)
    handlerStream.setFormatter(formatter)
    app_logger.addHandler(handlerStream)
    handler.setLevel(logging.INFO)
else:
    handlerStream = logging.StreamHandler()
    handlerStream.setLevel(logging.WARNING)
    handlerStream.setFormatter(formatter)
    app_logger.addHandler(handlerStream)
    handler.setLevel(logging.WARNING)
    app_logger.setLevel(logging.WARNING)


handler.setFormatter(formatter)
app_logger.addHandler(handler)

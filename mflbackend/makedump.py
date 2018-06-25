import logging
import sys

# set logging level before importing anything else
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
import src.backend

src.backend.prepare_restart()

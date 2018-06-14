# startup-scriptet (samma som strix har)
import sys
import json
from src.backend import app, start, offline_restart
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    sys.exit("Usage %s <port>" % sys.argv[0])
offline_restart()
WSGIServer(('0.0.0.0', port), app).serve_forever()

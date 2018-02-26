set -e
# get mappings and modes.json, lexiconconf, saldomp.json
cp karp-backend/config/lexiconconf.json dummyauth
cd karp-backend
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

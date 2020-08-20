import json
import os

print(f"cwd = {os.getcwd()}")

config = json.load(open("config/config.json"))
config["all_lexicons"] = json.load(open("config/lexicons.json"))
config["lexiconpath"] = {}
for lex in config["all_lexicons"]:
    config["lexiconpath"][lex["name"]] = "config/%s.json" % lex["name"]

import json


def get_config():
    with open('config.json') as file:
        return json.load(file)

import json

REGION_NAME_MAP = {
    "CHI@UC": "uc",
    "CHI@TACC": "tacc",
    "CHI@NRP": "nrp",
}

# allow us to import the referenceapi jsonschema without knowing the path in other modules.
SCHEMA = None
with open("data_files/rapi.jsonschema") as f:
    SCHEMA = json.load(f)

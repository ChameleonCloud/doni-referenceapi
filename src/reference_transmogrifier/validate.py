import argparse

from glob import glob
import json
from pydantic import ValidationError

from reference_transmogrifier.models import reference_repo as reference_repo_model

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_repo_dir")
    return parser.parse_args()


def find_node_json(reference_repo_dir):
    fnames = glob(f"{reference_repo_dir}/**/nodes/*.json", recursive=True)
    for fname in fnames:
        with open(fname, 'r') as f:
            yield json.load(f)

def main():
    args = parse_args()

    node_jsons = find_node_json(args.reference_repo_dir)
    for node in node_jsons:
        node_uuid = node.get('uid')
        node_name = node.get('node_name')
        # site = xxx
        
        try:
            validated_node = reference_repo_model.Node.model_validate(node)
        except ValidationError as e:
            print(f"Validation error for node {node_uuid}:{node_name} {e}")
            continue

if __name__ == "__main__":
    main()

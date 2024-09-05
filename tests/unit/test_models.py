import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from transmogrifier.models import reference_repo


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-repo-site-dir")
    return parser.parse_args()


def load_reference_json_files(path):
    pathlist = Path(path).glob("**/nodes/*.json")
    for path in pathlist:
        with open(path, "r") as fp:
            yield json.load(fp)


def main():
    args = parse_args()
    for reference_node in load_reference_json_files(args.reference_repo_site_dir):
        node_name = reference_node.get("node_name")
        try:
            reference_repo.Node.model_validate(reference_node)
        except ValidationError as exc:
            print(f"validating {node_name}")
            print(repr(exc))
            continue


if __name__ == "__main__":
    main()

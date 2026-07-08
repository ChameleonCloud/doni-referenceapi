import pathlib
import json

from reference_transmogrifier.models import reference_repo

REGION_NAME_MAP = {
    "CHI@UC": "uc",
    "CHI@TACC": "tacc",
    "CHI@NRP": "nrp",
    "KVM@TACC": "kvm",
}


def write_reference_repo(
    repo_dir, cloud_name, node: reference_repo.Node
) -> pathlib.Path:
    repo_path = pathlib.Path(repo_dir)
    node_data_path = repo_path.joinpath(
        "data/chameleoncloud/sites",
        cloud_name,
        "clusters/chameleon/nodes",
        f"{node.uid}.json",
    )

    output_json = json.dumps(
        node.model_dump(mode="json", exclude_none=True, exclude_unset=True),
        indent=2,
        sort_keys=True,
    )

    with open(node_data_path, "w") as f:
        f.write(output_json)

    return node_data_path


def prune_missing_nodes(
    repo_dir, cloud_name, live_node_uids
) -> list[pathlib.Path]:
    """Remove node JSON files for nodes no longer present in `live_node_uids`.

    Returns the list of removed file paths.
    """
    repo_path = pathlib.Path(repo_dir)
    nodes_dir = repo_path.joinpath(
        "data/chameleoncloud/sites", cloud_name, "clusters/chameleon/nodes"
    )

    removed = []
    if not nodes_dir.exists():
        return removed

    for node_json_path in nodes_dir.glob("*.json"):
        if node_json_path.stem not in live_node_uids:
            node_json_path.unlink()
            removed.append(node_json_path)

    return removed

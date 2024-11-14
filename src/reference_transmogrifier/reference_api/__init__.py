import pathlib

from reference_transmogrifier.models import reference_repo

REGION_NAME_MAP = {
    "CHI@UC": "uc",
    "CHI@TACC": "tacc",
    "CHI@NRP": "nrp",
}


def write_reference_repo(repo_dir, cloud_name, node: reference_repo.Node) -> None:
    repo_path = pathlib.Path(repo_dir)
    node_data_path = repo_path.joinpath(
        "data/chameleoncloud/sites",
        cloud_name,
        "clusters/chameleon/nodes",
        f"{node.uid}.json",
    )
    with open(node_data_path, "w") as f:
        f.write(
            node.model_dump_json(
                exclude_none=True,
                exclude_unset=True,
                indent=2,
            )
        )

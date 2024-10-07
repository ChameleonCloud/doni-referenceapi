import argparse
import json
import pathlib
import shutil
from tempfile import TemporaryDirectory

import openstack
from git import Repo
from openstack.exceptions import BadRequestException, NotFoundException
from pydantic import ValidationError

from reference_transmogrifier import reference_api
from reference_transmogrifier.models import blazar, inspector, reference_repo


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--cloud")
    parser.add_argument(
        "--reference-repo-url",
        help="URL for git repo",
        default="https://github.com/chameleoncloud/reference-repository.git",
    )
    parser.add_argument(
        "--reference-repo-ref",
        help="git ref to compare with (sha, branch, tag, whatever)",
        default="master",
    )
    parser.add_argument("--ironic-data-cache-dir")
    parser.add_argument(
        "--only-nodes",
        nargs="+",
        help="Name or ID of one or more nodes to target. Mutually exclusive with --except-node. Example: `--only-nodes nc01 nc60`",
    )
    parser.add_argument(
        "--except-nodes",
        nargs="+",
        help="Name or ID of one or more nodes to exclude from the list. Mutually exclusive with --only-node. Example: `--except-nodes nc01 nc60`",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    conn = openstack.connect(cloud=args.cloud)

    region_name = conn.config.get_region_name()
    cloud_name = reference_api.REGION_NAME_MAP[region_name]

    base_dir = pathlib.Path("./output")
    final_output_dir = base_dir.joinpath("reference-repository")

    local_dir = TemporaryDirectory(dir=base_dir)
    reference_repo_checkout = Repo.clone_from(
        url=args.reference_repo_url,
        branch=args.reference_repo_ref,
        to_path=local_dir.name,
    )

    ironic_uuid_to_blazar_hosts = {
        h.hypervisor_hostname: h for h in conn.reservation.hosts()
    }

    if args.only_nodes:
        # assume we have a short list to target, get them individually
        nodes_to_process = [conn.baremetal.get_node(n) for n in args.only_nodes]
    elif args.except_nodes:
        # get list of all nodes, filter out a subset
        nodes_to_process = [
            n
            for n in conn.baremetal.nodes()
            if (n.name not in args.except_nodes) and (n.id not in args.except_nodes)
        ]
    else:
        nodes_to_process = conn.baremetal.nodes()

    for node in nodes_to_process:
        blazar_host = ironic_uuid_to_blazar_hosts.get(node.id)

        # HACK: convert back to the form the API returns, instead of using properties field
        blazar_host_dict = blazar_host.to_dict()
        blazar_host_properties = blazar_host_dict.pop("properties")
        blazar_host_dict.update(blazar_host_properties)

        # For each node, get the inspection data from ironic_inspector
        try:
            inspection_dict = conn.baremetal_introspection.get_introspection_data(
                introspection=node.id, processed=True
            )
        except (BadRequestException, NotFoundException):
            print(f"{node.id}:{node.name}: missing inspection data - skipping")
            continue

        try:
            i_data = inspector.InspectorResult(**inspection_dict)
            b_data = blazar.Host(**blazar_host_dict)
            validated_node = reference_repo.Node.from_inspector_result(b_data, i_data)
        except ValidationError as ex:
            print(f"{node.id}:{node.name}: failed to validate with error {repr(ex)}")
            if args.verbose:
                print(json.dumps(inspection_dict, indent=2))
            continue

        node_json = reference_api.write_reference_repo(
            reference_repo_checkout.working_dir, cloud_name, validated_node
        )

        # diff the file we just wrote against the latest committed version
        repo_diff = reference_repo_checkout.index.diff(None, paths=node_json)
        if repo_diff:
            print(f"{node.id}:{node.name}: updated reference data")

    print(f"finished conversion, moving data from tmpdir to {final_output_dir}")
    shutil.move(reference_repo_checkout.working_dir, final_output_dir)


if __name__ == "__main__":
    main()

import argparse
import json
import os
import pathlib
import re
import shutil
import uuid
from datetime import datetime
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import openstack
from git import Repo
from github import Github
from openstack.exceptions import BadRequestException, NotFoundException
from pydantic import ValidationError

from reference_transmogrifier import reference_api
from reference_transmogrifier.models import blazar, inspector, reference_repo


def commit_and_pr_changes(
        reference_repo_url,
        reference_repo_ref,
        output_dir
    ):
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise Exception("GITHUB_TOKEN env var not set, cannot push changes")

    repo_url = re.sub(
        r"https://",
        f"https://{github_token}@",
        reference_repo_url
    )
    parts = urlparse(reference_repo_url)
    github_repo_name = parts.path.lstrip("/").removesuffix(".git")

    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"auto-update-{now}"
    pr_title = f"Automated update of reference data ({now})"
    pr_body = f"This is an automated update of the reference data on {now}"

    repo = Repo(str(output_dir))
    repo.git.remote('set-url', 'origin', repo_url)
    repo.git.checkout('HEAD', b=branch_name)
    repo.git.add(all=True)
    repo.index.commit(pr_title)
    origin = repo.remote(name="origin")
    origin.push(branch_name)

    gh = Github(github_token)
    gh_repo = gh.get_repo(github_repo_name)
    pr = gh_repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=reference_repo_ref
    )
    print(f"created PR: {pr.html_url}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--cloud")
    parser.add_argument(
        "--push-changes",
        action="store_true",
        help="Commit and push changes to a branch and open a PR",
    )
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
    base_dir.mkdir(exist_ok=True)

    final_output_dir = base_dir.joinpath("reference-repository")
    print(f"final output dir will be {final_output_dir}")
    if final_output_dir.exists():
        unique_id = uuid.uuid4().hex[0:8]
        archive_dir = base_dir.joinpath(f"reference-repository-{unique_id}")
        print(f"moving existing output dir to {archive_dir}")
        shutil.move(str(final_output_dir), str(archive_dir))

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

    if args.push_changes:
        commit_and_pr_changes(
            args.reference_repo_url,
            args.reference_repo_ref,
            final_output_dir
        )


if __name__ == "__main__":
    main()

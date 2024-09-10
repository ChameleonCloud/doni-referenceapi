import argparse

import openstack
from openstack.exceptions import BadRequestException, NotFoundException

from reference_transmogrifier import reference_api


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud")
    parser.add_argument("--reference-repo-dir")
    parser.add_argument("--ironic-data-cache-dir")
    return parser.parse_args()


def main():
    args = parse_args()

    conn = openstack.connect(cloud=args.cloud)

    region_name = conn.config.get_region_name()
    cloud_name = reference_api.REGION_NAME_MAP[region_name]

    ironic_uuid_to_blazar_hosts = {
        h.hypervisor_hostname: h for h in conn.reservation.hosts()
    }

    for node in conn.baremetal.nodes():
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
            print(f"failed to get inspection data for node {node.id}")
            continue

        try:
            generated_data = reference_api.generate_rapi_json(
                blazar_host_dict, inspection_dict
            )
        except Exception as ex:
            print(node.name)
            print(ex)
            continue

        validated_node = reference_api.reference_repo.Node(**generated_data)

        if args.reference_repo_dir:
            reference_api.write_reference_repo(
                args.reference_repo_dir, cloud_name, validated_node
            )
            print(f"wrote reference data for {validated_node.uid}")


if __name__ == "__main__":
    main()

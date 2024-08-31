import argparse
import json
import pathlib

import jsonschema
import openstack
from openstack.baremetal.v1.node import Node as IronicNode
from openstack.exceptions import BadRequestException, NotFoundException
from openstack.reservation.v1.host import Host as BlazarHost

from transmogrifier import reference_api


def generate_rapi_json(
    blazar_host: BlazarHost, ironic_node: IronicNode, inspection_item: dict
):
    blazar_properties = blazar_host.properties

    dmi_data = inspection_item.get("dmi", {})
    dmi_cpu = dmi_data.get("cpu")
    dmi_bios = dmi_data.get("bios")

    inspection_inventory = inspection_item.get("inventory", {})
    inventory_cpu = inspection_inventory.get("cpu")
    chassis = inspection_inventory.get("system_vendor")
    memory = inspection_inventory.get("memory")

    # // for integer floor division, don't convert to float
    memory_gb = memory.get("physical_mb") // 1024

    def hz_from_mhz(mhz):
        # string to float to int...
        mhz_int = int(float(mhz))
        hz = mhz_int * 1000 * 1000
        return hz

    data = {
        "uid": ironic_node.id,
        "node_name": ironic_node.name,
        "node_type": blazar_properties.get("node_type"),
        "architecture": {
            "platform_type": inspection_item.get("cpu_arch"),
            "smp_size": len(dmi_cpu),
            "smt_size": inspection_item.get("cpus"),
        },
        "bios": {
            "release_date": dmi_bios.get("Release Date"),
            "vendor": dmi_bios.get("Vendor"),
            "version": dmi_bios.get("Version"),
        },
        "chassis": {
            "manufacturer": chassis.get("manufacturer"),
            "name": chassis.get("product_name"),
            "serial": chassis.get("serial_number"),
        },
        "processor": {
            "model": f"{dmi_cpu[0].get('Manufacturer')} {dmi_cpu[0].get('Family')}",
            "other_description": inventory_cpu.get("model_name"),
            "clock_speed": hz_from_mhz(inventory_cpu.get("frequency")),
            "instruction_set": inventory_cpu.get("architecture"),
            "vendor": dmi_cpu[0].get("Manufacturer"),
        },
        "main_memory": {
            "humanized_ram_size": f"{memory_gb} GiB",
            "ram_size": memory.get("total"),
        },
        "monitoring": {"wattmeter": False},
        "network_adapters": [],
        "storage_devices": [],
        "supported_job_types": {
            "besteffort": False,
            "deploy": True,
            "virtual": "ivt",
        },
        "type": "node",
    }

    # hacky, set placement info IFF it exists
    placement = {}
    placement_node = blazar_properties.get("placement.node")
    if placement_node:
        placement["node"] = placement_node
    placement_rack = blazar_properties.get("placement.rack")
    if placement_rack:
        placement["rack"] = placement_rack

    if placement:
        data["placement"] = placement

    # sort all present interfaces by mac address
    sorted_interface_list = sorted(
        inspection_item.get("all_interfaces", []).items(),
        key=lambda i: i[1]["mac"],
    )
    for name, values in sorted_interface_list:
        rapi_interface = {
            "name": name,
            "mac": values.get("mac"),
            "enabled": None,
        }

        # if ironic inspection gets an ip address, then the interface
        # is enabled in neutron
        if values.get("ip"):
            rapi_interface["enabled"] = True
        else:
            rapi_interface["enabled"] = False

        lldp = values.get("lldp_processed")
        if lldp:
            rapi_interface["local_link_connection"] = {
                "switch_id": lldp.get("switch_chassis_id"),
                "switch_info": lldp.get("switch_system_name"),
                "switch_port_id": lldp.get("switch_port_id"),
                "switch_port_mtu": lldp.get("switch_port_mtu"),
            }

        data["network_adapters"].append(rapi_interface)

    for disk in inspection_inventory.get("disks", []):
        rapi_disk = {
            "device": disk.get("name"),
            "model": disk.get("model"),
            "serial": disk.get("serial"),
            "size": disk.get("size"),
            "interface": "UNKNOWN",
        }

        if disk.get("rotational") == False:
            rapi_disk["media_type"] = "SSD"
        elif disk.get("rotational") == True:
            rapi_disk["media_type"] = "Rotational"
        else:
            rapi_disk["media_type"] = "UNKNOWN"

        data["storage_devices"].append(rapi_disk)

    return data


def write_reference_repo(repo_dir, cloud_name, data: dict) -> None:
    node_id = data.get("uid")

    repo_path = pathlib.Path(repo_dir)
    node_data_path = repo_path.joinpath(
        "data/chameleoncloud/sites",
        cloud_name,
        "clusters/chameleon/nodes",
        f"{node_id}.json",
    )
    with open(node_data_path, "w") as f:
        json.dump(data, fp=f, indent=2, sort_keys=True)


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

    ironic = conn.baremetal
    inspector = conn.baremetal_introspection

    schema = reference_api.SCHEMA

    ironic_uuid_to_blazar_hosts = {
        h.hypervisor_hostname: h for h in conn.reservation.hosts()
    }

    # generator, yields ironic baremetal.v1.Node objects
    all_baremetal_nodes = ironic.nodes()

    for node in all_baremetal_nodes:
        blazar_host = ironic_uuid_to_blazar_hosts.get(node.id)

        # For each node, get the inspection data from ironic_inspector
        try:
            inspection_dict = inspector.get_introspection_data(
                introspection=node.id, processed=True
            )
        except (BadRequestException, NotFoundException):
            print(f"failed to get inspection data for node {node.id}")
            continue

        generated_data = generate_rapi_json(blazar_host, node, inspection_dict)
        jsonschema.validate(instance=generated_data, schema=schema)

        if args.reference_repo_dir:
            write_reference_repo(args.reference_repo_dir, cloud_name, generated_data)
            print(f"wrote reference data for {node.id}")


if __name__ == "__main__":
    main()

import pathlib

from reference_transmogrifier.models import reference_repo as model

REGION_NAME_MAP = {
    "CHI@UC": "uc",
    "CHI@TACC": "tacc",
    "CHI@NRP": "nrp",
}


def generate_rapi_json(blazar_host: dict, inspection_item: dict):
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
        "uid": blazar_host.get("hypervisor_hostname"),
        "node_name": blazar_host.get("node_name"),
        "node_type": blazar_host.get("node_type"),
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
    placement_node = blazar_host.get("placement.node")
    if placement_node:
        placement["node"] = placement_node
    placement_rack = blazar_host.get("placement.rack")
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
            "device": name,
            "mac": values.get("mac"),
            "enabled": None,
        }

        # if ironic inspection gets an ip address, then the interface
        # is enabled in neutron
        if values.get("ip"):
            rapi_interface["enabled"] = True
        else:
            rapi_interface["enabled"] = False

        data["network_adapters"].append(rapi_interface)

    for disk in inspection_inventory.get("disks", []):
        rapi_disk = {
            "device": disk.get("name"),
            "model": disk.get("model"),
            "serial": disk.get("serial"),
            "size": disk.get("size"),
        }

        if disk.get("rotational") == False:
            rapi_disk["media_type"] = "SSD"
        elif disk.get("rotational") == True:
            rapi_disk["media_type"] = "Rotational"

        data["storage_devices"].append(rapi_disk)

    return data


def write_reference_repo(repo_dir, cloud_name, node: model.Node) -> None:
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

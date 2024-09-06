import pathlib

from reference_transmogrifier.models import reference_repo
from reference_transmogrifier.models.inspector import main

REGION_NAME_MAP = {
    "CHI@UC": "uc",
    "CHI@TACC": "tacc",
    "CHI@NRP": "nrp",
}


def generate_rapi_json(blazar_host: dict, inspection_item: dict):
    inspector_data = main.InspectorResult(**inspection_item)

    dmi_data = inspection_item.get("dmi", {})
    dmi_cpu = dmi_data.get("cpu")
    dmi_bios = dmi_data.get("bios")

    inspection_inventory = inspection_item.get("inventory", {})
    chassis = inspection_inventory.get("system_vendor")
    memory = inspection_inventory.get("memory")

    # // for integer floor division, don't convert to float
    memory_gb = memory.get("physical_mb") // 1024

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

    data["processor"] = inspector_data.get_referenceapi_cpu_info()
    data["network_adapters"] = inspector_data.get_referenceapi_network_adapters()
    data["storage_devices"] = inspector_data.get_referenceapi_disks()

    return data


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

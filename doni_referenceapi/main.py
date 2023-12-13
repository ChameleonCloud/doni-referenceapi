import datetime
import json

import ironic_inspector_client
from doniclient.v1.client import Client as DoniClient
from keystoneauth1.adapter import Adapter
from openstack.connection import Connection

from doni_referenceapi.models import referenceapi

output_dir = (
    "../reference-repository/data/chameleoncloud/sites/boulder/clusters/chameleon/nodes"
)


def main():
    """Generates referenceapi compatible JSON for nodes at a given site.

    For a given site, specified via clouds.yaml compatible auth:
    1. Loop over all baremetal nodes returned from Doni
    2. For each device returned, populate referenceAPI pydantic model.
       Where necessary, fetch informaton from ironci-inspector results.
    """

    # get an openstack connection
    conn = Connection(cloud="boulder_admin")

    # get doni client
    doni = DoniClient(
        Adapter(
            session=conn.session,
            service_type="inventory",
            interface="public",
        )
    )

    # get ironic inspector client
    ic = ironic_inspector_client.ClientV1(session=conn.session)

    # get iterator for all HW items
    hwitems = doni.list()
    for item in hwitems:
        node_uuid = item.get("uuid")
        properties = item.get("properties")
        try:
            ic_data = ic.get_data(node_id=node_uuid)
        except ironic_inspector_client.ClientError:
            pass

        ic_dma_cpus = ic_data.get("dmi", {}).get("cpu")

        processors = [
            referenceapi.Processor(
                vendor=proc.get("Manufacturer"),
                model=proc.get("Version"),
                clock_speed=proc.get("Current Speed"),
            )
            for proc in ic_dma_cpus
        ]

        sockets = len(processors)
        cores_per_socket = int(ic_dma_cpus[0].get("Core Count"))
        threads_per_socket = int(ic_dma_cpus[0].get("Thread Count"))

        arch = referenceapi.Architecture(
            platform_type=ic_data.get("cpu_arch"),
            smp_size=sockets,
            smt_size=sockets * threads_per_socket,
        )

        ic_data_bios = ic_data.get("dmi", {}).get("bios")
        bios_release_date = datetime.datetime.strptime(
            ic_data_bios.get("Release Date"), "%m/%d/%Y"
        )

        bios = referenceapi.Bios(
            vendor=ic_data_bios.get("Vendor"),
            version=ic_data_bios.get("Version"),
            release_date=bios_release_date,
        )

        ic_data_mem = ic_data.get("dmi", {}).get("memory").get("devices")
        mem_devices = []
        for d in ic_data_mem:
            try:
                mem_device = referenceapi.MainMemory(ram_size=d.get("Size"))
            except Exception:
                pass
            else:
                mem_devices.append(mem_device)

        total_bytes_mem = sum(m.ram_size for m in mem_devices)
        memory = referenceapi.MainMemory(ram_size=total_bytes_mem)

        rapi_disks = []
        for d in ic_data.get("inventory", {}).get("disks"):
            if d.get("rotational"):
                media_type = "HDD"
            elif not d.get("rotational"):
                media_type = "SSD"
            else:
                media_type = "Unknown"

            rapi_disks.append(
                referenceapi.StorageDevice(
                    device=d.get("name"),
                    model=d.get("model"),
                    size=d.get("size"),
                    media_type=media_type,
                )
            )

        rapi_nics = []
        for n in ic_data.get("inventory", {}).get("interfaces"):
            rapi_nics.append(
                referenceapi.NetworkAdapter(
                    device=n.get("name"),
                    enabled=n.get("has_carrier", False),
                    mac=n.get("mac_address"),
                )
            )

        rapi_node = referenceapi.Node(
            uid=node_uuid,
            node_name=item.get("name"),
            node_type=properties.get("node_type"),
            architecture=arch,
            processor=processors[0],
            bios=bios,
            main_memory=memory,
            network_adapters=rapi_nics,
            storage_devices=rapi_disks,
        )

        with open(f"{output_dir}/{rapi_node.uid}.json", "w+") as f:
            json.dump(
                rapi_node.model_dump(mode="json", exclude_none=True),
                f,
                indent=2,
                sort_keys=True,
            )
            f.write("\n")  # Ensure file ends with a newline.


if __name__ == "__main__":
    main()

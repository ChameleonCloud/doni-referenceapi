from typing import List, Optional

from pydantic import BaseModel

from reference_transmogrifier.models import reference_repo
from reference_transmogrifier.models.inspector import dmi, extra_hardware, inventory


class InspectorResult(BaseModel):
    inventory: inventory.Inventory
    root_disk: dict
    boot_interface: str
    configuration: dict
    pci_devices: List[dict]
    dmi: dmi.DMI
    numa_topology: dict
    all_interfaces: dict
    interfaces: dict
    macs: List[str]
    local_gb: int
    cpus: int
    cpu_arch: str
    memory_mb: int
    extra: Optional[extra_hardware.InspectorExtraHardware] = None

    def get_referenceapi_network_adapters(self) -> List[reference_repo.NetworkAdapter]:
        if self.extra:
            ifaces = [
                iface.as_reference_iface(name)
                for name, iface in self.extra.network.items()
            ]
        else:
            ifaces = [iface.as_reference_iface() for iface in self.inventory.interfaces]
        return ifaces

    def get_referenceapi_cpu_info(self) -> reference_repo.Processor:
        extra_hardware_cpu = self.extra.cpu
        dmi_cpu = self.dmi.cpu[0]

        return reference_repo.Processor(
            cache_l1d=extra_hardware_cpu.physical_0.l1d_cache,
            cache_l1i=extra_hardware_cpu.physical_0.l1i_cache,
            cache_l2=extra_hardware_cpu.physical_0.l2_cache,
            cache_l3=extra_hardware_cpu.physical_0.l3_cache,
            clock_speed=dmi_cpu.current_speed_hz(),
            instruction_set=extra_hardware_cpu.physical_0.architecture,
            model=extra_hardware_cpu.physical_0.product,
            vendor=extra_hardware_cpu.physical_0.vendor,
        )

    def get_referenceapi_disks(self) -> List[reference_repo.StorageDevice]:
        """Combine data from multiple ironic collectors.

        We can use the wwn-id to match disks from inventory and extra data sources
        """

        output_disks_list = []

        extra_disks_by_wwn = {}
        if self.extra:
            extra_data_disks = self.extra.disk
            # index by wwn
            for name, disk in extra_data_disks.items():
                wwn = disk.wwn_id.lstrip("wwn-")
                extra_disks_by_wwn[wwn] = disk

        inventory_disks_list = self.inventory.disks
        for d in inventory_disks_list:
            wwn = d.wwn_with_extension
            # find matching disk by wwn
            extra_disk = extra_disks_by_wwn.get(wwn)

            extra_args = {}
            if isinstance(extra_disk, extra_hardware.Disk):
                extra_args["rev"] = extra_disk.rev

            if d.serial:
                extra_args["serial"] = d.serial

            output = reference_repo.StorageDevice(
                device=d.name,
                humanized_size=d.humanized_size,
                size=d.size,
                model=d.model,
                vendor=d.vendor,
                interface=d.interface,
                media_type=d.media_type,
                **extra_args,
            )
            output_disks_list.append(output)
        return output_disks_list

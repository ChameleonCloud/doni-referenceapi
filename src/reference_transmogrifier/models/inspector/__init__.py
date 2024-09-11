from typing import List, Optional

from pydantic import BaseModel, field_validator

from reference_transmogrifier.models import reference_repo
from reference_transmogrifier.models.inspector import (
    dmi,
    extra_hardware,
    inventory,
    pci,
)


class InspectorResult(BaseModel):
    inventory: inventory.Inventory
    root_disk: dict
    boot_interface: str
    configuration: dict
    pci_devices: List[pci.PciDevice]
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

    @field_validator("pci_devices", mode="before")
    @classmethod
    def filter_known_pci_devices(cls, v: List[pci.PciDevice]) -> List[pci.PciDevice]:
        """For speed, only grabbing display adapters for now."""

        display_adapter_device_class = "03"

        return [
            d
            for d in v
            if d.get("class").startswith(display_adapter_device_class)
            and d.get("vendor_id") != "102b"
        ]

    def get_referenceapi_network_adapters(self) -> List[reference_repo.NetworkAdapter]:
        if self.extra:
            ifaces = [
                iface.as_reference_iface(name)
                for name, iface in self.extra.network.items()
            ]
        else:
            ifaces = [iface.as_reference_iface() for iface in self.inventory.interfaces]

        # we want interfaces to be sorted by mac address, since it's a consistent ordering
        ifaces.sort()
        return ifaces

    def get_referenceapi_gpu_info(self) -> reference_repo.GPU:
        gpu_list = []
        for d in self.pci_devices:
            gpu_list.append(d)

        if len(gpu_list) > 0:
            return reference_repo.GPU(
                gpu_count=len(gpu_list),
                gpu_model=gpu_list[0].product_name,
                gpu_vendor=gpu_list[0].vendor_name,
            )

    def get_referenceapi_cpu_info(self) -> reference_repo.Processor:
        inv_cpu = self.inventory.cpu
        dmi_cpu = self.dmi.cpu[0]

        args = {}
        if self.extra:
            ecpu = self.extra.cpu
            args["cache_l1d"] = ecpu.physical_0.l1d_cache
            args["cache_l1i"] = ecpu.physical_0.l1i_cache
            args["cache_l2"] = ecpu.physical_0.l2_cache
            args["cache_l3"] = ecpu.physical_0.l3_cache

        return reference_repo.Processor(
            clock_speed=dmi_cpu.current_speed_hz(),
            instruction_set=inv_cpu.architecture,
            model=inv_cpu.name,
            vendor=dmi_cpu.manufacturer,
            **args,
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

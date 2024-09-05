from typing import List, Optional

import humanize
from pydantic import BaseModel

from reference_transmogrifier.models import reference_repo
from reference_transmogrifier.models.inspector import dmi, extra_hardware


class InspectorResult(BaseModel):
    inventory: dict
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
    extra: Optional[extra_hardware.InspectorExtraHardware]

    def get_referenceapi_network_adapters(self):
        extra_hardware_ifaces = self.extra.network.items()
        ifaces = [
            iface.as_reference_iface(name) for name, iface in extra_hardware_ifaces
        ]
        return ifaces

    def get_referenceapi_cpu_info(self):
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

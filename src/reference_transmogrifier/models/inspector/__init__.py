from typing import List, Optional

from pydantic import BaseModel

from reference_transmogrifier.models.inspector import (
    dmi,
    extra_hardware,
    inventory,
    pci,
)


class InspectorResult(BaseModel):
    inventory: inventory.Inventory
    root_disk: Optional[dict] = None
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
    memory_mb: Optional[int] = None
    extra: extra_hardware.InspectorExtraHardware

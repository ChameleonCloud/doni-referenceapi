from typing import List, Optional

from pydantic import BaseModel

from reference_transmogrifier.models import reference_repo


class InspectorExtraNetworkIface(BaseModel):
    """Subset of NIC info that we care about."""

    vendor: str
    product: str
    firmware: str
    capacity: int
    link: bool
    driver: str
    serial: str
    ipv4: Optional[str] = None

    def as_reference_iface(self, name):
        output = reference_repo.NetworkAdapter(
            name=name,
            device=name,
            driver=self.driver,
            enabled=self.link,
            mac=self.serial,
            model=self.product,
            vendor=self.vendor,
            rate=self.capacity,
        )

        return output


class InspectorExtraHardware(BaseModel):
    disk: dict
    system: dict
    firmware: dict
    memory: dict
    network: dict[str, InspectorExtraNetworkIface]
    lldp: dict
    cpu: dict
    numa: dict
    ipmi: dict
    hw: dict


class InspectorResult(BaseModel):
    inventory: dict
    root_disk: dict
    boot_interface: str
    configuration: dict
    pci_devices: List[dict]
    dmi: dict
    numa_topology: dict
    all_interfaces: dict
    interfaces: dict
    macs: List[str]
    local_gb: int
    cpus: int
    cpu_arch: str
    memory_mb: int
    extra: Optional[InspectorExtraHardware]

    def get_referenceapi_network_adapters(self):
        extra_hardware_ifaces = self.extra.network.items()
        ifaces = [
            iface.as_reference_iface(name) for name, iface in extra_hardware_ifaces
        ]
        return ifaces

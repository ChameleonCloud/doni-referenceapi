from typing import Optional

from pydantic import BaseModel, ByteSize, Field

from reference_transmogrifier.models import reference_repo


class NetworkAdapter(BaseModel):
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


class CPUSummary(BaseModel):
    number: int
    smt: bool


class PhysicalCPU(BaseModel):
    vendor: str
    product: str
    cores: int
    threads: int
    family: int
    model: int
    stepping: int
    architecture: str
    l1d_cache: ByteSize = Field(alias="l1d cache", exclude=True)
    l1i_cache: ByteSize = Field(alias="l1i cache", exclude=True)
    l2_cache: ByteSize = Field(alias="l2 cache", exclude=True)
    l3_cache: ByteSize = Field(alias="l3 cache", exclude=True)
    min_Mhz: int
    max_Mhz: int
    flags: str
    threads_per_core: int


class CPU(BaseModel):
    physical: CPUSummary
    physical_0: PhysicalCPU
    physical_1: Optional[PhysicalCPU] = None
    physical_2: Optional[PhysicalCPU] = None
    physical_3: Optional[PhysicalCPU] = None


class InspectorExtraHardware(BaseModel):
    disk: dict
    system: dict
    firmware: dict
    memory: dict
    network: dict[str, NetworkAdapter]
    lldp: dict
    cpu: CPU
    numa: dict
    ipmi: dict
    hw: dict

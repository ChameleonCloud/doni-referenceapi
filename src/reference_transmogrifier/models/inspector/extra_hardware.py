from typing import Optional

from pydantic import (
    BaseModel,
    ByteSize,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_extra_types import mac_address
from typing_extensions import Self

from reference_transmogrifier.models import reference_repo


class NetworkAdapter(BaseModel):
    """Subset of NIC info that we care about."""

    vendor: str
    product: str
    firmware: str
    capacity: Optional[int] = None
    link: bool
    driver: str
    serial: mac_address.MacAddress
    ipv4: Optional[str] = None

    @field_validator("serial", mode="after")
    @classmethod
    def truncate_ib_mac(cls, v: mac_address.MacAddress) -> mac_address.MacAddress:
        octets = v.split(":")
        if len(octets) >= 8:
            ib_mac = ":".join(octets[-8:])
            return mac_address.MacAddress(ib_mac)
        return v

    @computed_field
    def interface(self) -> bool:
        if "ipoib" in self.driver:
            return "InfiniBand"
        else:
            return "Ethernet"

    def as_reference_iface(self, name: str):
        output = reference_repo.NetworkAdapter(
            device=name,
            driver=self.driver,
            enabled=self.link,
            mac=self.serial,
            model=self.product,
            vendor=self.vendor,
            rate=self.capacity,
            interface=self.interface,
        )

        return output


class Disk(BaseModel):
    size_gb: int = Field(alias="size")
    vendor: str
    model: str
    rev: str
    rotational: bool
    serial: Optional[str] = Field(alias="SMART/serial_number", default=None)
    wwn_id: str = Field(alias="wwn-id")
    smart_firmware_version: str = Field(alias="SMART/firmware_version", default=None)

    @computed_field
    @property
    def media_type(self) -> str:
        if self.rotational:
            return "Rotational"
        else:
            return "SSD"


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

    @model_validator(mode="before")
    def cache_per_core(self) -> Self:
        """Cache is provided as totals, but we care about per-core."""
        keys = ["l1d cache", "l1i cache", "l2 cache", "l3 cache"]
        for k in keys:
            value = self.get(k)
            if not value:
                raise ValueError(f"{k} not found in input")

            size_str = value.split("(")[0].strip()
            instances_str = value.split("(")[1].strip().split(" ")[0]

            num_instances = int(instances_str)
            total_size_bytes = ByteSize._validate(size_str, None)
            per_core_bytes = total_size_bytes // num_instances
            self[k] = per_core_bytes
        return self


class CPU(BaseModel):
    physical: CPUSummary
    physical_0: PhysicalCPU
    physical_1: Optional[PhysicalCPU] = None
    physical_2: Optional[PhysicalCPU] = None
    physical_3: Optional[PhysicalCPU] = None


class InspectorExtraHardware(BaseModel):
    disk: dict[str, Disk]
    system: dict
    firmware: dict
    memory: dict
    network: dict[str, NetworkAdapter]
    lldp: Optional[dict] = None
    cpu: CPU
    numa: dict
    ipmi: dict
    hw: dict

    @model_validator(mode="before")
    def pop_logical_disk(self) -> None:
        """The disk model is not well formed, having two data types."""
        disk_data = self.get("disk")
        disk_data.pop("logical")
        self["disk"] = disk_data
        return self

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

from reference_transmogrifier.models.inspector.utils import filter_disks


class NetworkAdapter(BaseModel):
    """Subset of NIC info that we care about."""

    name: str
    vendor: str
    product: str
    firmware: Optional[str] = None
    capacity: Optional[int] = None
    link: Optional[bool] = None
    driver: str
    serial: Optional[mac_address.MacAddress] = None
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


class Disk(BaseModel):
    name: str
    size_gb: int = Field(alias="size")
    vendor: Optional[str] = None
    model: str
    rev: Optional[str] = None
    rotational: bool
    serial: Optional[str] = Field(alias="SMART/serial_number", default=None)
    wwn_id: Optional[str] = Field(alias="wwn-id", default=None)
    smart_firmware_version: Optional[str] = Field(alias="SMART/firmware_version", default=None)
    vendor: str

    @computed_field
    @property
    def wwn(self) -> str:
        if not self.wwn_id:
            return
        return self.wwn_id.removeprefix("wwn-")

    @computed_field
    @property
    def media_type(self) -> str:
        if self.rotational:
            return "Rotational"
        else:
            return "SSD"

    @field_validator("serial", mode="before")
    @classmethod
    def convert_serial_to_str(cls, v):
        """
        Normalize serial number as strings. E.g. an integer
        should be converted to a string for a serial number.
        """
        if v is None:
            return v
        return str(v)

    @field_validator("smart_firmware_version", mode="before")
    @classmethod
    def convert_smart_firmware_version_to_str(cls, v):
        """
        Normalize SMART firmware version as strings. E.g. an integer
        should be converted to a string for a firmware version.
        """
        if v is None:
            return v
        return str(v)


class CPUSummary(BaseModel):
    number: int


class PhysicalCPU(BaseModel):
    vendor: str
    product: str
    cores: Optional[int] = None
    threads: int
    family: Optional[int] = None
    model: int
    stepping: int
    architecture: str
    l1d_cache: Optional[ByteSize] = Field(alias="l1d cache", exclude=True)
    l1i_cache: Optional[ByteSize] = Field(alias="l1i cache", exclude=True)
    l2_cache: Optional[ByteSize] = Field(alias="l2 cache", exclude=True)
    l3_cache: Optional[ByteSize] = Field(alias="l3 cache", exclude=True)
    flags: str
    threads_per_core: int

    @model_validator(mode="before")
    def cache_per_core(self) -> Self:
        """Cache is provided as totals, but we care about per-core."""
        keys = ["l1d cache", "l1i cache", "l2 cache", "l3 cache"]
        for k in keys:
            value = self.get(k)
            if not value or not isinstance(value, str):
                self[k] = None
                continue

            try:
                size_str = value.split("(")[0].strip()
                instances_str = value.split("(")[1].strip().split(" ")[0]
                num_instances = int(instances_str)
                total_size_bytes = ByteSize._validate(size_str, None)
                per_core_bytes = total_size_bytes // num_instances
                self[k] = per_core_bytes
            except Exception:
                self[k] = None

        return self


class CPU(BaseModel):
    physical: CPUSummary
    physical_0: PhysicalCPU
    physical_1: Optional[PhysicalCPU] = None
    physical_2: Optional[PhysicalCPU] = None
    physical_3: Optional[PhysicalCPU] = None


class MemoryTotal(BaseModel):
    size: ByteSize


class Memory(BaseModel):
    total: MemoryTotal

    @computed_field
    @property
    def total_size_bytes(self) -> int:
        return self.total.size

    @computed_field
    @property
    def total_size_gib(self) -> int:
        return int(self.total.size.to("GiB"))


class InspectorExtraHardware(BaseModel):
    disk: list[Disk]
    system: dict
    firmware: dict
    memory: Memory
    network: list[NetworkAdapter]
    lldp: Optional[dict] = None
    cpu: CPU
    numa: dict
    ipmi: Optional[dict] = None
    hw: dict

    @field_validator("network", mode="before")
    @classmethod
    def nic_dict_to_list(cls, v: dict) -> list[NetworkAdapter]:
        """Data is presented as dict with interface name as keys. Convert to list for easier processing."""
        return [NetworkAdapter(name=name, **values) for name, values in v.items()]

    @model_validator(mode="before")
    def pop_logical_disk(self) -> None:
        """The disk model is not well formed, having two data types."""
        disk_data = self.get("disk")
        disk_data.pop("logical")
        self["disk"] = disk_data
        return self

    @field_validator("disk", mode="before")
    @classmethod
    def disk_dict_to_list(cls, v: dict) -> list[Disk]:
        """Data is presented as dict with interface name as keys. Convert to list for easier processing."""
        filtered_v = filter_disks(
            [
                {"name": name, **values} for name, values in v.items()
            ],
            match_disk_name=True
        )
        return [Disk(**disk) for disk in filtered_v]

from datetime import date
from enum import Enum
from typing import NewType, Optional

from pydantic import (
    UUID4,
    BaseModel,
    ByteSize,
    Field,
    computed_field,
    conlist,
    field_validator,
)

from doni_referenceapi.common.types.si_frequency import SiFrequency


class cpu_speed(object):
    SI_Frequency = [(1, "Hz"), (1000, "kHz"), (1000000, "MHz"), (1000000000, "GHz")]


class CpuInstructionSet(str, Enum):
    x86_64 = "x86_64"
    arm64 = "aarch64"


class Architecture(BaseModel):
    """
    Model for system architecture.
    Rolls up cpu properties when multiple are present.

    In OpenStack, SMP CPUs are known as cores, NUMA cells or nodes are known as sockets,
    and SMT CPUs are known as threads.
    For example, a quad-socket, eight core system with Hyper-Threading would have
    four sockets, eight cores per socket and two threads per core, for a total of 64 CPUs."""

    platform_type: CpuInstructionSet
    smp_size: int
    smt_size: int
    # sockets: int
    # cores: int
    # threads: int

    @field_validator("platform_type", mode="before")
    def transform(cls, raw: str) -> CpuInstructionSet:
        output = raw.lower().replace("-", "_")
        return CpuInstructionSet(output)

    # @computed_field
    # @property
    # def smp_size(self) -> int:
    #     """For backwards compatibility with reference-api."""
    #     return self.sockets

    # @computed_field
    # @property
    # def smt_size(self) -> int:
    #     """For backwards compatibility with reference-api."""
    #     return self.threads


class Bios(BaseModel):
    release_date: date
    vendor: str
    version: str


class Chassis(BaseModel):
    manufacturer: "str"
    name: "str"
    serial: Optional["str"] = None


class Processor(BaseModel):
    cache_l1: Optional[int] = None
    cache_l1d: Optional[int] = None
    cache_l1i: Optional[int] = None
    cache_l2: Optional[int] = None
    cache_l3: Optional[int] = None
    clock_speed: SiFrequency
    instruction_set: CpuInstructionSet = CpuInstructionSet.x86_64
    model: str
    vendor: str
    version: Optional[str] = None
    # cores: Optional[int] = None
    # threads: Optional[int] = None

    @field_validator("instruction_set", mode="before")
    def transform(cls, raw: str) -> CpuInstructionSet:
        output = raw.lower().replace("-", "_")
        return CpuInstructionSet(output)


class MainMemory(BaseModel):
    ram_size: ByteSize

    @computed_field
    @property
    def humanized_ram_size(self) -> str:
        """Return ram size in round, human numbers."""
        return self.ram_size.human_readable(decimal=True)


class Placement(BaseModel):
    """Represents where a node is in terms of racks and rack U."""

    # this should really be a string, but hw browser wants an int.
    # Represents bottommost rack-U occupied.
    node: Optional[int] = None
    rack: Optional[str] = None  # Name of the rack where node is installed.


class NetworkInterface(str, Enum):
    ethernet = "Ethernet"
    infiniband = "InfiniBand"


class NetworkAdapter(BaseModel):
    device: Optional[str] = None
    enabled: bool = True
    interface: NetworkInterface = NetworkInterface.ethernet
    mac: str
    management: bool = False
    model: Optional[str] = None
    rate: Optional[int] = None
    vendor: Optional[str] = None


NetworkAdapterListType = NewType(
    # Type to represent list of network adapters, with at least one
    "NetworkAdapterListType",
    conlist(NetworkAdapter, min_length=1),
)


class StorageInterface(str, Enum):
    pci_express = "PCIe"
    serial_ata = "SATA"


class StorageMediaType(str, Enum):
    ssd = "SSD"
    spinning_disk = "HDD"


class StorageDevice(BaseModel):
    device: str
    interface: Optional[StorageInterface] = None
    media_type: StorageMediaType
    model: Optional[str] = None
    rev: Optional[str] = None
    size: ByteSize
    vendor: Optional[str] = None

    @computed_field
    @property
    def humanized_size(self) -> str:
        """Return storage size in round, human numbers."""
        return self.size.human_readable(decimal=True)


StorageDeviceListType = NewType(
    # Type to represent list of storage devices, with at least one
    "StorageDeviceListType",
    conlist(StorageDevice, min_length=1),
)


class SupportedJobTypes(BaseModel):
    """Exists for compatability with G5K API, left as default for all Chameleon nodes."""

    besteffort: bool = False
    deploy: bool = True
    virtual: str = "ivt"


class Monitoring(BaseModel):
    wattmeter: bool = False


class Node(BaseModel):
    architecture: Architecture
    bios: Bios
    chassis: Optional[Chassis] = None
    infiniband: Optional[bool] = False
    main_memory: MainMemory
    monitoring: Monitoring = Field(default_factory=Monitoring)
    network_adapters: NetworkAdapterListType
    node_name: str
    node_type: str
    placement: Optional[Placement] = None
    processor: Processor
    storage_devices: StorageDeviceListType
    supported_job_types: SupportedJobTypes = Field(default_factory=SupportedJobTypes)
    type: str = "node"
    uid: UUID4


class Site(BaseModel):
    pass

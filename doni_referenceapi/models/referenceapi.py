from enum import Enum
from typing import List, NewType, Optional

from pydantic import UUID4, BaseModel, ByteSize, Field, computed_field, conlist


class Architecture(BaseModel):
    pass


class Bios(BaseModel):
    pass


class Chassis(BaseModel):
    pass


class CpuInstructionSet(str, Enum):
    x86_64 = "x86-64"
    amd64 = "x86-64"
    arm64 = "aarch64"


class CpuVendor(str, Enum):
    amd = "AMD"
    intel = "Intel"
    nvidia = "NVIDIA"
    fujitsu = "Fujitsu"


class Processor(BaseModel):
    cache_l1: Optional[int] = None
    cache_l1d: Optional[int] = None
    cache_l1i: Optional[int] = None
    cache_l2: Optional[int] = None
    cache_l3: Optional[int] = None
    clock_speed: int
    instruction_set: CpuInstructionSet = CpuInstructionSet.x86_64
    model: str
    vendor: CpuVendor
    version: Optional[str] = None


class MainMemory(BaseModel):
    pass


class Placement(BaseModel):
    pass


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
    interface: StorageInterface
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
    besteffort: bool = False
    deploy: bool = True
    virtual: str = "ivt"


class Node(BaseModel):
    architecture: Architecture
    bios: Bios
    chassis: Chassis
    infiniband: bool = False
    main_memory: MainMemory
    network_adapters: NetworkAdapterListType
    node_name: str
    node_type: str
    placement: Placement = Field(default_factory=Placement)
    processor: Processor
    storage_devices: StorageDeviceListType
    supported_job_types: SupportedJobTypes = Field(default_factory=SupportedJobTypes)
    type: str = "node"
    uid: UUID4


class Site(BaseModel):
    pass

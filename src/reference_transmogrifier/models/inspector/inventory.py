from typing import List, Optional

from pydantic import BaseModel, ByteSize, Field, computed_field, field_validator


class NetworkInterface(BaseModel):
    name: str
    mac_address: str
    has_carrier: bool
    vendor: str
    product: str


class Disk(BaseModel):
    name: str
    model: str
    size: ByteSize
    rotational: bool
    wwn: str
    serial: str
    vendor: str
    wwn_with_extension: str
    wwn_vendor_extension: Optional[str] = None
    hctl: str
    by_path: str

    @field_validator("name", mode="after")
    @classmethod
    def remove_dev_prefix(cls, v: str) -> str:
        return v.lstrip("/dev/")

    @field_validator("vendor", mode="after")
    @classmethod
    def check_disk_vendor(cls, v: str) -> str:
        """A number of nodes incorrectly report ATA as the vendor."""
        if v == "ATA":
            return None
        return v

    @computed_field
    @property
    def humanized_size(self) -> str:
        size_gb = self.size.to("GB")
        rounded_gb = int(round(size_gb, 0))
        return f"{rounded_gb:02d} GB"

    @computed_field
    @property
    def media_type(self) -> str:
        if self.rotational:
            return "Rotational"
        else:
            return "SSD"

    @computed_field
    @property
    def interface(self) -> str:
        # guess interface from path
        if "scsi" in self.by_path:
            return "SAS"
        elif "sas" in self.by_path:
            return "SAS"
        elif "nvme" in self.by_path:
            return "PCIe"
        elif "ata" in self.by_path:
            return "SATA"
        else:
            return None


class CPU(BaseModel):
    name: str = Field(alias="model_name")
    frequency: str
    count: int
    architecture: str
    flags: List[str]


class SystemVendor(BaseModel):
    product_name: str
    serial_number: str
    manufacturer: str


class Inventory(BaseModel):
    interfaces: List[NetworkInterface]
    cpu: CPU
    disks: List[Disk]
    memory: dict
    system_vendor: SystemVendor
    boot: dict
    hostname: str
    bmc_mac: str

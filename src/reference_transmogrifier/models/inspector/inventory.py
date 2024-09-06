from typing import List, Optional, Self

from pydantic import BaseModel, ByteSize, computed_field, field_validator


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
        elif "nvme" in self.by_path:
            return "PCIe"
        elif "sata" in self.by_path:
            return "SATA"
        else:
            return None


class Inventory(BaseModel):
    interfaces: List[dict]
    cpu: dict
    disks: List[Disk]
    memory: dict
    system_vendor: dict
    boot: dict
    hostname: str
    bmc_mac: str

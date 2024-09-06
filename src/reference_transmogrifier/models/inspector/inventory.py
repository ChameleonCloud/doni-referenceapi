from typing import List, Optional

from pydantic import BaseModel, ByteSize


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


class Inventory(BaseModel):
    interfaces: List[dict]
    cpu: dict
    disks: List[Disk]
    memory: dict
    system_vendor: dict
    boot: dict
    hostname: str
    bmc_mac: str

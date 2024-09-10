from pydantic import BaseModel, Field


class PciDevice(BaseModel):
    vendor_id: str
    product_id: str
    pci_class: str = Field(alias="class")
    revision: str
    bus: str

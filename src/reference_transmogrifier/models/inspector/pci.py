from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field, computed_field


class PciProductInfo(BaseModel):
    device_name: str
    subsystems: dict


class PciVendorInfo(BaseModel):
    vendor_name: str

    # [str, dict] instead of [str, PciProductInfo] to avoid eagerly parsing every entry
    devices: Dict[str, dict]


class KnownPciClassEnum(str, Enum):
    mass_storage_controller = "01"
    network_controller = "02"
    display_controller = "03"
    multimedia_controller = "04"
    memory_controller = "05"
    bridge = "06"
    communication_controller = "07"
    generic_system_peripheral = "08"
    serial_bus_controller = "0c"
    encryption_controller = "10"
    signal_processing_controller = "11"
    processing_accelerator = "12"
    non_essential_instrumentation = "13"
    unassigned_class = "ff"


class PciIdsMap(object):
    file_path = "src/reference_transmogrifier/models/inspector/pci.ids"

    def _load_pciids_file(self, file_path: str) -> Dict:
        data = {}

        current_vendor_id = None
        current_device_id = None

        with open(file_path, "r") as file:
            for line in file:
                line = line.rstrip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Detect the indentation level
                indent_level = len(line) - len(line.lstrip())
                line = line.lstrip()

                # Vendor line (no indentation)
                if indent_level == 0:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        current_vendor_id, vendor_name = parts
                        data[current_vendor_id] = {
                            "vendor_name": vendor_name,
                            "devices": {},
                        }

                # Device line (single level of indentation)
                elif indent_level == 1 or line.startswith("\t"):
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        current_device_id, device_name = parts
                        if current_vendor_id is not None:
                            data[current_vendor_id]["devices"][current_device_id] = {
                                "device_name": device_name,
                                "subsystems": {},
                            }

                # Subsystem line (double level of indentation)
                elif indent_level == 2 or line.startswith("\t\t"):
                    parts = line.split(maxsplit=2)
                    if len(parts) == 3:
                        subvendor_id, subdevice_id, subsystem_name = parts
                        if (
                            current_vendor_id is not None
                            and current_device_id is not None
                        ):
                            subsystem_key = (subvendor_id, subdevice_id)
                            data[current_vendor_id]["devices"][current_device_id][
                                "subsystems"
                            ][subsystem_key] = subsystem_name

        return data

    def __init__(self) -> None:
        self.data = self._load_pciids_file(self.file_path)

    def lookup_vendor(self, vendor_id: str) -> PciVendorInfo:
        result = self.data.get(vendor_id)
        if not result:
            raise KeyError(f"vendor_id: {vendor_id} not found in pci ids db")
        return PciVendorInfo(**result)

    def lookup_product(self, vendor_id: str, product_id: str) -> PciProductInfo:
        vendor = self.lookup_vendor(vendor_id)
        product = vendor.devices.get(product_id)
        if not (vendor and product):
            raise KeyError(f"({vendor_id},{product_id}) not found in pci ids db")
        return PciProductInfo(**product)


# initialize on import so we don't reload it constantly
PCI_MAP = PciIdsMap()


class PciDevice(BaseModel):
    vendor_id: str
    product_id: str
    pci_class: str = Field(alias="class")
    revision: str
    bus: str

    @computed_field
    def vendor_name(self) -> str:
        try:
            return PCI_MAP.lookup_vendor(self.vendor_id).vendor_name
        except KeyError:
            return None

    @computed_field
    def product_name(self) -> str:
        try:
            return PCI_MAP.lookup_product(self.vendor_id, self.product_id).device_name
        except KeyError:
            return None

    @computed_field
    def pci_class_enum(self) -> KnownPciClassEnum:
        """Use first two characters of PCI class hex to look up"""
        return KnownPciClassEnum(self.pci_class[0:2])

from typing import Dict, Optional

from pydantic import BaseModel, Field, computed_field


class PciDeviceInfo(BaseModel):
    device_name: str
    subsystems: dict


class PciVendorInfo(BaseModel):
    vendor_name: str
    devices: Dict[str, PciDeviceInfo]


class PciIdsMap(object):
    file_path = "src/reference_transmogrifier/models/inspector/pci.ids"

    @staticmethod
    def _load_pciids_file(file_path: str) -> Dict:
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

    data = _load_pciids_file(file_path)

    @classmethod
    def lookup_vendor(cls, vendor_id: str) -> PciVendorInfo:
        result = cls.data.get(vendor_id)
        if result:
            return PciVendorInfo.model_validate(result)
        else:
            raise KeyError(f"vendor_id: {vendor_id} not found in pci ids db")

    @classmethod
    def lookup_product(cls, vendor_id: str, product_id: str) -> PciDeviceInfo:
        vendor = cls.lookup_vendor(vendor_id)
        product = vendor.devices.get(product_id)
        if vendor and product:
            return PciDeviceInfo.model_validate(product)
        else:
            raise KeyError(f"({vendor_id},{product_id}) not found in pci ids db")


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

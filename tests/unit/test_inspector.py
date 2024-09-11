import json

from oslotest import base

from reference_transmogrifier.models.inspector import (
    dmi,
    extra_hardware,
    inventory,
    pci,
)


class TestInventory(base.BaseTestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            json_data = json.load(f)
            self.data = json_data.get("inventory")

    def test_interfaces(self):
        iface_data = self.data.get("interfaces")
        for iface in iface_data:
            inventory.NetworkInterface(**iface)

    def test_cpu(self):
        cpu_data = self.data.get("cpu")
        inventory.CPU(**cpu_data)

    def test_disks(self):
        disk_data = self.data.get("disks")
        for disk in disk_data:
            inventory.Disk(**disk)

    def test_memory(self):
        pass


class TestDmi(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        # TODO load specific snippet of DMI info for different cases
        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            json_data = json.load(f)
            self.data = json_data.get("dmi")

    def test_bios(self):
        pass

    def test_cpu(self):
        pass

    def test_memory(self):
        pass


class TestExtraHardware(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        # TODO load specific snippet of DMI info for different cases
        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            json_data = json.load(f)
            self.data = json_data.get("extra")

    def test_interfaces(self):
        for name, values in self.data.get("network").items():
            nic_model = extra_hardware.NetworkAdapter.model_validate(values)

    def test_cpu(self):
        cpu_data = self.data.get("cpu")
        cpu_model = extra_hardware.CPU.model_validate(cpu_data)

    def test_physical_cpu(self):
        cpu_data = self.data.get("cpu")
        phys0_cpu_data = cpu_data.get("physical_0")
        phys_cpu_model = extra_hardware.PhysicalCPU.model_validate(phys0_cpu_data)

    def test_cpu_cache_per_core(self):
        # TODO: this is brittle and needs tests
        pass

    def test_disk(self):
        disk_data = self.data.get("disk").get("sda")
        disk_model = extra_hardware.Disk.model_validate(disk_data)

    def test_disks(self):
        disk_data = self.data.get("disk")
        disk_data.pop("logical")

        for name, values in disk_data.items():
            disk_model = extra_hardware.Disk.model_validate(values)

    def test_memory(self):
        pass

    def test_top_level(self):
        extra_hw_model = extra_hardware.InspectorExtraHardware.model_validate(self.data)


class TestPciDevices(base.BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_lookup_vendor_product(self):
        vendor_info = pci.PCI_MAP.lookup_vendor("10de")
        assert vendor_info.vendor_name == "NVIDIA Corporation"

    def test_lookup_product(self):
        device_info = pci.PCI_MAP.lookup_product(vendor_id="10de", product_id="1e30")
        assert device_info.product_name == "TU102GL [Quadro RTX 6000/8000]"

    def test_parse_pci_devices(self):
        nvidia_rtx_6000_data = {
            "vendor_id": "10de",
            "product_id": "1e30",
            "class": "030000",
            "revision": "a1",
            "bus": "0000:3b:00.0",
        }

        device_model = pci.PciDevice.model_validate(nvidia_rtx_6000_data)
        assert device_model.vendor_name == "NVIDIA Corporation"
        assert device_model.product_name == "TU102GL [Quadro RTX 6000/8000]"
        print(device_model.model_dump_json(indent=2))

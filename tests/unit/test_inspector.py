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

        with open("tests/unit/json_samples/inspector/inventory_gigaio01.json") as f:
            self.data = json.load(f)

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
    """Exercise DMI classs with real inspector data."""

    def setUp(self):
        super().setUp()
        # TODO load specific snippet of DMI info for different cases
        with open("tests/unit/json_samples/inspector/dmi_gigaio01.json") as f:
            self.data = json.load(f)

    #     def test_bios(self):
    #         pass

    def test_cpu(self):
        cpu_data = self.data.get("cpu")[0]
        dmi_model = dmi.CPU.model_validate(cpu_data)
        self.assertEqual(2300 * 10**6, dmi_model.current_speed)
        self.assertEqual(40, dmi_model.core_count)
        self.assertEqual(40, dmi_model.core_enabled)
        self.assertEqual(80, dmi_model.thread_count)


#     def test_memory(self):
#         pass


class TestDmiCpu(base.BaseTestCase):
    def setUp(self):
        super().setUp()

        self.data = {
            "Manufacturer": "Intel",
            "Version": "Intel(R) Xeon(R) Gold 6126 CPU @ 2.60GHz",
            "Current Speed": "2600 MHz",
            "Core Count": "12",
            "Core Enabled": "12",
            "Thread Count": "24",
        }

    def test_cpu_current_speed_hz(self):
        self.assertEqual(2600 * 10**6, dmi.CPU.current_speed_hz("2600 MHz"))
        self.assertEqual(2600 * 10**6, dmi.CPU.current_speed_hz("2.6 GHz"))

    def test_dmi_cpu(self):
        cpu_model = dmi.CPU.model_validate(self.data)
        print(cpu_model.model_dump_json(indent=2))
        self.assertEqual(2600 * 10**6, cpu_model.current_speed)


class TestExtraHardware(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        with open(
            "tests/unit/json_samples/inspector/extra_hardware_gigaio01.json"
        ) as f:
            self.data = json.load(f)

    def test_interfaces(self):
        for name, values in self.data.get("network").items():
            values["name"] = name
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
        disk_data["name"] = "sda"
        disk_model = extra_hardware.Disk.model_validate(disk_data)

    def test_disks(self):
        disk_data = self.data.get("disk")
        disk_data.pop("logical")

        for name, values in disk_data.items():
            values["name"] = name
            disk_model = extra_hardware.Disk.model_validate(values)

    def test_memory(self):
        mem_model = extra_hardware.Memory.model_validate(
            {"total": {"size": 274877906944}}
        )
        print(mem_model.model_dump_json(indent=2))

    def test_top_level(self):
        extra_hw_model = extra_hardware.InspectorExtraHardware.model_validate(self.data)


class TestPciDevices(base.BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_lookup_vendor(self):
        vendor_info = pci.PCI_MAP.lookup_vendor("10de")
        assert isinstance(vendor_info, pci.PciVendorInfo)
        assert vendor_info.vendor_name == "NVIDIA Corporation"

        self.assertRaises(KeyError, pci.PCI_MAP.lookup_vendor, "gggg")

    def test_lookup_product(self):
        device_info = pci.PCI_MAP.lookup_product(vendor_id="10de", product_id="1e30")
        assert isinstance(device_info, pci.PciProductInfo)
        assert device_info.device_name == "TU102GL [Quadro RTX 6000/8000]"

        # vendor isn't found
        self.assertRaises(KeyError, pci.PCI_MAP.lookup_product, "gggg", "1e30")

        # product isn't found
        self.assertRaises(KeyError, pci.PCI_MAP.lookup_product, "10de", "gggg")

        # neither are found
        self.assertRaises(KeyError, pci.PCI_MAP.lookup_product, "gggg", "gggg")

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

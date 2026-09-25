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

    def test_interface_without_vendor(self):
        """Interface copied verbatim from chi001 (ncar), which IPA reports without a vendor."""
        iface = inventory.NetworkInterface.model_validate(
            {
                "name": "enxbe3af2b6059f",
                "mac_address": "be:3a:f2:b6:05:9f",
                "has_carrier": True,
                "vendor": None,
                "product": None,
            }
        )
        self.assertIsNone(iface.vendor)
        self.assertIsNone(iface.product)

    def test_nvme_behind_scsi_interface(self):
        """sda copied verbatim from gh01 (ncar): an NVMe drive behind a SCSI HBA."""
        disk = inventory.Disk.model_validate(
            {
                "by_path": "/dev/disk/by-path/pci-0006:01:00.0-scsi-0:2:0:0",
                "hctl": "0:2:0:0",
                "model": "SAMSUNG MZTL21T9",
                "name": "/dev/sda",
                "rotational": False,
                "serial": "S6RCNG0Y600203",
                "size": 1920383410176,
                "vendor": "NVMe",
                "wwn": None,
                "wwn_vendor_extension": None,
                "wwn_with_extension": None,
            }
        )
        self.assertEqual("PCIe", disk.interface)

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

    def test_physical_cpu_stepping_arm(self):
        """physical_0 copied verbatim from gh01 (ncar, NVIDIA GH200)."""
        phys_cpu_model = extra_hardware.PhysicalCPU.model_validate(
            {
                "architecture": "aarch64",
                "boost": "disabled",
                "cores": 72,
                "flags": "fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm jscvt fcma lrcpc dcpop sha3 sm3 sm4 asimddp sha512 sve asimdfhm dit uscat ilrcpc flagm sb paca pacg dcpodp sve2 sveaes svepmull svebitperm svesha3 svesm4 flagm2 frint svei8mm svebf16 i8mm bf16 dgh bti",
                "l1d cache": "4.5 MiB (72 instances)",
                "l1i cache": "4.5 MiB (72 instances)",
                "l2 cache": "72 MiB (72 instances)",
                "l3 cache": "114 MiB (1 instance)",
                "max_Mhz": 3429,
                "min_Mhz": 81,
                "model": 0,
                "product": "Neoverse-V2",
                "stepping": "r0p0",
                "threads": 72,
                "threads_per_core": 1,
                "vendor": "ARM",
            }
        )
        self.assertEqual("r0p0", phys_cpu_model.stepping)

    def test_physical_cpu_stepping_x86(self):
        """physical_0 copied verbatim from P3-NVDIMM-001 (uc)."""
        phys_cpu_model = extra_hardware.PhysicalCPU.model_validate(
            {
                "architecture": "x86_64",
                "cores": 28,
                "family": 6,
                "flags": "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid dca sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb cat_l3 cdp_l3 invpcid_single intel_ppin ssbd mba ibrs ibpb stibp ibrs_enhanced tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid cqm mpx rdt_a avx512f avx512dq rdseed adx smap clflushopt clwb intel_pt avx512cd avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves cqm_llc cqm_occup_llc cqm_mbm_total cqm_mbm_local dtherm ida arat pln pts pku ospke avx512_vnni md_clear flush_l1d arch_capabilities",
                "l1d cache": "3.5 MiB (112 instances)",
                "l1i cache": "3.5 MiB (112 instances)",
                "l2 cache": "112 MiB (112 instances)",
                "l3 cache": "154 MiB (4 instances)",
                "max_Mhz": 4000,
                "min_Mhz": 1000,
                "model": 85,
                "product": "Intel(R) Xeon(R) Platinum 8276 CPU @ 2.20GHz",
                "stepping": 7,
                "threads": 28,
                "threads_per_core": 1,
                "vendor": "GenuineIntel",
            }
        )
        self.assertEqual("7", phys_cpu_model.stepping)

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

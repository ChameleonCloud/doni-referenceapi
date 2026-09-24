import json

from oslotest import base

from reference_transmogrifier.models import blazar, inspector, reference_repo


class ReferenceRepoNode(base.BaseTestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/r_api_nc35.json") as f:
            self.reference_node_json = json.load(f)

        with open("tests/unit/json_samples/blazar_nc35.json") as f:
            self.blazar_host_json = json.load(f)

        with open("tests/unit/json_samples/ironic_inspector_nc35.json") as f:
            self.ironic_inspector_node_json = json.load(f)

    def test_validate_current_data(self):
        """Validate that existing referenceapi data passes the validator."""
        reference_repo.Node.model_validate(self.reference_node_json)

    def test_find_gpus(self):
        pci_device_json = self.ironic_inspector_node_json.get("pci_devices")
        pci_list = [inspector.pci.PciDevice(**p) for p in pci_device_json]
        gpus_model = reference_repo.Node.find_gpu_from_pci(pci_list)

        self.assertEqual(1, gpus_model.gpu_count)
        self.assertEqual("TU102GL [Quadro RTX 6000/8000]", gpus_model.gpu_model)
        self.assertEqual("NVIDIA", gpus_model.gpu_vendor)

    def test_find_gpus_excludes_matrox_bmc(self):
        """Matrox BMC display devices copied verbatim from c01-22 and c02-01 (tacc)."""
        pci_list = [
            inspector.pci.PciDevice.model_validate(p)
            for p in [
                {
                    "bus": "0000:0a:00.0",
                    "class": "030000",
                    "product_id": "0534",
                    "revision": "01",
                    "vendor_id": "102b",
                },
                {
                    "bus": "0000:62:00.0",
                    "class": "030000",
                    "product_id": "0536",
                    "revision": "04",
                    "vendor_id": "102b",
                },
            ]
        ]
        gpus_model = reference_repo.Node.find_gpu_from_pci(pci_list)

        self.assertFalse(gpus_model.gpu)

    def test_find_gpus_excludes_ncar_builtin_display(self):
        """Display-class PCI devices copied verbatim from chi014 (ncar, zen5 grado).

        ASPEED is the BMC's VGA, and AMD 13c0 is the Zen 5 integrated graphics.
        """
        pci_list = [
            inspector.pci.PciDevice.model_validate(p)
            for p in [
                {
                    "bus": "0000:03:00.0",
                    "class": "030000",
                    "product_id": "2000",
                    "revision": "52",
                    "vendor_id": "1a03",
                },
                {
                    "bus": "0000:06:00.0",
                    "class": "030000",
                    "product_id": "13c0",
                    "revision": "d1",
                    "vendor_id": "1002",
                },
            ]
        ]
        gpus_model = reference_repo.Node.find_gpu_from_pci(pci_list)

        self.assertFalse(gpus_model.gpu)

    def test_storage_device_nvme_vendor(self):
        """sda on gh01 (ncar): an NVMe drive behind a SCSI HBA.

        Values from its inventory and extra hardware entries, and the wwn from
        /sys/block/sda/device/wwid on the node.
        """
        disk_model = reference_repo.StorageDevice.model_validate(
            {
                "device": "sda",
                "interface": "SAS",
                "media_type": "SSD",
                "model": "SAMSUNG MZTL21T9",
                "rev": "602Q",
                "serial": "S6RCNG0Y600203",
                "size": 1920000000000,
                "vendor": "NVMe",
                "wwn": "eui.36524330596002030025384700000001",
            }
        )
        self.assertIsNone(disk_model.vendor)

    def test_find_fpga(self):
        pci_device_json = [
            {
                "vendor_id": "10ee",
                "product_id": "d00c",
                "class": "120000",
                "revision": "00",
                "bus": "0000:af:00.0",
            },
            {
                "vendor_id": "8086",
                "product_id": "a182",
                "class": "010601",
                "revision": "09",
                "bus": "0000:00:17.0",
            },
        ]
        pci_list = [inspector.pci.PciDevice(**p) for p in pci_device_json]
        fpgas_model = reference_repo.Node.find_fpga_from_pci(pci_list)
        self.assertEqual("Alveo U280 Golden Image", fpgas_model.board_model)
        self.assertEqual("Xilinx", fpgas_model.board_vendor)

    def test_ami_bios_vendor(self):
        """BIOS vendor copied verbatim from chi001 (ncar, zen5 grado)."""
        self.assertEqual(
            reference_repo.ManufacturerEnum.ami,
            reference_repo.normalize_manufacturer("American Megatrends International, LLC."),
        )
        # The stored value must also be accepted.
        self.assertEqual(
            reference_repo.ManufacturerEnum.ami,
            reference_repo.normalize_manufacturer(reference_repo.ManufacturerEnum.ami.value),
        )

    def test_supermicro_chassis_name(self):
        """product_name copied verbatim from chi001 (ncar, zen5 grado).

        The DMI name has a space ("AS -3015MR") that the stored value doesn't.
        """
        supermicro = reference_repo.ChassisModelEnum.supermicro_3015mr_h10tnr
        chassis = reference_repo.Chassis(name="AS -3015MR-H10TNR (To be filled by O.E.M.)")
        self.assertEqual(supermicro, chassis.name)
        # The stored value must also be accepted.
        self.assertEqual(supermicro, reference_repo.Chassis(name=supermicro.value).name)

    def test_chassis_values_normalize_to_themselves(self):
        """Every stored chassis value must be accepted, since validate.py checks the generated files."""
        for chassis_model in reference_repo.ChassisModelEnum:
            chassis = reference_repo.Chassis(name=chassis_model.value)
            self.assertEqual(chassis_model, chassis.name)

    def test_find_processor(self):
        inspection_model = inspector.InspectorResult.model_validate(
            self.ironic_inspector_node_json
        )

        cpu_model = reference_repo.Node.find_processor_info(
            inspection_model.dmi.cpu, inspection_model.extra.cpu
        )

        self.assertEqual(32768, cpu_model.cache_l1i)
        self.assertEqual(32768, cpu_model.cache_l1d)
        self.assertEqual(2600 * 10**6, cpu_model.clock_speed)

    def test_find_network_adapters(self):
        inspection_model = inspector.InspectorResult.model_validate(
            self.ironic_inspector_node_json
        )
        nic_list = reference_repo.Node.find_network_adapters(
            inspection_model.extra.network
        )
        for n in nic_list:
            print(n.model_dump_json(indent=2))

    def _make_extra_nic(self, driver, name="eth0", link=True):
        return inspector.extra_hardware.NetworkAdapter(
            name=name,
            vendor="Mellanox",
            product="Some Product",
            driver=driver,
            serial="aa:bb:cc:dd:ee:ff",
            link=link,
        )

    def test_infiniband_false_when_no_ib_nics(self):
        nics = [self._make_extra_nic("mlx5_core", name="eth0")]
        nic_list = reference_repo.Node.find_network_adapters(nics)
        infiniband = any(nic.interface == "InfiniBand" for nic in nic_list)
        self.assertFalse(infiniband)

    def test_infiniband_true_when_ib_nic_present(self):
        nics = [
            self._make_extra_nic("mlx5_core", name="eth0"),
            self._make_extra_nic("ipoib", name="ib0"),
        ]
        nic_list = reference_repo.Node.find_network_adapters(nics)
        infiniband = any(nic.interface == "InfiniBand" for nic in nic_list)
        self.assertTrue(infiniband)

    def test_find_storage_devices(self):
        inspection_model = inspector.InspectorResult.model_validate(
            self.ironic_inspector_node_json
        )
        disk_list = reference_repo.Node.find_storage_devices(
            inspection_model.inventory.disks, inspection_model.extra.disk
        )

    def test_storage_serial_from_inventory(self):
        """Serial comes from inventory, even when SMART doesn't report one.

        Disk entries copied verbatim from P3-NVDIMM-001 (uc) introspection
        data. The extra hardware entry has no SMART/serial_number.
        """
        inv_disk = inspector.inventory.Disk.model_validate(
            {
                "by_path": "/dev/disk/by-path/pci-0000:48:00.0-sas-phy6-lun-0",
                "hctl": "0:0:0:0",
                "model": "KPM5XVUG960G",
                "name": "/dev/sdb",
                "rotational": False,
                "serial": "11G0A02GTP5F",
                "size": 960197124096,
                "vendor": "TOSHIBA",
                "wwn": "0x58ce38ee21498f29",
                "wwn_vendor_extension": None,
                "wwn_with_extension": "0x58ce38ee21498f29",
            }
        )
        extra_disk = inspector.extra_hardware.Disk.model_validate(
            {
                "name": "sdb",
                "Read Cache Disable": 0,
                "Write Cache Enable": 0,
                "model": "KPM5XVUG960G",
                "nr_requests": 256,
                "optimal_io_size": 0,
                "physical_block_size": 4096,
                "rev": "B02A",
                "rotational": 0,
                "scheduler": "mq-deadline",
                "scsi-id": "scsi-358ce38ee21498f29",
                "size": 960,
                "vendor": "TOSHIBA",
                "wwn-id": "wwn-0x58ce38ee21498f29",
            }
        )
        self.assertIsNone(extra_disk.serial)

        disk_list = reference_repo.Node.find_storage_devices([inv_disk], [extra_disk])

        self.assertEqual(1, len(disk_list))
        self.assertEqual("11G0A02GTP5F", disk_list[0].serial)

    def test_generate_data(self):
        blazar_info = blazar.Host(
            hypervisor_hostname="03129bbe-330c-4591-bc17-96d7e15d3e74",
            node_name="test_node_4",
            node_type="compute_skylake",
            placement_node="foo",
            placement_rack="bar",
        )

        inspection_model = inspector.InspectorResult.model_validate(
            self.ironic_inspector_node_json
        )

        output_node_model = reference_repo.Node.from_inspector_result(
            blazar_info, inspection_model
        )

        self.assertEqual("uefi", output_node_model.boot_mode)

    def test_manufacturer_values_normalize_to_themselves(self):
        """Every stored manufacturer value must be accepted, since validate.py checks the generated files."""
        for manufacturer in reference_repo.ManufacturerEnum:
            self.assertEqual(
                manufacturer, reference_repo.normalize_manufacturer(manufacturer.value)
            )

    def test_validate_kioxia_storage_device(self):
        """storage_devices entry copied verbatim from c552-pvc02 (tacc) in the reference repo."""
        disk_model = reference_repo.StorageDevice.model_validate(
            {
                "device": "nvme1n1",
                "humanized_size": "3840 GB",
                "interface": "PCIe",
                "media_type": "SSD",
                "model": "Dell DC NVMe CD8 U.2 3.84TB",
                "rev": "2.0.0",
                "serial": "Z3W0A0PATSRJ",
                "size": 3840000000000,
                "vendor": "kioxia",
                "wwn": "eui.01000000000000088ce38ee3009e8265",
            }
        )
        self.assertEqual(reference_repo.ManufacturerEnum.kioxia, disk_model.vendor)
        self.assertEqual("Kioxia", disk_model.vendor.value)

    def test_node_mode_absent_by_default(self):
        node = reference_repo.Node.model_validate(self.reference_node_json)
        self.assertIsNone(node.node_mode)

        dumped = node.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        self.assertNotIn("node_mode", dumped)

    def test_node_mode_vm_only_round_trips(self):
        node_json = dict(self.reference_node_json, node_mode="vm_only")
        node = reference_repo.Node.model_validate(node_json)
        self.assertEqual(reference_repo.NodeModeEnum.vm_only, node.node_mode)

        dumped = node.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        self.assertEqual("vm_only", dumped["node_mode"])


class VmFlavorModel(base.BaseTestCase):
    def test_validates_non_gpu_flavor(self):
        flavor_json = {
            "type": "vm_flavor",
            "uid": "m1.large",
            "vcpus": 4,
            "ram_size": 8589934592,
            "humanized_ram_size": "8 GiB",
            "disk_size": 40000000000,
            "humanized_disk_size": "40 GB",
            "gpu": {"gpu": False},
            "su_cost_per_hour": 0.95,
        }
        flavor = reference_repo.VmFlavor.model_validate(flavor_json)
        self.assertEqual("m1.large", flavor.uid)
        self.assertFalse(flavor.gpu.gpu)
        self.assertEqual(0.95, flavor.su_cost_per_hour)

    def test_validates_gpu_mig_slice_flavor(self):
        flavor_json = {
            "type": "vm_flavor",
            "uid": "g1.h100.mig.1",
            "vcpus": 8,
            "ram_size": 17179869184,
            "disk_size": 40000000000,
            "gpu": {
                "gpu": True,
                "gpu_count": 1,
                "gpu_allocation": "mig_slice",
                "gpu_mig_profile": "1g.12gb",
            },
            "openstack_properties": {"resources:VGPU": "1"},
            "su_cost_per_hour": 16.0,
        }
        flavor = reference_repo.VmFlavor.model_validate(flavor_json)
        self.assertTrue(flavor.gpu.gpu)
        self.assertEqual(
            reference_repo.GpuAllocationEnum.mig_slice, flavor.gpu.gpu_allocation
        )
        self.assertEqual("1g.12gb", flavor.gpu.gpu_mig_profile)
        self.assertEqual(16.0, flavor.su_cost_per_hour)

    def test_su_cost_per_hour_defaults_to_none_when_absent(self):
        flavor_json = {
            "type": "vm_flavor",
            "uid": "m1.tiny",
            "gpu": {"gpu": False},
        }
        flavor = reference_repo.VmFlavor.model_validate(flavor_json)
        self.assertIsNone(flavor.su_cost_per_hour)

        dumped = flavor.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        self.assertNotIn("su_cost_per_hour", dumped)

    def test_su_cost_per_hour_accepts_explicit_null(self):
        flavor_json = {
            "type": "vm_flavor",
            "uid": "m1.tiny",
            "gpu": {"gpu": False},
            "su_cost_per_hour": None,
        }
        flavor = reference_repo.VmFlavor.model_validate(flavor_json)
        self.assertIsNone(flavor.su_cost_per_hour)


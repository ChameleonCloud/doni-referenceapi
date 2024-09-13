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

    def test_find_storage_devices(self):
        inspection_model = inspector.InspectorResult.model_validate(
            self.ironic_inspector_node_json
        )
        disk_list = reference_repo.Node.find_storage_devices(
            inspection_model.inventory.disks, inspection_model.extra.disk
        )

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

        print(output_node_model.model_dump_json(indent=2))

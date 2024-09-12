import json

from oslotest import base

import reference_transmogrifier.reference_api
from reference_transmogrifier.models import inspector, reference_repo


class TestIronicInspectorModel(base.BaseTestCase):
    """Test methods for generating referenceapi info."""

    def setUp(self):
        super().setUp()
        with open("tests/unit/json_samples/inspector/gigaio01.json") as f:
            self.ironic_inspector_node_json = json.load(f)

        self.model = inspector.InspectorResult(**self.ironic_inspector_node_json)

    def test_get_nic_info(self):
        ifaces = self.model.get_referenceapi_network_adapters()
        for iface in ifaces:
            reference_repo.NetworkAdapter.model_validate(iface)

    def test_get_gpu_info(self):
        result = self.model.get_referenceapi_gpu_info()
        reference_repo.GPU.model_validate(result)
        print(result)

    def test_get_cpu_info(self):
        result = self.model.get_referenceapi_cpu_info()
        reference_repo.Processor.model_validate(result)

    def test_get_disks(self):
        result = self.model.get_referenceapi_disks()
        self.assertEqual("D3DJ004", result[0].rev)

    def test_get_pci_devices(self):
        for d in self.model.pci_devices:
            print(d.model_dump_json(indent=2))


class ReferenceRepoNode(base.BaseTestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/r_api_nc35.json") as f:
            self.reference_node_json = json.load(f)

        # with open("tests/unit/json_samples/blazar_p3-ssd-010.json") as f:
        with open("tests/unit/json_samples/blazar_nc35.json") as f:
            self.blazar_host_json = json.load(f)

        # with open("tests/unit/json_samples/ironic_inspector_p3-ssd-010.json") as f:
        with open("tests/unit/json_samples/ironic_inspector_nc35.json") as f:
            self.ironic_inspector_node_json = json.load(f)

    def test_validate_current_data(self):
        """Validate that existing referenceapi data passes the validator."""
        reference_repo.Node.model_validate(self.reference_node_json)

    def test_generate_data(self):
        current_data_rep = reference_repo.Node(**self.reference_node_json)

        output_data = reference_transmogrifier.reference_api.generate_rapi_json(
            blazar_host=self.blazar_host_json,
            inspection_item=self.ironic_inspector_node_json,
        )
        output_data_rep = reference_repo.Node(**output_data)
        print(output_data_rep.model_dump_json(indent=2))

import json

import reference_transmogrifier.reference_api
from reference_transmogrifier.models import ironic_inspector, reference_repo
from tests.unit import base


class TestIronicInspectorModel(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            self.ironic_inspector_node_json = json.load(f)

    def test_inspector_extra_hardware(self):
        extra = self.ironic_inspector_node_json.get("extra")
        ironic_inspector.InspectorExtraHardware.model_validate(extra)

    def test_inspector_result(self):
        ironic_inspector.InspectorResult.model_validate(self.ironic_inspector_node_json)

    def test_get_nic_info(self):
        model = ironic_inspector.InspectorResult(**self.ironic_inspector_node_json)
        ifaces = model.extra.network
        for name, value in ifaces.items():
            result = value.as_reference_iface(name)
            reference_repo.NetworkAdapter.model_validate(result)


class ReferenceRepoNode(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/r_api_nc35.json") as f:
            self.reference_node_json = json.load(f)

        # with open("tests/unit/json_samples/blazar_p3-ssd-010.json") as f:
        with open("tests/unit/json_samples/blazar_gigaio01.json") as f:
            self.blazar_host_json = json.load(f)

        # with open("tests/unit/json_samples/ironic_inspector_p3-ssd-010.json") as f:
        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            self.ironic_inspector_node_json = json.load(f)

    def test_validate_node(self):
        """Validate that existing referenceapi data passes the validator."""
        reference_repo.Node.model_validate(self.reference_node_json)

    def test_generate_data(self):
        output_data = reference_transmogrifier.reference_api.generate_rapi_json(
            blazar_host=self.blazar_host_json,
            inspection_item=self.ironic_inspector_node_json,
        )

        reference_repo.Node.model_validate(output_data)
        output_node = reference_repo.Node(**output_data)
        print(output_node.model_dump_json(indent=2))

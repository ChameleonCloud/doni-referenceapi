import json

import reference_transmogrifier.reference_api
from reference_transmogrifier.models import reference_repo
from tests.unit import base


class ReferenceRepoNode(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/r_api_p3-ssd-010.json") as f:
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
        print(json.dumps(output_data, indent=2))

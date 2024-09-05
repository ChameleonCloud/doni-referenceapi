import json

from reference_transmogrifier.models import reference_repo
from tests.unit import base


class ReferenceRepoNode(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/rapi_p3-ssd-010.json") as f:
            self.node_json = json.load(f)

    def test_validate_node(self):
        """Validate that existing referenceapi data passes the validator."""
        output_node = reference_repo.Node(**self.node_json)

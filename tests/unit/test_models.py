import json

import reference_transmogrifier.reference_api
from reference_transmogrifier.models import inspector, reference_repo
from reference_transmogrifier.models.inspector import extra_hardware
from tests.unit import base


class TestIronicInspectorExtraData(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            self.ironic_inspector_node_json = json.load(f)

        self.extra_data = self.ironic_inspector_node_json.get("extra")

    def test_inspector_extra_hardware(self):
        extra_hardware.InspectorExtraHardware.model_validate(self.extra_data)

    def test_extra_data_physical_cpu(self):
        extra_cpu_json = self.extra_data.get("cpu").get("physical_0")

        proc_model = extra_hardware.PhysicalCPU(**extra_cpu_json)
        # TODO make sure we're reporting per-core cache info here
        # assert proc_model.l1i_cache == "32kb in int"
        # assert proc_model.l1d_cache == "48kb in int"
        # assert proc_model.l2_cache == "48kb in int"
        # assert proc_model.l3_cache == "48kb in int"

    def test_extra_data_cpu(self):
        extra_cpu_json = self.extra_data.get("cpu")
        proc_model = extra_hardware.CPU(**extra_cpu_json)

    def test_extra_data_disk(self):
        extra_json = self.extra_data.get("disk").get("sda")
        model = extra_hardware.Disk(**extra_json)
        print(model.model_dump_json(indent=2))


class TestIronicInspectorModel(base.TestCase):
    def setUp(self):
        super().setUp()

        with open("tests/unit/json_samples/ironic_inspector_gigaio01.json") as f:
            self.ironic_inspector_node_json_extra = json.load(f)

        with open(
            "tests/unit/json_samples/ironic_inspector_gigaio01_noextra.json"
        ) as f:
            self.ironic_inspector_node_json_noextra = json.load(f)

    def test_fullmodel_extra(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_extra)

    def test_fullmodel_noextra(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_noextra)

    def test_get_nic_info(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_noextra)
        ifaces = model.get_referenceapi_network_adapters()
        for iface in ifaces:
            reference_repo.NetworkAdapter.model_validate(iface)

    def test_get_cpu_info(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_noextra)
        result = model.get_referenceapi_cpu_info()
        reference_repo.Processor.model_validate(result)

    def test_get_disks(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_noextra)
        result = model.get_referenceapi_disks()
        assert result[0].rev is None

    def test_get_disks_extra(self):
        model = inspector.InspectorResult(**self.ironic_inspector_node_json_extra)
        result = model.get_referenceapi_disks()
        assert result[0].rev == "J004"


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

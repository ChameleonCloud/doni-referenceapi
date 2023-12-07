import json
from uuid import uuid4

from doni_referenceapi.models.referenceapi import Node

FAKE_NODE_UUID = uuid4()
FAKE_NODE_NAME = "test_node_1234"
FAKE_NODE_TYPE = "test_node_type"

FAKE_NETWORK_ADAPTER = {"mac": "aa:bb:cc:dd:ee:ff"}

FAKE_STORAGE_DEVICE = {
    "device": "fakedevicename1",
    "interface": "PCIe",
    "media_type": "SSD",
    "size": "960197124096",
}

FAKE_PROCESSOR = {
    "cache_l1": 3200000,
    "cache_l2": 51200000,
    "cache_l3": 61440000,
    "clock_speed": 2300000000,
    "instruction_set": "x86-64",
    "model": "Intel(R) Xeon(R) Platinum 8380 CPU @ 2.30GHz",
    "vendor": "Intel",
}


def test_sanity():
    external_data = {
        "uid": FAKE_NODE_UUID,
        "node_name": FAKE_NODE_NAME,
        "node_type": FAKE_NODE_TYPE,
        "network_adapters": [FAKE_NETWORK_ADAPTER],
        "storage_devices": [FAKE_STORAGE_DEVICE],
        "processor": FAKE_PROCESSOR,
    }
    node = Node(**external_data)
    print(json.dumps(node.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    test_sanity()

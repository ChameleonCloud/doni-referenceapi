import json
from uuid import uuid4

from doni_referenceapi.models import referenceapi as rapi

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
    "cache_l1": 123456,
    "cache_l2": 35135138,
    "cache_l3": 73133516,
    "clock_speed": 3518882187,
    "instruction_set": "x86-64",
    "model": "Fake Vendor with Fake Family and Fake model",
    "vendor": "Intel",
}

FAKE_ARCHITECTURE = {
    "platform_type": "x86-64",
    "sockets": 2,
    "cores": 24,
    "threads": 48,
}
FAKE_BIOS = {
    "release_date": "2013-11-02",
    "vendor": "fake_bios_vendor",
    "version": "fake_version_string",
}
FAKE_CHASSIS = {
    "manufacturer": "fake_manufacturer_string",
    "name": "fake_chassis_name",
}
FAKE_MAIN_MEMORY = {
    "ram_size": 256000000000,
}

FAKE_PLACEMENT = {}


def test_processor():
    test_dict = FAKE_PROCESSOR.copy()
    proc = rapi.Processor(**test_dict)
    assert proc.clock_speed == 3518882187

    # test with string
    test_dict["clock_speed"] = "982 mhz"
    proc = rapi.Processor(**test_dict)
    assert proc.clock_speed == 982 * 10**6


def test_architecture():
    rapi.Architecture(**FAKE_ARCHITECTURE)


def test_bios():
    rapi.Bios(**FAKE_BIOS)


def test_chassis():
    rapi.Chassis(**FAKE_CHASSIS)


def test_main_memory():
    rapi.MainMemory(**FAKE_MAIN_MEMORY)


def test_placement():
    rapi.Placement(**FAKE_PLACEMENT)


def test_sanity():
    external_data = {
        "uid": FAKE_NODE_UUID,
        "node_name": FAKE_NODE_NAME,
        "node_type": FAKE_NODE_TYPE,
        "network_adapters": [FAKE_NETWORK_ADAPTER],
        "storage_devices": [FAKE_STORAGE_DEVICE],
        "processor": FAKE_PROCESSOR,
        "bios": FAKE_BIOS,
        "architecture": FAKE_ARCHITECTURE,
        "chassis": FAKE_CHASSIS,
        "main_memory": FAKE_MAIN_MEMORY,
        "placement": FAKE_PLACEMENT,
    }
    node = rapi.Node(**external_data)
    print(
        json.dumps(
            node.model_dump(
                mode="json",
                exclude_unset=True,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    test_sanity()

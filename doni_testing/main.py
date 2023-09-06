import json

import ironic_inspector_client
import jsonschema
from doniclient.v1.client import Client as DoniClient
from keystoneauth1.adapter import Adapter
from openstack.connection import Connection

# from ironicclient.client import Client as IronicClient


NODE_UUID="7ed407a7-98dd-4708-bf32-9e0ab50c9f68"

def get_inspection_api(session=None, node_uuid=None):
    ic = ironic_inspector_client.ClientV1(session=session)
    raise NotImplemented


def get_inspection_json(*args, **kwargs):
    data = None
    with open("test_data/p3-ssd-010.json") as f:
        data = json.load(f)
    return data

def get_hw_json(*args, **kwargs):
    data = None
    with open("test_data/doni_p3-ssd-010.json") as f:
        data = json.load(f)
    return data

def get_hardware_item(session=None, node_uuid=None):
    doni = DoniClient(Adapter(
        session=session,
        service_type="inventory",
        interface="public",
        ))
    item = doni.get_by_uuid(node_uuid)
    return item


def generate_rapi_json(doni_item, inspection_item):
    doni_properties = doni_item.get("properties", {})

    dmi_data = inspection_item.get("dmi", {})
    dmi_cpu=dmi_data.get("cpu")


    data = {
        "uid": doni_item.get("uuid"),
        "node_name": doni_item.get("name"),
        "node_type": doni_properties.get("node_type"),
        "architecture": {
            "platform_type": inspection_item.get("cpu_arch"),
            "smp_size": len(dmi_cpu),
            "smt_size": inspection_item.get("cpus"),
        },
        "processor": {
            "model": dmi_cpu[0].get("Version"),
            "vendor": dmi_cpu[0].get("Manufacturer")
        },
        "main_memory": {},
        "network_adapters": [],
        "storage_devices": [],
    }

    return data

def main():
    # conn = Connection(cloud="uc_admin")
    # doni_item = get_hardware_item(session=conn.session, node_uuid=NODE_UUID)


    with open("doni_testing/rapi/rapi.jsonschema") as f:
        schema = json.load(f)

    with open("test_data/rapi_p3-ssd-010.json") as f:
        rapi_data = json.load(f)

    # sanity check, make sure schema validates existint rAPI data
    jsonschema.validate(instance=rapi_data, schema=schema)

    doni_item = get_hw_json(node_uuid=NODE_UUID)
    inspection_dict = get_inspection_json(node_uuid=NODE_UUID)

    # generate and then validate data we parse from Doni and inspection
    generated_data = generate_rapi_json(doni_item=doni_item, inspection_item=inspection_dict)
    jsonschema.validate(instance=generated_data, schema=schema)











if __name__ == "__main__":
    main()

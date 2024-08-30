import json
from humanize import naturalsize
import math
from urllib.request import urlretrieve
import re
import ssl

import ironic_inspector_client
import jsonschema
from doniclient.v1.client import Client as DoniClient
from keystoneauth1.adapter import Adapter
from openstack.connection import Connection

# from ironicclient.client import Client as IronicClient


#NODE_UUID="7ed407a7-98dd-4708-bf32-9e0ab50c9f68"
NODE_UUID="d389fc04-f030-425d-8556-55b8d9ec12eb"

def parse_vendor_file(file_path):
    data = {}
    
    current_vendor_id = None
    current_device_id = None
    
    with open(file_path, 'r') as file:
        for line in file:
            line = line.rstrip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Detect the indentation level
            indent_level = len(line) - len(line.lstrip())
            line = line.lstrip()

            # Vendor line (no indentation)
            if indent_level == 0:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    current_vendor_id, vendor_name = parts
                    data[current_vendor_id] = {'vendor_name': vendor_name, 'devices': {}}
                    
            # Device line (single level of indentation)
            elif indent_level == 1 or line.startswith('\t'):
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    current_device_id, device_name = parts
                    if current_vendor_id is not None:
                        data[current_vendor_id]['devices'][current_device_id] = {'device_name': device_name, 'subsystems': {}}
                        
            # Subsystem line (double level of indentation)
            elif indent_level == 2 or line.startswith('\t\t'):
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    subvendor_id, subdevice_id, subsystem_name = parts
                    if current_vendor_id is not None and current_device_id is not None:
                        subsystem_key = (subvendor_id, subdevice_id)
                        data[current_vendor_id]['devices'][current_device_id]['subsystems'][subsystem_key] = subsystem_name

    return data

def get_inspection_api(session=None, node_uuid=None):
    ic = ironic_inspector_client.ClientV1(session=session)
    raise NotImplemented

def get_inspection_json(*args, **kwargs):
    data = None
    with open("test_data/gigaio01-inspect.json") as f:
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
    dmi_bios=dmi_data.get("bios", {})
    
    inspection_inventory = inspection_item.get("inventory")
    memory_data = inspection_inventory.get("memory", {})

    cpu_version = dmi_cpu[0].get("Signature").split(", ")

    # get cpu speed and convert to Hz without
    cpu_speed, cpu_speed_unit = dmi_cpu[0].get("Current Speed").split()

    # Convert the numeric part to an integer and multiply by 1,000,000
    if cpu_speed_unit == "MHz":
        cpu_speed_hz = int(cpu_speed) * 1_000_000

    base2_ram_size = 2**round(math.log2(memory_data.get("total")))

    data = {
        "uid": doni_item.get("uuid"),
        "node_name": doni_item.get("name"),
        "node_type": doni_properties.get("node_type"),
        "architecture": {
            "platform_type": inspection_item.get("cpu_arch"),
            "smp_size": len(dmi_cpu),
            "smt_size": inspection_item.get("cpus"),
        },
        "bios": {
            "release_date": dmi_bios.get("Release Date"),
            "vendor": dmi_bios.get("Vendor"),
            "version": dmi_bios.get("Version")
        },
        "infiniband": False, #TODO detect this
        "processor": {
            "clock_speed": cpu_speed_hz,
            "instruction_set": inspection_inventory.get("cpu").get("architecture").replace("_", "-"),
            "model": dmi_cpu[0].get("Version"),
            "vendor": dmi_cpu[0].get("Manufacturer"),
            "version": '{} {}'.format(cpu_version[2], cpu_version[3])
        },
        "main_memory": {
            "ram_size": memory_data.get("total"),
            # humanize and remove decimal with regex
            "humanized_ram_size": re.sub(r'(\d+)\.\d+', r'\1', naturalsize( base2_ram_size, binary=True ) ),
        },
        "monitoring": { #TODO detect this
            "wattmeter": False
        },
        "network_adapters": [],
        "storage_devices": [],
        "supported_job_types": { #TODO detect this?
            "besteffort": False,
            "deploy": True,
            "virtual": "ivt"
        },
        "type": "node" #TODO detect this?
    }

    for iface in inspection_inventory.get("interfaces", []):
        vendor_id = iface.get("vendor")[2:]
        product_id = iface.get("product")[2:]
        vendor_info = pci_lookup[vendor_id]
        device_info = vendor_info['devices'].get(product_id)

        rapi_interface = {
            "device": iface.get("name"),
            "interface": "Ethernet", #TODO detect this
            "mac": iface.get("mac_address"),
            "enabled": None,
            "vendor": vendor_info.get("vendor_name"),
            "management": None,
            "model": device_info["device_name"]
        }

        # if the interface address is the same as the bmc address, then 
        # it must be the management interface
        if iface.get("ipv4_address") == inspection_inventory.get("bmc_address"):
            rapi_interface["management"] = True
        else:
            rapi_interface["management"] = False

        # if ironic inspection gets an ip address, then the interface
        # is enabled in neutron
        if iface.get("ipv4_address"):
            rapi_interface["enabled"] = True
        else:
            rapi_interface["enabled"] = False

        data["network_adapters"].append(rapi_interface)

    for disk in inspection_inventory.get("disks", []):
        rapi_disk = {
            "name": disk.get("name"),
            "model": disk.get("model"),
            "size": disk.get("size"),
            # humanize and remove decimal with regex
            "humanized_size": re.sub(r'(\d+)\.\d+', r'\1', naturalsize( disk.get("size"), binary=False ) ),
            "interface": "UNKNOWN"
        }

        if disk.get("rotational") == False:
            rapi_disk["media_type"]="SSD"
        elif disk.get("rotational") == True:
            rapi_disk["media_type"]="Rotational"
        else:
            rapi_disk["media_type"]="UNKNOWN"

        data["storage_devices"].append(rapi_disk)

    # pci_devs = get_pci_dev_from_vendor_file( inspection_item.get("pci_devices"), "pci.ids")

    for pcidev in inspection_item.get("pci_devices"):
        vendor_id = pcidev.get("vendor_id")
        product_id = pcidev.get("product_id")
        vendor_info = pci_lookup[vendor_id]
        device_info = vendor_info['devices'].get(product_id)
        if not device_info:
            # print("{} Device Lookup failed ({}:P{})".format(vendor_info["vendor_name"], vendor_id, product_id))
            print("WARNING: PCI device {}:{} could not be identified".format(vendor_id, product_id))
        # else:
        #     print("{}:{} == {} | {}".format(vendor_id, product_id, vendor_info["vendor_name"], device_info["device_name"]))

    return data

pci_lookup = parse_vendor_file("pci.ids")

def main():
    # conn = Connection(cloud="uc_admin")
    # doni_item = get_hardware_item(session=conn.session, node_uuid=NODE_UUID)

    # Download PCI Vendor and Device Idintification from https://pci-ids.ucw.cz
    urlretrieve("http://pci-ids.ucw.cz/v2.2/pci.ids", "pci.ids")

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

    with open("output_file_test.json", "w+") as f:
        json.dump(generated_data, f, indent=2, sort_keys=True)

if __name__ == "__main__":
    main()

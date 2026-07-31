#!/usr/bin/env python3
"""Convert lshw JSON hardware reports to reference-repository node format.

Usage:
    lshw_to_refapi.py --node-type gpu_h100 [--input-dir tmp/] [--input a.json b.json]
                      [--output-dir ../reference-repository] [--site kvm] [--node-mode vm_only]
"""

import argparse
import json
import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _find(node, *, cls=None, id_prefix=None):
    return [
        n for n in _walk(node)
        if (cls is None or n.get("class") == cls)
        and (id_prefix is None or n.get("id", "").startswith(id_prefix))
    ]


def _vendor(name: str) -> str | None:
    if not name:
        return None
    try:
        from reference_transmogrifier.models.reference_repo import normalize_manufacturer
        return normalize_manufacturer(name).value
    except (ImportError, AssertionError):
        return name.strip() or None


def _parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    from datetime import datetime
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d %Y"):
        try:
            return datetime.strptime(date_str.lstrip("0"), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_clock_from_model(product: str) -> int | None:
    """Extract nominal clock from CPU model string, e.g. '@ 2.30GHz' → 2300000000."""
    import re
    m = re.search(r"@\s*([\d.]+)\s*GHz", product, re.IGNORECASE)
    return int(float(m.group(1)) * 1_000_000_000) if m else None


def extract_bios(lshw: dict) -> dict:
    for core in lshw.get("children", []):
        if core.get("id") == "core":
            for child in core.get("children", []):
                if child.get("id") == "firmware":
                    return {
                        "release_date": _parse_date(child.get("date")),
                        "vendor": _vendor(child.get("vendor", "")),
                        "version": str(child.get("version", "")),
                    }
    return {}


def extract_chassis(lshw: dict) -> dict:
    # Strip SKU suffix: "PowerEdge R630 (SKU=...)" → "PowerEdge R630"
    name = lshw.get("product", "").split("(")[0].strip()
    return {
        "manufacturer": _vendor(lshw.get("vendor", "")),
        "name": name or None,
        "serial": lshw.get("serial"),
    }


def extract_architecture(lshw: dict) -> dict:
    cpus = _find(lshw, cls="processor", id_prefix="cpu")
    threads = sum(int(c.get("configuration", {}).get("threads", 0)) for c in cpus)
    return {"platform_type": "x86_64", "smp_size": len(cpus), "smt_size": threads}


def extract_processor(lshw: dict) -> dict:
    cpus = _find(lshw, cls="processor", id_prefix="cpu")
    if not cpus:
        return {}
    cpu0 = cpus[0]
    cores = int(cpu0.get("configuration", {}).get("cores", 1))

    caches = {}
    for c in _find(cpu0, cls="memory"):
        desc = c.get("description", "").lower()
        if "l1" in desc:
            caches["l1"] = c.get("size")
        elif "l2" in desc:
            caches["l2"] = c.get("size")
        elif "l3" in desc:
            caches["l3"] = c.get("size")

    product = cpu0.get("product", "")
    # lshw "size" reflects current (possibly throttled) frequency; prefer nominal from model name
    clock_speed = _parse_clock_from_model(product) or cpu0.get("size")

    result = {
        "clock_speed": clock_speed,
        "instruction_set": "x86_64",
        "model": product,
        "vendor": _vendor(cpu0.get("vendor", "")),
    }
    # lshw reports L1 as a unified per-socket total; split evenly across d/i per core
    if caches.get("l1"):
        per_core = caches["l1"] // cores // 2
        result["cache_l1d"] = per_core
        result["cache_l1i"] = per_core
    if caches.get("l2"):
        result["cache_l2"] = caches["l2"] // cores
    if caches.get("l3"):
        result["cache_l3"] = caches["l3"]
    return result


def extract_memory(lshw: dict) -> dict:
    mem_nodes = [
        n for n in _find(lshw, cls="memory")
        if n.get("id", "").startswith("memory") and (n.get("size") or 0) > 1_000_000_000
    ]
    if mem_nodes:
        total = mem_nodes[0]["size"]
    else:
        total = sum(
            n["size"] for n in _find(lshw, cls="memory")
            if n.get("id", "").startswith("bank") and n.get("size")
        )
    return {"humanized_ram_size": f"{total // 2**30} GiB", "ram_size": total}


def extract_network_adapters(lshw: dict) -> list:
    adapters = []
    for net in _find(lshw, cls="network"):
        mac = net.get("serial")
        if not mac:
            continue
        cfg = net.get("configuration", {})
        caps = net.get("capabilities", {})
        rate = net.get("size") or net.get("capacity")

        iface = "InfiniBand" if (
            "infiniband" in caps or "infiniband" in net.get("description", "").lower()
        ) else "Ethernet"

        logicalname = net.get("logicalname")
        if isinstance(logicalname, list):
            logicalname = logicalname[0]

        entry = {
            "device": logicalname,
            "driver": cfg.get("driver") or None,
            "enabled": not net.get("disabled", False),
            "interface": iface,
            "mac": mac,
            "model": net.get("product") or None,
            "rate": rate or None,
            "vendor": _vendor(net.get("vendor", "")) if net.get("vendor") else None,
        }
        adapters.append({k: v for k, v in entry.items() if v is not None})

    return sorted(adapters, key=lambda a: a.get("mac", ""))


def extract_gpu(lshw: dict) -> dict:
    gpu_devices = [
        d for d in _find(lshw, cls="display")
        if "matrox" not in d.get("vendor", "").lower()
    ]
    if not gpu_devices:
        return {"gpu": False}

    def _pci_bus(device):
        parts = device.get("handle", "").split(":")
        return parts[2] if len(parts) >= 4 else device.get("handle", "")

    # H100 and similar GPUs expose multiple PCIe functions per physical device;
    # count by unique bus number to get the physical GPU count.
    unique_buses = {_pci_bus(d) for d in gpu_devices}
    first = gpu_devices[0]
    return {
        "gpu": True,
        "gpu_count": len(unique_buses),
        "gpu_model": first.get("product") or None,
        "gpu_vendor": _vendor(first.get("vendor", "")) or None,
    }


def extract_storage(lshw: dict) -> list:
    _SKIP_DESC = frozenset({"dvd-ram writer", "dvd-rom", "cd-rom writer"})
    devices = []
    for disk in _find(lshw, cls="disk"):
        size = disk.get("size")
        if not size or disk.get("description", "").lower() in _SKIP_DESC:
            continue

        handle = disk.get("handle", "")
        serial = disk.get("serial")
        if handle.startswith("GUID:"):
            wwn = handle[5:]
        elif serial:
            wwn = f"serial-{serial}"
        else:
            wwn = f"disk-{len(devices)}"

        logicalname = disk.get("logicalname")
        if isinstance(logicalname, list):
            logicalname = logicalname[0]

        entry = {
            "device": logicalname or disk.get("id"),
            "humanized_size": f"{size // 10**9} GB",
            "model": disk.get("product") or disk.get("description") or "unknown",
            "rev": disk.get("version") or None,
            "serial": serial or None,
            "size": size,
            "wwn": wwn,
        }
        devices.append({k: v for k, v in entry.items() if v is not None})
    return devices


def lshw_to_node(lshw: dict, node_type: str, node_mode: str) -> dict:
    nics = extract_network_adapters(lshw)
    node = {
        "architecture": extract_architecture(lshw),
        "bios": {k: v for k, v in extract_bios(lshw).items() if v is not None},
        "chassis": {k: v for k, v in extract_chassis(lshw).items() if v is not None},
        "gpu": {k: v for k, v in extract_gpu(lshw).items() if v is not None},
        "infiniband": any(a.get("interface") == "InfiniBand" for a in nics),
        "main_memory": extract_memory(lshw),
        "monitoring": {"wattmeter": False},
        "network_adapters": nics,
        "node_mode": node_mode,
        "node_name": lshw.get("id"),
        "node_type": node_type,
        "processor": {k: v for k, v in extract_processor(lshw).items() if v is not None},
        "storage_devices": extract_storage(lshw),
        "supported_job_types": {"besteffort": False, "deploy": True, "virtual": "ivt"},
        "type": "node",
        "uid": lshw.get("configuration", {}).get("uuid"),
    }
    return {k: v for k, v in node.items() if v is not None}


def write_node(node: dict, output_dir: pathlib.Path, site: str) -> pathlib.Path:
    nodes_dir = (
        output_dir / "data" / "chameleoncloud" / "sites" / site
        / "clusters" / "chameleon" / "nodes"
    )
    nodes_dir.mkdir(parents=True, exist_ok=True)
    out_path = nodes_dir / f"{node['uid']}.json"
    out_path.write_text(json.dumps(node, indent=2, sort_keys=True) + "\n")
    return out_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert lshw JSON reports to reference-repository node format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-dir", type=pathlib.Path, default=_REPO_ROOT / "tmp", metavar="DIR",
        help="Directory of lshw JSON files",
    )
    input_group.add_argument(
        "--input", nargs="+", type=pathlib.Path, metavar="FILE",
        help="One or more lshw JSON files",
    )
    parser.add_argument(
        "--output-dir", type=pathlib.Path, default=_REPO_ROOT.parent / "reference-repository",
        metavar="DIR", help="Root of the reference-repository checkout",
    )
    parser.add_argument("--site", default="kvm", help="Site name in the reference-repository")
    parser.add_argument(
        "--node-type", required=True, metavar="TYPE",
        help="Node type (e.g. gpu_h100, compute_haswell). Run once per node-type batch.",
    )
    parser.add_argument(
        "--node-mode", default="vm_only", metavar="MODE",
        help="Node mode written to every output node",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        from reference_transmogrifier.models.reference_repo import NodeTypeEnum
    except ImportError:
        pass
    else:
        try:
            NodeTypeEnum(args.node_type)
        except ValueError:
            valid = ", ".join(sorted(e.value for e in NodeTypeEnum))
            print(f"error: invalid --node-type {args.node_type!r}\nvalid: {valid}", file=sys.stderr)
            sys.exit(1)

    input_files = args.input or sorted(args.input_dir.glob("*.json"))
    if not input_files:
        print("error: no JSON files found", file=sys.stderr)
        sys.exit(1)

    for path in input_files:
        lshw = json.loads(path.read_text())
        node = lshw_to_node(lshw, args.node_type, args.node_mode)
        if not node.get("uid"):
            print(f"warning: {path.name} has no configuration.uuid — skipping", file=sys.stderr)
            continue
        out = write_node(node, args.output_dir, args.site)
        print(f"{path.name} → {out}")


if __name__ == "__main__":
    main()

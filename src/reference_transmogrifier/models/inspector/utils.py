import re


disk_exclusion_regex = re.compile(r'^/dev/(?:md|pmem)')
disk_name_regex = re.compile("^(nvme\d+n\d+|sd[a-z]+)$")


def filter_disks(disks, match_disk_name=False):
    """
    Filter out disks that are not physical disks.

    Any device name that begins with /dev/md* or /dev/pmem* is excluded.
    """
    filtered = []
    for disk in disks:
        name = disk.get("name") if isinstance(disk, dict) else getattr(disk, "name", None)

        if name and disk_exclusion_regex.match(name):
            continue

        if not match_disk_name or disk_name_regex.match(name):
            filtered.append(disk)

    return filtered

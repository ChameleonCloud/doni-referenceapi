def filter_excluded_disks(disks):
    """Filter out disks that are not physical disks."""
    exclude_prefixes = ("/dev/md", "/dev/pmem")
    filtered = []
    for disk in disks:
        if isinstance(disk, dict):
            name = disk.get("name")
        else:
            name = disk.name
        if name and any(name.startswith(prefix) for prefix in exclude_prefixes):
            continue
        filtered.append(disk)
    return filtered

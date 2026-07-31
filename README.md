# Usage

```
usage: generate-reference-repo [-h] [--cloud CLOUD] [--reference-repo-dir REFERENCE_REPO_DIR] [--ironic-data-cache-dir IRONIC_DATA_CACHE_DIR]

options:
  -h, --help            show this help message and exit
  --cloud CLOUD
  --reference-repo-dir REFERENCE_REPO_DIR
  --ironic-data-cache-dir IRONIC_DATA_CACHE_DIR
```

Example:

1. Ensure you have a valid clouds.yaml file
1. Fetch the current reference-repository:
   ```
   git clone https://github.com/chameleoncloud/reference-repository
   ```
1. Invoke the *transmogrifier*
   ```
   generate-reference-repo \
    --cloud clouds_yaml_key \
    --reference-repo-dir /path/to/reference-repository
   ```
1. After a run, executing `git status` in the reference-repository will show any changed files.

## scripts/lshw_to_refapi.py

Converts `lshw -json` output to reference-repository node format. Intended for KVM hypervisor hosts that aren't managed by Ironic.

```
lshw_to_refapi.py --node-type gpu_h100 --input tmp/lshw-kvmgpu01.json
lshw_to_refapi.py --node-type compute_haswell --input tmp/lshw-c08-02.json
```

`--node-type` is required and applies to all files in the batch; run once per type. Defaults: `--input-dir tmp/`, `--output-dir ../reference-repository`, `--site kvm`, `--node-mode vm_only`.

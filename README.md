# Usage

```
usage: generate-reference-repo [-h] [--verbose] [--cloud CLOUD] [--push-changes]
                               [--reference-repo-url REFERENCE_REPO_URL]
                               [--reference-repo-ref REFERENCE_REPO_REF]
                               [--ironic-data-cache-dir IRONIC_DATA_CACHE_DIR]
                               [--only-nodes ONLY_NODES [ONLY_NODES ...]]
                               [--except-nodes EXCEPT_NODES [EXCEPT_NODES ...]]
                               [--prune-missing-nodes] [--allow-lease-mode-change]

options:
  -h, --help            show this help message and exit
  --verbose
  --cloud CLOUD
  --push-changes        Commit and push changes to a branch and open a PR
  --reference-repo-url REFERENCE_REPO_URL
                        URL for git repo
  --reference-repo-ref REFERENCE_REPO_REF
                        git ref to compare with (sha, branch, tag, whatever)
  --ironic-data-cache-dir IRONIC_DATA_CACHE_DIR
  --only-nodes ONLY_NODES [ONLY_NODES ...]
                        Name or ID of one or more nodes to target. Mutually exclusive with
                        --except-node. Example: `--only-nodes nc01 nc60`
  --except-nodes EXCEPT_NODES [EXCEPT_NODES ...]
                        Name or ID of one or more nodes to exclude from the list. Mutually
                        exclusive with --only-node. Example: `--except-nodes nc01 nc60`
  --prune-missing-nodes
                        Remove node JSON files from the reference repository that no longer
                        correspond to a node in Ironic for this cloud. This is based on the
                        cloud's full current node list, independent of --only-nodes/--except-
                        nodes. Off by default.
  --allow-lease-mode-change
                        Accept a node whose lease_mode in Blazar differs from the reference
                        repository, and print a warning for it. Without this flag the run fails
                        after listing every such node.
```

Example:

1. Ensure you have a valid clouds.yaml file
1. Invoke the *transmogrifier*. It clones the reference-repository from `--reference-repo-url`.
   ```
   generate-reference-repo --cloud clouds_yaml_key
   ```
1. Run `git status` in `output/reference-repository` to see the changed files.
   The run moves any earlier `output/reference-repository` to `output/reference-repository-<id>`.
1. To open a PR with the changes, set `GITHUB_TOKEN` and pass `--push-changes`.

The run exits non-zero if a node's `lease_mode` in Blazar differs from the reference repository.
Fix the extra in Blazar, or pass `--allow-lease-mode-change` to accept the change.

## scripts/lshw_to_refapi.py

Converts `lshw -json` output to reference-repository node format. Intended for KVM hypervisor hosts that aren't managed by Ironic.

```
lshw_to_refapi.py --node-type gpu_h100 --input tmp/lshw-kvmgpu01.json
lshw_to_refapi.py --node-type compute_haswell --input tmp/lshw-c08-02.json
```

`--node-type` is required and applies to all files in the batch; run once per type. Defaults: `--input-dir tmp/`, `--output-dir ../reference-repository`, `--site kvm`, `--lease-mode flavor`.

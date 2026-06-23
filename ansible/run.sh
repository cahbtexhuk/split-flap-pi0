#!/usr/bin/env bash
# Wrapper for ansible-playbook that works around the WSL/Windows NTFS
# world-writable directory issue (Ansible ignores ansible.cfg on such
# filesystems). Configuration is passed via environment variables instead.
#
# Usage:
#   ./run.sh                                    # use inventory host
#   ./run.sh -e ansible_host=192.168.1.106      # override target IP
#   ./run.sh -i 192.168.1.106,                  # one-off IP, no inventory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ANSIBLE_ROLES_PATH="${SCRIPT_DIR}/roles"
export ANSIBLE_INVENTORY="${SCRIPT_DIR}/inventories/dev/hosts.yml"
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_RETRY_FILES_ENABLED=False
export ANSIBLE_STDOUT_CALLBACK=default
export ANSIBLE_RESULT_FORMAT=yaml

ansible-playbook "${SCRIPT_DIR}/playbooks/site.yml" "$@"

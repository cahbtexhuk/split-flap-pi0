#!/usr/bin/env bash
# Wrapper for ansible-playbook that works around the WSL/Windows NTFS
# world-writable directory issue (Ansible ignores ansible.cfg on such
# filesystems). Configuration is passed via environment variables instead.
#
# Usage:
#   ./run.sh                                    # deploy app (site.yml) using inventory host
#   ./run.sh -e ansible_host=192.168.1.106      # deploy app, override target IP
#   ./run.sh provision.yml                      # full Pi provisioning (first-time setup)
#   ./run.sh provision.yml -e ansible_host=IP   # full provisioning with IP override
#   ./run.sh -i 192.168.1.106,                  # deploy app, one-off IP (no inventory)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ANSIBLE_ROLES_PATH="${SCRIPT_DIR}/roles"
export ANSIBLE_INVENTORY="${SCRIPT_DIR}/inventories/dev/hosts.yml"
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_RETRY_FILES_ENABLED=False
export ANSIBLE_STDOUT_CALLBACK=default
export ANSIBLE_RESULT_FORMAT=yaml

PLAYBOOK="${SCRIPT_DIR}/playbooks/site.yml"

if [[ $# -gt 0 && "$1" == *.yml ]]; then
	PLAYBOOK="${SCRIPT_DIR}/playbooks/$1"
	shift
fi

ansible-playbook "${PLAYBOOK}" "$@"

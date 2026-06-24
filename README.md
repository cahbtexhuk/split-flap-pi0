# split-flap-pi0

Raspberry Pi Zero based controller for a split-flap display, with:

- Ansible IaC for device provisioning
- Python app entrypoint for runtime logic

## Project layout

- `ansible/` Infrastructure provisioning playbook, inventory, and role tasks
- `python_app/` Main Python program and dependencies

## Prerequisites

- Control machine with Ansible installed
- Network access to your Raspberry Pi over SSH
- SSH auth configured (key or password)

## Provision a Raspberry Pi

From the project root:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

Current provisioning includes:

- Passwordless sudo for `split-flap`
- `apt` update and regular package upgrade
- I2C enablement (`dtparam=i2c_arm=on` + `i2c-dev` module)
- Python and global I2C Python packages (`python3`, `python3-pip`, `python3-smbus`, `smbus2`)
- Hardware watchdog enablement (`dtparam=watchdog=on` + `bcm2835_wdt`)
- Watchdog package install and service enable/start

Reboot after the first provisioning run so boot config changes fully apply.

## Override target IP at runtime

Use the existing inventory host alias and override `ansible_host`:

```bash
cd ansible
ansible-playbook playbooks/site.yml --limit split-flap -e ansible_host=192.168.1.50
```

Or bypass inventory with a one-off host:

```bash
cd ansible
ansible-playbook playbooks/site.yml -i 192.168.1.50,
```

## Run Python app

```bash
cd python_app
python main.py
```

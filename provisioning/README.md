# Lab provisioning (VirtualBox)

Automates the **network fabric and VM skeleton** of the lab: it creates the
VirtualBox networks and creates/imports and wires every VM (NICs, RAM, CPU)
from one declarative file, idempotently, on both Linux and Windows.

> **Scope.** This builds and wires the machines. **Booting and in-guest
> configuration stay manual** — pfSense rules, VyOS/RIP, IP addressing,
> Splunk and OpenNMS are set up by hand exactly as in
> [`../docs/report.md`](../docs/report.md). The appliance OSes (pfSense,
> VyOS, Windows XP) can't be cloud-init provisioned, so full "one command
> from nothing" isn't honest for this stack — the images come from the
> course and are referenced, never installed from scratch here.

## Why VBoxManage (and not Vagrant)

The lab is VirtualBox-native and mixes appliances that Vagrant handles
poorly (pfSense, Windows XP). A thin `VBoxManage` driver reproduces the exact
NAT-network + internal-network topology from the report and runs identically
on Linux and Windows. The whole topology — the 8 subnets and VLAN IDs from
Table 2 of the report — lives in one `topology.yaml`, so it stays in sync
with the addressing table.

## Files

| File | What it is |
|---|---|
| `topology.yaml` | Declarative source of truth: networks + VMs. **Edit this.** |
| `labctl.py` | The driver. Reads `topology.yaml`, calls `VBoxManage`. |
| `requirements.txt` | Just PyYAML. |

## Prerequisites

- [VirtualBox](https://www.virtualbox.org/) with `VBoxManage` on your `PATH`
  (or set the `VBOXMANAGE` env var to its full path).
- Python 3.9+
- The course-provided VM images (OVAs or disks). These are **not committed**
  — see the repo `.gitignore`.

```bash
pip install -r provisioning/requirements.txt
```

## Usage

```bash
# 1. Point each VM at its image: edit the `image:` fields in topology.yaml.
#    Leave image "" to get an empty shell you install into by hand.

# 2. Sanity check (no changes made):
python provisioning/labctl.py validate

# 3. See exactly what would run, without touching VirtualBox:
python provisioning/labctl.py --dry-run up

# 4. Build the networks and all VMs (does NOT power them on):
python provisioning/labctl.py up

# 5. Power VMs on / off (all, or by name):
python provisioning/labctl.py start
python provisioning/labctl.py start lab-pfsense lab-r1
python provisioning/labctl.py stop

# 6. See current state:
python provisioning/labctl.py status

# 7. Tear everything down (deletes the lab VMs, disks and NAT network):
python provisioning/labctl.py destroy          # prompts first
python provisioning/labctl.py destroy --yes     # no prompt
```

Every command is **idempotent** — rerun `up` after editing `topology.yaml`
and it re-applies NIC/CPU/RAM to existing VMs instead of duplicating them.

## How networks and VLANs are modelled

A VirtualBox *internal network* is a dumb L2 hub with no VLAN filtering, so
each L2 segment from the report is modelled as its **own internal network**.
The `vlan:` field in `topology.yaml` is **documentation only** — it records
the VLAN ID the report assigns, so you tag the matching guest interfaces
(pfSense sub-interfaces, VyOS tagged interfaces) to stay faithful to the
report. VirtualBox itself does not tag frames.

Only the `outer_wan` **NAT network** is created explicitly (for internet
access); internal networks are created automatically the moment a VM NIC is
attached to them.

## Topology at a glance

| VM | Networks (NIC order) |
|---|---|
| `lab-wan-router` | outer_wan, wan |
| `lab-pfsense` | wan, servers_net, dmz1_net, clients_net |
| `lab-r1` | clients_net, r1r2, r1r3 |
| `lab-r2` | r1r2, r2r3 |
| `lab-r3` | r1r3, r2r3, r3r4 |
| `lab-r4` | r3r4, lab_net |
| `lab-kali-admin` / `lab-splunk` / `lab-opennms` | servers_net |
| `lab-webserver` | dmz1_net |
| `lab-victim-xp` | lab_net |

See [`../docs/report.md`](../docs/report.md) for the full addressing table,
firewall rules and per-device configuration.

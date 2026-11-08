#!/usr/bin/env python3
"""labctl - idempotent VirtualBox provisioning for the Network Attack Sim Lab.

Reads ``topology.yaml`` and creates the lab's VirtualBox networks and VMs via
VBoxManage. Scope is NETWORK + VM SKELETON: it builds the fabric and wires the
VMs (NICs, RAM, CPU). Booting and in-guest configuration stay manual, exactly
as described in ``docs/report.md``.

Everything is idempotent: running a command twice does not create duplicates.
Works on both Linux and Windows (VBoxManage is located automatically).

Usage:
    python labctl.py validate          # check VBoxManage + parse topology
    python labctl.py networks          # create the NAT network(s)
    python labctl.py vms               # create/import + wire all VMs
    python labctl.py up                # networks + vms (does NOT start them)
    python labctl.py start [names...]  # power on all (or named) VMs
    python labctl.py stop  [names...]  # power off all (or named) VMs
    python labctl.py status            # show VM + network state
    python labctl.py destroy [--yes]   # unregister+delete all lab VMs & NAT net

Add --dry-run to any command to print the VBoxManage calls without running them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is required. Install it with:\n"
        "    pip install -r provisioning/requirements.txt"
    )

# Topology lives next to this script, regardless of the current directory.
TOPOLOGY_PATH = Path(__file__).resolve().parent / "topology.yaml"


# --------------------------------------------------------------------------- #
# VBoxManage discovery + execution
# --------------------------------------------------------------------------- #
def find_vboxmanage() -> str:
    """Locate the VBoxManage executable cross-platform.

    Order: $VBOXMANAGE override -> PATH -> common install locations.
    """
    override = os.environ.get("VBOXMANAGE")
    if override and Path(override).exists():
        return override

    exe = "VBoxManage.exe" if os.name == "nt" else "VBoxManage"
    on_path = shutil.which(exe) or shutil.which("VBoxManage")
    if on_path:
        return on_path

    candidates = [
        Path(r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"),
        Path(r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"),
        Path("/usr/bin/VBoxManage"),
        Path("/usr/local/bin/VBoxManage"),
        Path("/opt/VirtualBox/VBoxManage"),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)

    sys.exit(
        "Could not find VBoxManage. Install VirtualBox, or set the "
        "VBOXMANAGE environment variable to its full path."
    )


class Vbox:
    """Thin wrapper around VBoxManage with dry-run support."""

    def __init__(self, dry_run: bool = False) -> None:
        self.bin = find_vboxmanage()
        self.dry_run = dry_run

    def run(self, *args: str, check: bool = True, quiet: bool = False) -> str:
        cmd = [self.bin, *args]
        if self.dry_run:
            print("DRY-RUN:", " ".join(_quote(a) for a in cmd))
            return ""
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
        if result.returncode != 0 and check:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(
                f"VBoxManage failed ({result.returncode}): "
                f"{' '.join(_quote(a) for a in cmd)}"
            )
        if result.stderr and not quiet and not check:
            # Non-fatal stderr (e.g. query misses) is swallowed by callers.
            pass
        return result.stdout

    # -- queries ----------------------------------------------------------- #
    def list_vms(self) -> set[str]:
        out = self.run("list", "vms", check=False, quiet=True)
        return {line.split('"')[1] for line in out.splitlines() if '"' in line}

    def list_running(self) -> set[str]:
        out = self.run("list", "runningvms", check=False, quiet=True)
        return {line.split('"')[1] for line in out.splitlines() if '"' in line}

    def list_natnetworks(self) -> set[str]:
        out = self.run("natnetwork", "list", check=False, quiet=True)
        names: set[str] = set()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Name:"):
                names.add(line.split(":", 1)[1].strip())
            elif line.startswith("NetworkName:"):
                names.add(line.split(":", 1)[1].strip())
        return names


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg else arg


# --------------------------------------------------------------------------- #
# Topology loading
# --------------------------------------------------------------------------- #
def load_topology() -> dict:
    if not TOPOLOGY_PATH.exists():
        sys.exit(f"Topology file not found: {TOPOLOGY_PATH}")
    with TOPOLOGY_PATH.open(encoding="utf-8") as fh:
        topo = yaml.safe_load(fh)

    networks = {n["name"]: n for n in topo.get("networks", [])}
    vms = topo.get("vms", [])

    # Validate that every NIC references a known network.
    for vm in vms:
        for i, nic in enumerate(vm.get("nics", []), start=1):
            if nic["net"] not in networks:
                sys.exit(
                    f"VM '{vm['name']}' NIC {i} references unknown network "
                    f"'{nic['net']}'."
                )
    return {"networks": networks, "vms": vms}


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_validate(vbox: Vbox, topo: dict) -> None:
    print(f"VBoxManage : {vbox.bin}")
    print(f"Topology   : {TOPOLOGY_PATH}")
    print(f"Networks   : {len(topo['networks'])}")
    print(f"VMs        : {len(topo['vms'])}")
    missing = [v["name"] for v in topo["vms"] if not v.get("image")]
    if missing:
        print(
            "\nVMs without an image (created as empty shells): "
            + ", ".join(missing)
        )
    print("\nOK - topology parsed successfully.")


def cmd_networks(vbox: Vbox, topo: dict) -> None:
    """Create NAT networks. Internal networks need no pre-creation in VBox:
    they spring into existence when a VM NIC is attached to them."""
    existing = vbox.list_natnetworks()
    for net in topo["networks"].values():
        if net.get("kind") != "natnetwork":
            continue
        name = net["name"]
        if name in existing:
            print(f"[=] NAT network '{name}' already exists")
            continue
        print(f"[+] Creating NAT network '{name}' ({net['cidr']})")
        vbox.run(
            "natnetwork", "add",
            "--netname", name,
            "--network", net["cidr"],
            "--enable",
            "--dhcp", "on" if net.get("dhcp") else "off",
        )
    intnets = [n["name"] for n in topo["networks"].values()
               if n.get("kind") == "intnet"]
    print(
        f"[i] {len(intnets)} internal network(s) are created implicitly when "
        "VMs are wired: " + ", ".join(intnets)
    )


def _vm_exists(vbox: Vbox, name: str, known: set[str]) -> bool:
    return name in known


def cmd_vms(vbox: Vbox, topo: dict) -> None:
    known = vbox.list_vms()
    for vm in topo["vms"]:
        name = vm["name"]
        if _vm_exists(vbox, name, known):
            print(f"[=] VM '{name}' already exists - re-applying NIC/CPU/RAM")
        else:
            _create_vm(vbox, vm)
        _configure_vm(vbox, topo, vm)
    print("\nDone. Configure and boot the guests manually (see docs/report.md).")


def _create_vm(vbox: Vbox, vm: dict) -> None:
    name = vm["name"]
    image = vm.get("image", "")

    if image:
        img_path = Path(image).expanduser()
        if not img_path.exists():
            print(f"[!] VM '{name}': image not found ({image}); skipping")
            return
        if img_path.suffix.lower() == ".ova":
            print(f"[+] Importing OVA for '{name}' from {img_path}")
            vbox.run("import", str(img_path), "--vsys", "0", "--vmname", name)
        else:
            print(f"[+] Creating '{name}' and attaching disk {img_path}")
            _create_shell(vbox, vm)
            vbox.run(
                "storagectl", name,
                "--name", "SATA", "--add", "sata", "--controller", "IntelAhci",
            )
            vbox.run(
                "storageattach", name,
                "--storagectl", "SATA", "--port", "0", "--device", "0",
                "--type", "hdd", "--medium", str(img_path),
            )
    else:
        print(f"[+] Creating empty shell '{name}' (install the OS manually)")
        _create_shell(vbox, vm)


def _create_shell(vbox: Vbox, vm: dict) -> None:
    vbox.run(
        "createvm",
        "--name", vm["name"],
        "--ostype", vm.get("ostype", "Other"),
        "--register",
    )


def _configure_vm(vbox: Vbox, topo: dict, vm: dict) -> None:
    name = vm["name"]
    args = [
        "modifyvm", name,
        "--cpus", str(vm.get("cpus", 1)),
        "--memory", str(vm.get("memory", 512)),
    ]

    # Reset NICs 1-8 to "none", then enable the ones we need in order.
    for i in range(1, 9):
        args += [f"--nic{i}", "none"]

    nics = vm.get("nics", [])
    for idx, nic in enumerate(nics, start=1):
        net = topo["networks"][nic["net"]]
        kind = net.get("kind", "intnet")
        if kind == "natnetwork":
            args += [f"--nic{idx}", "natnetwork",
                     f"--nat-network{idx}", net["name"]]
        else:  # intnet
            args += [f"--nic{idx}", "intnet",
                     f"--intnet{idx}", net["name"]]
        args += [f"--nictype{idx}", nic.get("nictype", "82540EM")]
        if nic.get("promisc"):
            args += [f"--nicpromisc{idx}", nic["promisc"]]
        if nic.get("mac"):
            args += [f"--macaddress{idx}", nic["mac"].replace(":", "")]

    vbox.run(*args)
    seg_list = ", ".join(n["net"] for n in nics)
    print(f"    [{name}] {len(nics)} NIC(s): {seg_list}")


def cmd_start(vbox: Vbox, topo: dict, names: list[str]) -> None:
    targets = _select(topo, names)
    running = vbox.list_running()
    known = vbox.list_vms()
    for name in targets:
        if name not in known:
            print(f"[!] '{name}' does not exist yet (run 'vms' first)")
            continue
        if name in running:
            print(f"[=] '{name}' already running")
            continue
        print(f"[>] Starting '{name}'")
        vbox.run("startvm", name, "--type", "gui")


def cmd_stop(vbox: Vbox, topo: dict, names: list[str]) -> None:
    targets = _select(topo, names)
    running = vbox.list_running()
    for name in targets:
        if name not in running:
            print(f"[=] '{name}' is not running")
            continue
        print(f"[.] Stopping '{name}'")
        vbox.run("controlvm", name, "acpipowerbutton", check=False)


def cmd_status(vbox: Vbox, topo: dict) -> None:
    known = vbox.list_vms()
    running = vbox.list_running()
    nat = vbox.list_natnetworks()
    print("NAT networks:")
    for net in topo["networks"].values():
        if net.get("kind") == "natnetwork":
            mark = "up" if net["name"] in nat else "MISSING"
            print(f"  [{mark:>7}] {net['name']} ({net['cidr']})")
    print("\nVMs:")
    for vm in topo["vms"]:
        name = vm["name"]
        if name not in known:
            state = "absent"
        elif name in running:
            state = "running"
        else:
            state = "stopped"
        print(f"  [{state:>7}] {name}")


def cmd_destroy(vbox: Vbox, topo: dict, assume_yes: bool) -> None:
    names = [vm["name"] for vm in topo["vms"]]
    print("This will unregister and DELETE these VMs and their disks:")
    for n in names:
        print(f"  - {n}")
    nat = [n["name"] for n in topo["networks"].values()
           if n.get("kind") == "natnetwork"]
    print("and remove NAT network(s): " + ", ".join(nat))
    if not assume_yes:
        reply = input("\nType 'yes' to proceed: ").strip().lower()
        if reply != "yes":
            print("Aborted.")
            return
    known = vbox.list_vms()
    running = vbox.list_running()
    for name in names:
        if name not in known:
            continue
        if name in running:
            vbox.run("controlvm", name, "poweroff", check=False)
        print(f"[-] Deleting '{name}'")
        vbox.run("unregistervm", name, "--delete", check=False)
    for net in nat:
        print(f"[-] Removing NAT network '{net}'")
        vbox.run("natnetwork", "remove", "--netname", net, check=False)


def _select(topo: dict, names: list[str]) -> list[str]:
    all_names = [vm["name"] for vm in topo["vms"]]
    if not names:
        return all_names
    unknown = [n for n in names if n not in all_names]
    if unknown:
        sys.exit("Unknown VM name(s): " + ", ".join(unknown))
    return names


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Idempotent VirtualBox provisioning for the lab."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print VBoxManage commands without running them")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="check VBoxManage and parse topology")
    sub.add_parser("networks", help="create NAT network(s)")
    sub.add_parser("vms", help="create/import and wire all VMs")
    sub.add_parser("up", help="networks + vms (does not start them)")
    sub.add_parser("status", help="show VM and network state")

    p_start = sub.add_parser("start", help="power on all (or named) VMs")
    p_start.add_argument("names", nargs="*")
    p_stop = sub.add_parser("stop", help="power off all (or named) VMs")
    p_stop.add_argument("names", nargs="*")

    p_destroy = sub.add_parser("destroy", help="delete all lab VMs + NAT net")
    p_destroy.add_argument("--yes", action="store_true", help="skip prompt")

    args = parser.parse_args()
    vbox = Vbox(dry_run=args.dry_run)
    topo = load_topology()

    if args.command == "validate":
        cmd_validate(vbox, topo)
    elif args.command == "networks":
        cmd_networks(vbox, topo)
    elif args.command == "vms":
        cmd_vms(vbox, topo)
    elif args.command == "up":
        cmd_networks(vbox, topo)
        cmd_vms(vbox, topo)
    elif args.command == "start":
        cmd_start(vbox, topo, args.names)
    elif args.command == "stop":
        cmd_stop(vbox, topo, args.names)
    elif args.command == "status":
        cmd_status(vbox, topo)
    elif args.command == "destroy":
        cmd_destroy(vbox, topo, args.yes)


if __name__ == "__main__":
    main()

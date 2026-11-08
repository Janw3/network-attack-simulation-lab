from scapy.all import *
from scapy.layers.inet import IP, UDP
from scapy.layers.snmp import SNMP, SNMPvarbind, SNMPbulk

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def snmp_attack_preparation(snmp_device: string, oid: string):
    print(f"Analyzing SNMP packet size to '{snmp_device}' with OID {oid}")

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
    ip_packet = IP(dst=snmp_device) / udp_packet / snmp_packet
    ip_packet.show()

    sr1(ip_packet, timeout=2)


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: %s snmp-device-ip oid" % (sys.argv[0]))
        sys.exit(0)

    snmp_device_ip = str(sys.argv[1])
    oid = str(sys.argv[2])
    snmp_attack_preparation(snmp_device_ip, oid)


if __name__ == "__main__":
    main()

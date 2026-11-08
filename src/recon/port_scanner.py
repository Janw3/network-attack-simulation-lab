from scapy.all import *
from scapy.layers.inet import TCP, IP


logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def scan_tcp_ports(target_ip, start_port, end_port):
    print(
        "Scanning "
        + target_ip
        + " for open TCP ports in range ("
        + str(start_port)
        + " - "
        + str(end_port)
        + ")."
    )

    if start_port == end_port:
        end_port += 1

    try:
        for port in range(start_port, end_port):
            syn_packet = IP(dst=target_ip) / TCP(dport=port, flags="S")
            response = sr1(syn_packet, timeout=0.5, verbose=0)
            if response.getlayer(TCP).flags == 0x12:  # SYN-ACK.
                print("Port " + str(port) + " is open!")
            sr(
                IP(dst=target_ip) / TCP(dport=response.sport, flags="R"),
                timeout=0.5,
                verbose=0,
            )
    except AttributeError:
        pass

    print("Scan is complete!")


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: %s target startport endport" % (sys.argv[0]))
        sys.exit(0)

    target = str(sys.argv[1])
    startport = int(sys.argv[2])
    endport = int(sys.argv[3])

    scan_tcp_ports(target, startport, endport)


if __name__ == "__main__":
    main()

# Project Report: Network Attack Simulation Lab

> **Note on this document.** This is an adapted version of the original
> project report, prepared for this repository. A few editorial notes:
> - Figures and screenshots from the original submission (Wireshark traces,
>   Splunk dashboards, pfSense UI screens, etc.) are **not included** here.
>   Figure numbers are kept in the text only for traceability to the
>   original document.
> - Python code listings that were duplicated in the original report's
>   appendix have been replaced with references to the corresponding files
>   in [`src/`](../src/) and [`examples/legacy/`](../examples/legacy/).
> - Contact details and location fields from the original device
>   configuration have been replaced with generic placeholders.
> - OCR/text-extraction artifacts from the original PDF (garbled quotation
>   marks, apostrophes, dashes) have been corrected. No wording was changed.

## List of abbreviations

| # | Abbreviation | Description |
|---|---|---|
| 1 | ACL | Access Control List |
| 2 | ACK | Acknowledgement (TCP flag) |
| 3 | ARP | Address Resolution Protocol |
| 4 | BGP | Border Gateway Protocol |
| 5 | CPU | Central Processing Unit |
| 6 | DMZ | Demilitarized zone |
| 7 | DNS | Domain Name System |
| 8 | DDoS | Distributed Denial of Service |
| 9 | DoS | Denial of Service |
| 10 | HTTP | Hypertext Transfer Protocol |
| 11 | ICMP | Internet Control Message Protocol |
| 12 | IDS | Intrusion Detection System |
| 13 | IP | Internet Protocol |
| 14 | IPS | Intrusion Prevention System |
| 15 | LAN | Local Area Network |
| 16 | LTS | Long Term Support |
| 17 | MAC | Media Access Control |
| 18 | MIB | Management Information Base |
| 19 | NAT | Network Address Translation |
| 20 | NMS | Network Management System |
| 21 | OID | Object Identifier |
| 22 | OSPF | Open Shortest Path First |
| 23 | OWASP | Open Worldwide Application Security Project |
| 24 | PC | Personal Computer |
| 25 | PDU | Protocol Data Unit |
| 26 | RIP | Routing Information Protocol |
| 27 | RST | Reset (TCP flag) |
| 28 | SIEM | Security Information and Event Management |
| 29 | SNMP | Simple Network Management Protocol |
| 30 | SOAR | Security Orchestration, Automation and Response |
| 31 | SPL | Search Processing Language |
| 32 | SSH | Secure Shell |
| 33 | SYN | Synchronize (TCP flag) |
| 34 | TCP | Transmission Control Protocol |
| 35 | UDP | User Datagram Protocol |
| 36 | VLAN | Virtual Local Area Network |
| 37 | WAN | Wide Area Network |

## Abstract / Summary

In this project the goal is to set up a virtual network based on virtual
machines using Oracle VirtualBox to show three different network attacks
and how to mitigate them. This project shows a reconnaissance attack, a
Denial-of-Service (DoS) attack, and an SNMP reflection/amplification
attack. These attacks are visible through traces using programs like
Wireshark and their effects are measurable on the affected devices. All the
attacks are implemented as Python scripts using Scapy. Some mitigation
measures are proposed to increase the security of the network. Furthermore,
some concepts of network security management, like monitoring and network
device management, are applied. OpenNMS and a SIEM system (Splunk) are used
to monitor and alert administrators of the network in case of anomalies
like outages and suspicious network activity. A pfSense firewall is the
entry point to the trusted network, which is divided into multiple network
segments using the range `192.168.20.0/24` as required by the course,
including a DMZ hosting a webserver reachable from the outside world. For
this a WAN router is used, which allows the network to communicate with the
internet. The internal trusted network uses four routers running RIP as a
dynamic routing protocol.

In the first part of this report, the setup of the network and its
validation are shown. Then the different attacks and their mitigations are
described and analyzed. Finally, some conclusions and recommendations are
drawn from the experiments shown in this project.

**Keywords:** Firewall pfSense, SIEM, Splunk, Reconnaissance, port scan,
ARP host discovery, Denial of Service, TCP SYN Flood, SNMP
reflection/amplification, OpenNMS, DMZ, RIP, Wireshark, Scapy.

---

## 1. Introduction

This section shows the network topology, its components, and the setup.
This lays the ground for the network attacks and mitigation measures
described in [Section 2](#2-attacking-the-network-analysis-and-results).

### 1.1 Overview

The network in this project consists of two main areas. The first is the
untrusted network, which has two network segments: the "Outer WAN"
(`10.13.37.0/24`) and the "WAN" (`172.16.1.0/24`). The underlying physical
network of the "Outer WAN" uses a VirtualBox NAT Network called "Outer WAN"
to perform NAT between the virtual network in Oracle VirtualBox and the
host network connected to the internet. In addition, the physical network
of the "WAN" network uses a different Internal Network called "wan" so that
messages are separated between the trusted and untrusted network at the
physical network level. This ensures that messages in the virtual
environment are not visible from the trusted network, which is protected
by a firewall.

*(Original Figure 1: Network topology — see [`docs/diagrams/`](diagrams/)
for the source topology diagram, and the simplified architecture diagram in
the repository [README](../README.md).)*

In the right part of the network lies the trusted network. The entry point
for it is the pfSense firewall, which has four interfaces across the two
main parts of the network.

The trusted network is segmented into eight subnets starting from the base
address `192.168.20.0/24` as specified in the course requirements (see
Table 2):

- **Servers**: holds all the servers needed for the current functioning of
  the network. Services like OpenNMS and SIEM (Splunk) are hosted there.
  The administrator of the network connects here to perform administration
  tasks like configuring OpenNMS, Splunk, and the firewall.
- **DMZ1**: a demilitarized zone to group services needed from the
  outside. This includes a webserver reachable from the internet through
  destination NAT in the firewall, port-forwarded to TCP port 80.
- **Clients**: a network holding clients and the entry point for the
  remaining networks in the rest of the trusted area.
- **R1-R2**: network between routers R1 and R2.
- **R1-R3**: network between routers R1 and R3.
- **R2-R3**: network between routers R2 and R3.
- **R3-R4**: network between routers R3 and R4.
- **LAB**: laboratory network holding clients that can be used as victims
  for the attacks.

**Table 2: Network segmentation**

| Network name | Network address | Broadcast | Host range | VLAN ID |
|---|---|---|---|---|
| Servers | 192.168.20.0/28 | 192.168.20.15 | 192.168.20.1 – 192.168.20.14 | No VLAN |
| DMZ1 | 192.168.20.16/28 | 192.168.20.31 | 192.168.20.17 – 192.168.20.30 | 16 |
| Clients | 192.168.20.32/28 | 192.168.20.47 | 192.168.20.33 – 192.168.20.46 | 32 |
| R1-R2 | 192.168.20.48/28 | 192.168.20.63 | 192.168.20.49 – 192.168.20.62 | 48 |
| R1-R3 | 192.168.20.64/28 | 192.168.20.79 | 192.168.20.65 – 192.168.20.78 | 64 |
| R2-R3 | 192.168.20.80/28 | 192.168.20.95 | 192.168.20.81 – 192.168.20.94 | 80 |
| R3-R4 | 192.168.20.96/28 | 192.168.20.111 | 192.168.20.97 – 192.168.20.110 | 96 |
| LAB | 192.168.20.112/28 | 192.168.20.127 | 192.168.20.113 – 192.168.20.126 | No VLAN |

### 1.2 Victim PC (Windows XP)

One of the victims of the following attacks is the "victim PC" running
Windows XP. This operating system was chosen because it is old and runs on
a low amount of resources. The provided course image is used and slightly
modified. This PC is connected to the "LAB" network. Due to the limited
VLAN support in the legacy operating system, the "LAB" network is
configured without VLANs.

The network settings were configured under "Control Panel → Network
Connections → Properties". The IP address `192.168.20.126/28` was entered,
corresponding to a network mask of `255.255.255.240`. The default gateway
is the IP address of router R4's interface in the "LAB" network
(`192.168.20.113`). To access the internet through this machine, the
well-known public DNS servers Cloudflare DNS (`1.1.1.1`) and Google Public
DNS (`8.8.8.8`) were configured.

At this point no validation was possible because the other components of
the network were not yet available. This is validated later once the other
components are online.

### 1.3 Routers

Traffic between the firewall and the "LAB" network is routed using four
routers. These routers run the VyOS operating system, each in an
independent virtual machine based on the same image. The routers exchange
route information via the RIP protocol. SSH on port 22 is enabled on all of
them for further configuration. See the configuration commands for router
R1 in Table 10, R2 in Table 11, R3 in Table 12, and R4 in Table 13
(Appendix).

Interface status is validated with `show interfaces` on each router.
Reachability is tested by pinging every router from every other router
(R1 → R2, R3, R4; R2 → R1, R3, R4; etc.). Route exchange is verified with
`show ip route` on every router. Finally, connectivity from R1 to the
victim PC (Windows XP) is confirmed with a ping.

### 1.4 WAN router

The WAN Router makes it possible to communicate with the internet. It is
also based on the VyOS image, but with special settings: it performs
source NAT so the internal network can reach the internet. See Table 14
(Appendix) for the configuration commands. Because the router is directly
connected to the firewall (which performs source NAT), no additional
custom routes are necessary beyond the default route `0.0.0.0/0`, which is
needed to route traffic to the Host PC performing NAT within the
VirtualBox NAT network.

The settings are verified with `show interfaces` and `show ip route`.
Internet connectivity is tested by pinging `1.1.1.1`.

### 1.5 Admin PC (kali)

The Kali Admin PC is used to set up all servers and the firewall. It uses
the provided Kali image from the course, configured to be in the "Servers"
network via standard Ethernet. The network configuration was changed by
editing `/etc/network/interfaces` (see Table 15, Appendix). Connectivity to
other devices is verified with `ping`.

### 1.6 Firewall (pfSense)

The pfSense firewall is the most important component in the network — the
barrier between the untrusted and trusted networks. The course-provided
image was reset to factory settings for a clean initial setup.

#### 1.6.1 Interfaces

The firewall has four physical network interfaces. The first interface,
WAN, is connected to the physical network called "wan". The remaining
interfaces — SERVERS, DMZ1, and CLIENTS — are connected to the physical
network called "project_net". The DMZ1 and CLIENTS interfaces additionally
use VLANs 16 and 32, respectively.

#### 1.6.2 Firewall configuration rules

Firewall rules are essential to control and restrict traffic, ensuring that
only authorized communication is allowed between systems. They help
protect devices from unauthorized access, block malicious activity like
scans or attacks, and enforce network segmentation. Without firewall
rules, any device could reach any other, making the network vulnerable and
unmanageable.

**Table 3: Firewall configuration rules**

| From | To | Allowed? |
|---|---|---|
| Servers | DMZ1 | YES |
| Servers | Clients | YES |
| Servers | Internet | YES |
| DMZ1 | Servers | NO |
| DMZ1 | Clients | NO |
| DMZ1 | Internet | NO |
| Clients | DMZ1 | YES |
| Clients | Internet | YES |
| Clients | Servers | NO |
| Internet | Servers | NO |
| Internet | Clients | NO |
| Internet | DMZ1 | YES (port 80 only) |

**Firewall ruleset for WAN.** A single rule allows incoming traffic from
the internet to the internal webserver (`192.168.20.30`) on port 80
(HTTP). This enables public web access while ensuring all other
unsolicited inbound connections are blocked by default, since pfSense
denies any traffic not matching an explicit allow rule — minimizing the
attack surface. Verified with a ping and an HTTP `wget` request from the
external attacker to the exposed webserver (`172.16.1.254`).

**Firewall rule for Servers.** Two rules: an Anti-Lockout Rule (allows
access to the firewall itself on ports 80/443 from the SERVERS subnet, to
prevent administrators from locking themselves out), and a "Default allow
LAN to any" rule permitting all outgoing traffic from SERVERS. Servers can
freely initiate connections; incoming connections from outside are blocked
unless explicitly allowed. Verified with pings from the admin PC to
`8.8.8.8`, to router R1 in "Clients", and to the webserver in "DMZ1".

**Firewall rule for DMZ1.** No rules are defined, so all traffic from DMZ1
is blocked by default — devices there cannot initiate any connection and
are not reachable from other networks. Verified by pinging from the
webserver to `8.8.8.8` (fails), to router R1 (fails), and to the admin PC
(fails).

**Firewall rule for Clients.** Two rules: block all traffic from Clients to
the Servers subnets, and allow outgoing traffic from Clients to the
internet. An alias "CLIENTS_CHILDREN" groups all subnet ranges reachable
from "clients" to the "LAB" network for simplified rule management.
Verified with a ping from the Windows XP machine to `8.8.8.8` (works) and
to the admin PC/Servers subnet (blocked).

#### 1.6.3 RIP settings

To communicate with the "LAB" network, routes inside the firewall must be
updated via RIP, configured on the "CLIENTS" interface. Due to the lack of
built-in RIP support, the FRR package [1] is used (supports BGP, OSPF, and
RIP), installed via "System → Package Manager → Available Packages".

The FRR package is enabled under "Services → FRR Global/Zebra", requiring
a router ID (the interface's IP address) and a master password, configured
as specified in [2]. Once active, six new services appear under
"Services". RIP routing is enabled under "Services → FRR RIP", specifying
the RIP network. Crucially, "Redistribute a Default route to neighbors"
under "Default Route Redistribution" is enabled so the firewall advertises
`0.0.0.0/0` to the other RIP nodes — enabling access to the rest of the
servers (e.g. the webserver in DMZ1) and to the internet. RIP status is
visible under "Services → FRR RIP → Status" once routes are advertised.

#### 1.6.4 NAT Settings: webserver

The last firewall setting enables the webserver to be reachable from the
internet via port forwarding. Every request to the firewall's WAN interface
on TCP port 80 (HTTP), from any source, is mapped to the webserver's
internal address (`192.168.20.30`) on TCP port 80, configured under
"Firewall → NAT".

### 1.7 Internal attacker PC (kali)

The internal attacker PC simulates attacks from within the internal
network. Based on the provided Kali Linux image, it operates in the
"Clients" subnet via the shared internal network interface "project_net".
Only the hostname and network configuration were modified by editing
`/etc/network/interfaces` (see Table 16, Appendix) — this system uses a
VLAN interface to communicate in the appropriate subnet. Connectivity to
the firewall and internal systems is verified via `ping`.

### 1.8 External attacker PC (kali)

The external attacker PC emulates an attacker from an external, untrusted
network (e.g. the internet). It uses the provided Kali Linux image and is
assigned to the "Outer WAN" network segment via VirtualBox's internal
network "outer_wan", with static IP configuration (see Table 17, Appendix).
Connectivity to the firewall's WAN interface is verified via `ping`.

### 1.9 Webserver (OWASP)

The server in DMZ1 simulates a webserver running vulnerable OWASP
applications, used to simulate external traffic entering the trusted
network and to verify the firewall works as expected. Only the network
settings were changed, by editing `/etc/network/interfaces` (see Table 18,
Appendix). Setup is verified by opening the website from the admin PC and
from the external attacker PC (confirming NAT works and the webserver is
reachable from the outside).

### 1.10 SIEM (Splunk)

Splunk is used to collect, process, and analyze logs from various systems
(pfSense, webserver, attacker machines). The Splunk server is placed in
the "Servers" subnet. Since it runs on Ubuntu 22.04 LTS (using `netplan`),
`/etc/netplan/00-installer-config.yaml` was edited accordingly (see Table
21, Appendix), followed by `sudo netplan apply`.

Connectivity is validated with a ping from the admin PC and from the
pfSense firewall. After logging into the Splunk web interface, the stream
configuration is set up to enable the TCP, ICMP, ARP, and SNMP streams
needed to capture the attacks in this project. Once enabled, the
`streamfwd` component captures live network traffic on selected interfaces
and extracts protocol metadata (source/destination IP, ports, HTTP
headers, DNS queries, connection flags), searchable via SPL in the "Search
& Reporting" tab. Queries are saved as alerts that can, for example, email
an administrator when an attack occurs — one alert is configured per
attack in this project.

### 1.11 OpenNMS

OpenNMS monitors the network devices. The course-provided image's network
setup was adapted to this project's topology. Since it runs on Ubuntu
22.04 LTS (using `netplan`), `/etc/netplan/00-installer-config.yaml` was
edited (see Table 20, Appendix), followed by `sudo netplan apply`.
Connectivity is verified by navigating to the OpenNMS site from the admin
PC.

Device discovery is configured under "Settings → Configure Discovery"
with the network ranges from Table 2. After a while, all active network
devices are discovered and added to the OpenNMS database.

Routers R1 through R4 are configured for SNMP monitoring with a read-only
community `public`, open to **all** clients in the trusted network (see
Table 19, Appendix). This deliberately permissive choice — rather than
restricting access to, say, just the OpenNMS server — is made specifically
to later demonstrate how an SNMP attack can be performed against such a
misconfiguration (see [Section 2.3](#23-snmp-reflectionamplification-attack)).
OpenNMS is then updated with the `public` community for each router under
"Settings → Configure SNMP Community Names by IP Address", and each router
is rescanned. Discovered nodes expose interface and device details,
including the configured contact and location information (see Table 19).

After shutting down some network components, outages are correctly
detected and displayed in the OpenNMS dashboard, confirming the system
works as expected.

---

## 2. Attacking the network: analysis and results

In this section, three different attack types are performed against the
described network. For each, the strategy and execution are described,
followed by detection and mitigation mechanisms.

### 2.1 Reconnaissance attacks

A reconnaissance attack is a typical first step in a cyber-attack, during
which an attacker gathers information about the target network to identify
active hosts, services, and potential vulnerabilities. This can be done
passively (e.g. sniffing traffic) or actively (e.g. scanning hosts and
ports). In this project, an active reconnaissance attack is performed from
the internal attacker system within the segmented virtual network, aiming
to discover potential targets and services by scanning the internal subnet
and specific systems like the webserver.

#### 2.1.1 Network scan: host discovery using ARP

**Overview.** The internal attacker (kali) already has access to the
trusted network. To identify systems in the local network segment, the
attacker performs an ARP scan. Since ARP is a link-layer protocol, it
works even when ICMP is blocked. The attacker sends ARP requests as
Ethernet broadcast packets to all IP addresses within the subnet
`192.168.20.32/28` — 16 addresses in total, 15 usable host addresses
(`192.168.20.32`–`192.168.20.46`, see Table 2). A packet for each of these
15 addresses is constructed using the broadcast MAC address
(`ff:ff:ff:ff:ff:ff`), ensuring all devices in the local network receive
the request.

**Performing the attack.** The attack is performed with a Scapy script
(see Table 4, Appendix — this ARP scan script only exists as inline code
in the original report and was not provided as a standalone file in this
repository) using `sudo python3 Host_Discovery.py 192.168.20.32/28`.
Wireshark traces confirm exactly 15 ARP requests were sent, with two
replies: the pfSense firewall at `192.168.20.33` and router R1 at
`192.168.20.46`. Each device owning one of the targeted IP addresses
responds directly with its MAC and IP address, letting the attacker
determine which hosts are currently active.

**Detecting the attack.** An alert is created in Splunk using the SPL
query in Table 22 (Appendix). It detects ARP scanning by identifying
source IPs (`src_ip`) that send ARP requests to more than 10 unique
destination IPs (`dest_ip`) within a 30-second window — indicative of host
discovery behavior.

**Mitigating the attack.** It is not realistically possible to completely
prevent ARP scans, since ARP operates at Layer 2 and does not pass through
firewalls like pfSense. However, impact can be significantly reduced by
limiting the attacker's visibility: isolating sensitive devices (routers,
firewall) into a separate VLAN (`192.168.20.32/28`) restricts broad host
discovery to that segment only.

#### 2.1.2 Port scan on R1 router

**Overview.** After discovering R1's IP address (`192.168.20.46`), a TCP
SYN port scan checks which ports are open. For each port in a predefined
range, a TCP SYN packet is sent to R1. An open port responds SYN-ACK (the
attacker immediately replies RST to close the half-open connection,
minimizing the scan's footprint); a closed port responds RST-ACK; a
filtered port returns no response at all.

**Performing the attack.** The Scapy script (Table 5, Appendix — see
[`src/recon/port_scanner.py`](../src/recon/port_scanner.py)) sends crafted
SYN packets and observes the response, run as `sudo python3
Reconnaissance_Attack.py <IP to scan> <Port range>`. Only port 22 (SSH) is
detected as open; all other ports are closed or filtered. Wireshark traces
confirm all ports respond RST-ACK except port 22, which responds SYN-ACK.

**Detecting and mitigating the port scan attack.** An alert is created
using the SPL query in Table 23 (Appendix), identifying source IPs
(`src_ip`) that attempt to connect to 50 or more different destination
ports (`dest_port`).

### 2.2 Denial-of-Service (DoS) attack

A Denial of Service (DoS) attack aims to disrupt the normal functionality
of a service by overwhelming it with excessive traffic.

#### 2.2.1 Overview

The external attacker (kali) launches a DoS attack against the webserver,
simulating an external threat. The attacker sends a continuous stream of
TCP SYN segments to the webserver through the firewall (which performs
destination NAT). For each SYN received, the firewall forwards the request
to the webserver, which replies SYN-ACK, expecting a final ACK. The
attacker never sends that ACK. The webserver keeps each half-open
connection in memory, waiting for a response that never arrives. Over
time, these incomplete connections accumulate, consuming memory and socket
resources, until the server runs out of available connections or system
resources — unable to respond to legitimate traffic, effectively causing a
denial of service.

#### 2.2.2 Performing the attack

The attacker uses the Scapy script in Table 6 (Appendix — see
[`src/dos/tcp_syn_flood.py`](../src/dos/tcp_syn_flood.py)) to perform a
TCP SYN flood on port 80 of the server (`192.168.20.30`), run as `sudo
python3 SYN_Flood.py <IP to flood> <Port to flood>`. The targeted IP is
the firewall's address (`172.16.1.254`), due to NAT.

Before the attack, the webserver responds normally; CPU usage is around 1%
idle. During the attack, the number of half-open connections increases
sharply, making the webserver slow and unresponsive: system usage (%sy),
hardware interrupts (%hi), and software interrupts (%si) all rise notably
(the OS handling many incoming SYN packets), while idle time (%id) drops
significantly. User-space usage (%us) and I/O wait (%wa) remain low. After
the attack, the server gradually recovers. Wireshark traces confirm many
TCP handshakes to `192.168.20.30:80` are initiated but never completed.

#### 2.2.3 DoS attack: detection and mitigation

An alert is created using the SPL query in Table 24 (Appendix). It detects
the SYN flood by identifying connections receiving many TCP packets
without corresponding ACKs (`ack_packets_in="0"`), grouped by connection
and a 10-second time window, flagging any connection with more than 50
such packets as suspicious.

To mitigate, the pfSense firewall supports a feature called "Synproxy"
(visible under the advanced options of the WAN rule). It protects the
server by intercepting and handling the TCP handshake on the firewall's
behalf: instead of forwarding SYN packets directly, the firewall replies
with SYN-ACK itself, and only completes the handshake — forwarding the
connection to the real server — once the client responds with a valid
ACK. This way, only legitimate TCP connections reach the server.

### 2.3 SNMP reflection/amplification attack

The most complex attack in this project is a special form of distributed
denial of service (DDoS) called an SNMP reflection/amplification attack.
It exploits misconfigured network devices that use the SNMP protocol for
remote management.

The attacker sends an SNMP request to the misconfigured devices using the
spoofed IP address of the targeted victim — this is the *reflection*.
These devices respond with SNMP responses the victim never requested,
increasing resource use on the victim's system as it processes the
incoming malicious traffic — this is the *denial of service*. The
requests are crafted so a small SNMP request (e.g. 100 bytes) results in a
large SNMP response (e.g. 2000 bytes) — this is the *amplification*. This
attack is shown in two variants. [3]

#### 2.3.1 Variant 1: Using the VLANs

**Preparing the attack.** The internal kali attacker (`192.168.20.40`,
connected to "Clients"/VLAN 32) attacks the Victim PC (`192.168.20.126`,
Windows XP) via the four routers R1–R4, which are misconfigured to accept
SNMP requests from any client using the `public` community. After
reconnaissance and traffic sniffing confirm this misconfiguration and the
victim's location, the attacker crafts a malicious SNMP packet and sends
it to the nearest router, R1 (`192.168.20.46/28`). The packet contains an
SNMP-GETBULK-PDU with one or more MIB-OIDs, requesting the target to
return a single response with the requested OID and all its children —
meaning a single small request results in a large response, due to the
nature of this PDU type. [4]

Because sniffed traffic shows that SNMP-GETBULK responses contain at most
100 variable bindings, the goal is to find a parent OID with at least 100
children and the most data per child. Using the Scapy script in Table 7
(Appendix — see
[`src/snmp_amplification/oid_analysis.py`](../src/snmp_amplification/oid_analysis.py))
and analyzing response sizes in Wireshark, the OID with the largest
response is `1.3.6.1.2.1.4.24`, corresponding to `ipForward` [5] — a table
of all forwarded IPs, which can hold many (large) entries. Measured at the
IPv4 layer only (ignoring Layer 2, to account for VLAN vs. non-VLAN
differences): the bulk request is 71 bytes; the reassembled response (after
IP fragmentation) is 3722 bytes — an amplification factor of **52.4×** for
this exact packet. Assuming similar behavior across all routers, this OID
is used for the attack.

**Performing the attack.** The attacker sends a single SNMP-GETBULK
request with OID `1.3.6.1.2.1.4.24` to each router, with the source IP
address spoofed to the victim's address `192.168.20.126` to leverage
reflection. Packets are sent at a 1 ms interval to maximize damage. This
is done with the Scapy script in Table 8 (Appendix — see
[`src/snmp_amplification/attack_vlan_routed.py`](../src/snmp_amplification/attack_vlan_routed.py)),
run as `sudo python3 snmp_attack_vlan.py 192.168.20.126`. See
[`docs/diagrams/snmp-attack-vlan.puml`](diagrams/snmp-attack-vlan.puml) for
the attack flow diagram.

Wireshark traces show the attacker's request to R1, the (fragmented,
large) response traversing "Clients" → "R1-R3" (VLAN 64) → "R3-R4" (VLAN
96) → the victim, and the same pattern for R2, R3, and R4. The victim
responds to the unsolicited SNMP responses with an ICMP "Destination
unreachable" packet, since nothing is listening on the source UDP port.

The effect is indirectly measured via the victim's Task Manager CPU usage:
idling at ~0% before/after the attack, rising to a constant ~10% during
the attack. Because only four routers reflect traffic, and the Python
attacker's send rate is limited by the environment, the victim is not
overwhelmed at this scale — but the attack is shown to be possible. With
more reflecting devices and a faster attacker, the victim could plausibly
be fully overwhelmed.

**Detecting the attack.** An alert is created using the SPL query in Table
25 (Appendix), using the SNMP stream data, triggering if more than 100
`GetBulkRequest` messages are seen within a 1-second interval. Because the
stored source IP is the spoofed victim address (not the attacker), this
identifies which device is under attack rather than who is attacking.

**Mitigating the attack.** This attack is possible because the managed
SNMP devices are misconfigured. Instead of allowing SNMP requests from all
clients, only a subset of well-known machines is permitted — updating the
router configuration with the commands in Table 27 (Appendix) restricts
access to the OpenNMS server, the only node (besides a network
administrator) that genuinely needs SNMP access. After this mitigation,
victim CPU usage remains at 0% during a repeated attack; Wireshark
confirms the routers no longer reply to the malicious requests. Splunk
continues to detect and alert on the (now-ineffective) attack attempts.

#### 2.3.2 Variant 2: Using the shared ethernet network

The second variant exploits the fact that the underlying virtual
environment has a single "Physical Network" of type "Internal Network"
called "project_net", putting every network component in a single Layer 2
broadcast domain. This variant is specific to this virtual environment and,
unlike Variant 1, is unlikely to apply to real-world scenarios — it is
shown to illustrate what increased performance could achieve. Preparation
is identical to Variant 1; only the sending method changes.

**Performing the attack.** The attacker sends a single malicious
SNMP-GETBULK request to the broadcast address `224.0.0.1`, which
corresponds to all systems in this subnet [6]. Since all routers share the
same Layer 2 segment, they receive and process the request simultaneously,
each responding with a large SNMP response — causing the same
amplification and reflection as before, but faster (no routing needed,
every router receives the message at the same time). This is done using
the Scapy script in Table 9 (Appendix — see
[`src/snmp_amplification/attack_broadcast.py`](../src/snmp_amplification/attack_broadcast.py)),
run as `sudo python3 snmp_attack.py 192.168.20.126`. See
[`docs/diagrams/snmp-attack-broadcast.puml`](diagrams/snmp-attack-broadcast.puml)
for the attack flow diagram.

Wireshark traces show the initial broadcast request, then each router
responding directly to the victim without routing; the large SNMP
responses are fragmented, and the victim again responds with ICMP
"Destination unreachable". Victim CPU usage rises up to ~30% during this
variant (vs. ~10% in Variant 1), confirming that a higher request rate
increases the attack's effectiveness.

**Detecting the attack.** The first SPL query is adapted (Table 26,
Appendix) to measure `GetBulkRequest` count over a 10-second window,
triggering at more than 50 requests to the same source IP — the lower
threshold reflects this variant's higher efficiency (fewer requests needed
per second).

**Mitigating the attack.** The same mitigation (Table 27, Appendix) is
applied to all routers. Wireshark confirms only the malicious broadcast
request is seen; no router replies. Interestingly, some CPU activity is
still observed on the victim after mitigation — not from router
reflection (there is none), but because the victim itself sits in the same
Layer 2 broadcast domain and receives and processes the broadcast request
directly. This is specific to this virtual topology and would not occur
in a realistic network. Splunk continues to detect and alert on the
mitigated attack attempts.

---

## 3. Conclusion and Recommendations

After introducing the network topology and its components, three main
attacks were shown, analyzed, and successfully mitigated: a
reconnaissance attack (in two variants), a Denial of Service (DoS)
attack, and an SNMP reflection/amplification attack.

Generally, using the firewall together with network/VLAN segmentation
allows administrators to manage the network effectively. This makes it
possible to introduce a DMZ to expose the webserver to the internet while
isolating it from the rest of the network, increasing overall security.
Furthermore, visibility inside the network is increased via OpenNMS,
which lets administrators monitor devices and visualize outages and
device status. Stateful firewall rules mitigate a lot of external
requests and limit external actors' access — but this is not sufficient
protection on its own. It is therefore recommended to add an IDS/IPS
system (e.g. Snort) to the firewall, to increase detection of more
complex attacks and even block them in real time.

In this network, internal attackers are still capable of launching
reconnaissance attacks such as host discovery (ARP scans) and port scans
on neighboring VLANs. These can be detected via the SIEM (Splunk), which
aggregates network stream data for near-real-time alerting — e.g. when a
source IP sends too many ARP requests in a short window, or scans too
many ports. This enables detection and notification of suspicious
reconnaissance behavior before exploitation occurs. Mitigation of this
attack class is not entirely possible, but because the network is already
heavily restricted by VLAN segmentation, an attacker only discovers the
R1 router and the firewall via host discovery.

The DoS attack, in which an external attacker floods the webserver with
SYN packets to exhaust its resources with half-open connections, can be
successfully detected and mitigated. Detection works in Splunk by
observing connections without ACKs over short windows. While detection
helps identify the attack, mitigation requires infrastructure hardening —
one approach is SYN proxying (SYN cookies) on the firewall, validating TCP
handshakes before they reach the target, filtering out incomplete
connections. Rate limiting is another way to reduce a DoS attack's
impact.

With the implemented network topology, an SNMP reflection/amplification
attack is also possible, and is shown to be detectable via Splunk, with
administrators notified in real time. Mitigation could be enhanced with
an IDS/IPS system like Snort to block this traffic outright, complemented
by a SOAR system for an even better security response — but these
measures only take effect once an attack is already underway. Preventive
action is preferable: the attack is possible because the network is
misconfigured, so restricting the `public` community to a set of
well-known machines reduces the amplification effect, since the spoofed
victim is not authorized to perform SNMP requests unless it is one of
those machines. Another mitigation option is SNMPv3 — only SNMP v2c was
used in this project, where communities are sent in clear text, which
allowed the internal attacker to sniff the community and perform the
attack. SNMPv3 supports authentication and encryption, reducing the
attack surface.

## Bibliography

[1] Netgate, "FRR Package | pfSense Documentation," Netgate, 2025.
Available: https://docs.netgate.com/pfsense/en/latest/packages/frr/index.html

[2] Netgate, "FRR Global Settings Configuration | pfSense Documentation,"
Netgate, 2025. Available:
https://docs.netgate.com/pfsense/en/latest/packages/frr/global/configuration.html

[3] Imperva, "What is SNMP Reflection & Amplification | DDoS Attack |
Imperva," Imperva, 2025. Available:
https://www.imperva.com/learn/ddos/snmp-reflection/

[4] Digital Prototype Systems Inc., "What is a SNMP GetBulk Request?,"
Digital Prototype Systems Inc., 2022. Available:
https://www.dpstele.com/blog/what-is-a-snmp-getbulk-request.php

[5] The Internet Society, "OID 1.3.6.1.2.1.4.24 ipForward database
reference," The Internet Society, 2006. Available:
https://oidref.com/1.3.6.1.2.1.4.24

[6] Internet Assigned Numbers Authority (IANA), "IPv4 Multicast Address
Space Registry," IANA, 2025. Available:
https://www.iana.org/assignments/multicast-addresses/multicast-addresses.xhtml

---

## Appendix A: Scripts and configuration

### Python scripts

The Scapy scripts listed as tables in the original report correspond to
the following files in this repository:

| Original table | Script purpose | Location in this repo |
|---|---|---|
| Table 4 | ARP host discovery | *not included as a standalone file — only existed as inline code in the original report* |
| Table 5 | TCP SYN port scan | [`src/recon/port_scanner.py`](../src/recon/port_scanner.py) |
| Table 6 | TCP SYN flood (DoS) | [`src/dos/tcp_syn_flood.py`](../src/dos/tcp_syn_flood.py) |
| Table 7 | SNMP attack preparation / OID analysis | [`src/snmp_amplification/oid_analysis.py`](../src/snmp_amplification/oid_analysis.py) |
| Table 8 | SNMP attack, Variant 1 (VLAN-routed) | [`src/snmp_amplification/attack_vlan_routed.py`](../src/snmp_amplification/attack_vlan_routed.py) |
| Table 9 | SNMP attack, Variant 2 (broadcast) | [`src/snmp_amplification/attack_broadcast.py`](../src/snmp_amplification/attack_broadcast.py) |

Two additional draft scripts from earlier project stages are kept in
[`examples/legacy/`](../examples/legacy/) for transparency — see the
repository [README](../README.md#status--limitations) for details.

### Router and device configuration

**Table 10: Configuration commands of router R1**

```
configure
set system host-name R1
set interfaces ethernet eth0 vif 32 address 192.168.20.46/28
set interfaces ethernet eth0 vif 32 description "UP"
set interfaces ethernet eth0 vif 48 address 192.168.20.49/28
set interfaces ethernet eth0 vif 48 description "RIGHT"
set interfaces ethernet eth0 vif 64 address 192.168.20.65/28
set interfaces ethernet eth0 vif 64 description "BOTTOM"
set protocols rip interface eth0.32
set protocols rip interface eth0.48
set protocols rip interface eth0.64
set service ssh port 22
commit
save
exit
```

**Table 11: Configuration commands of router R2**

```
configure
set system host-name R2
set interfaces ethernet eth0 vif 48 address 192.168.20.62/28
set interfaces ethernet eth0 vif 48 description "LEFT"
set interfaces ethernet eth0 vif 80 address 192.168.20.81/28
set interfaces ethernet eth0 vif 80 description "BOTTOM"
set protocols rip interface eth0.48
set protocols rip interface eth0.80
set service ssh port 22
commit
save
exit
```

**Table 12: Configuration commands of router R3**

```
configure
set system host-name R3
set interfaces ethernet eth0 vif 64 address 192.168.20.78/28
set interfaces ethernet eth0 vif 64 description "UP"
set interfaces ethernet eth0 vif 80 address 192.168.20.94/28
set interfaces ethernet eth0 vif 80 description "UP-RIGHT"
set interfaces ethernet eth0 vif 96 address 192.168.20.97/28
set interfaces ethernet eth0 vif 96 description "RIGHT"
set protocols rip interface eth0.64
set protocols rip interface eth0.80
set protocols rip interface eth0.96
set service ssh port 22
commit
save
exit
```

**Table 13: Configuration commands of router R4**

```
configure
set system host-name R4
set interfaces ethernet eth0 vif 96 address 192.168.20.110/28
set interfaces ethernet eth0 vif 96 description "LEFT"
set interfaces ethernet eth0 address 192.168.20.113/28
set protocols rip interface eth0.96
set protocols rip interface eth0
set service ssh port 22
commit
save
exit
```

**Table 14: Configuration commands for the WAN router**

```
set interfaces ethernet eth4 address 10.13.37.254/24
set interfaces ethernet eth4 description WAN
set interfaces ethernet eth3 address 172.16.1.1/24
set interfaces ethernet eth3 description RIGHT
set protocols static route 0.0.0.0/0 next-hop 10.13.37.1
# Enable NAT
edit nat source rule 1
set description "Masquerade LAN to WAN"
set outbound-interface eth4
set translation address masquerade
compare
commit
save
exit
```

**Table 15: `/etc/network/interfaces` of the admin PC (kali)**

```
auto eth0
iface eth0 inet static
address 192.168.20.13/28
gateway 192.168.20.1
```

**Table 16: `/etc/network/interfaces` of the internal attacker (kali)**

```
auto eth0
iface eth0 inet manual
up ifconfig eth0 up
auto eth0.32
iface eth0.32 inet static
address 192.168.20.40/28
gateway 192.168.20.33
vlan-raw-device eth0
```

**Table 17: `/etc/network/interfaces` of the external attacker (kali)**

```
auto eth0
iface eth0 inet static
address 10.13.37.2
netmask 255.255.255.0
gateway 10.13.37.254
```

**Table 18: Configuration file for the webserver (OWASP)**

```
# The loopback network interface
auto lo
iface lo inet loopback
# The primary network interface
auto eth0
iface eth0 inet manual
up ifconfig eth0 up
auto eth0.16
iface eth0.16 inet static
address 192.168.20.30
netmask 255.255.255.240
gateway 192.168.20.17
vlan-raw-device eth0
```

**Table 19: Configuration commands for the routers to enable SNMP**

> Contact and location fields below are generic placeholders; the original
> submission used institution-specific values here.

```
configure
set service snmp community public authorization ro
set service snmp community public client 0.0.0.0
set service snmp location "City, Country"
set service snmp contact "admin@example.com"
set service snmp trap-target 192.168.20.14 port 162
set service snmp trap-target 192.168.20.14 community public
compare
commit
save
exit
```

**Table 20: Network configuration of OpenNMS** (`/etc/netplan/00-installer-config.yaml`)

*Not available as text in the source material (shown as a screenshot in
the original submission).*

**Table 21: Network configuration of Splunk** (`/etc/netplan/00-netplan.yaml`)

*Not available as text in the source material (shown as a screenshot in
the original submission).*

### Splunk SPL queries

**Table 22: SPL query to detect the ARP scan attack**

```spl
sourcetype="stream:arp"
| bin _time span=30s
| stats dc(dest_ip) AS unique_targets BY _time, src_ip
| where unique_targets > 10
```

**Table 23: SPL query to detect the TCP port scanning attack**

```spl
sourcetype="stream:tcp"
| stats dc(dest_port) AS num_dest_port BY src_ip
| where num_dest_port >= 50
```

**Table 24: SPL query to detect the TCP SYN flood attack**

```spl
sourcetype="stream:tcp"
| bin _time span=10s
| stats count(eval(ack_packets_in="0")) AS filtered_events BY _time, connection
| where filtered_events > 50
```

**Table 25: SPL query to detect the SNMP attack (Variant 1, with VLAN)**

```spl
sourcetype="stream:snmp"
| search "method{}"=GetBulkRequest
| bucket _time span=1s
| stats count by _time, src_ip
| where count > 100
| rename src_ip AS "victim ip"
```

**Table 26: SPL query to detect the SNMP attack (Variant 2, without VLAN)**

```spl
sourcetype="stream:snmp"
| search "method{}"=GetBulkRequest
| bucket _time span=10s
| stats count by _time, src_ip
| where count > 50
| rename src_ip AS "victim ip"
```

### Mitigation commands

**Table 27: Commands to mitigate the SNMP attack in the routers**

```
configure
delete service snmp community public network 0.0.0.0/0
set service snmp community public client 192.168.20.14
compare
commit
exit
```

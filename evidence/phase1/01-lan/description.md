# Task A — LAN Connectivity

## Objective

The objective of this task was to verify that all four macOS machines
are connected to the same private LAN and can communicate with each
other.

## Machines

| Machine | Role |
|---|---|
| Mac 1 | Private DNS Server |
| Mac 2 | Edge / Reverse Proxy / Load Balancer |
| Mac 3 | Backend A |
| Mac 4 | Backend B |

## 1. IP Address Information

The network information of all four machines was collected, including:

- IPv4 address
- Subnet mask
- Default gateway
- Active network interface
- MAC address

Evidence:

```text
01-ip-addresses/
├── MAC1.jpeg
├── MAC2.jpeg
├── MAC3.jpeg
└── MAC4.jpeg


# Ping Connectivity Tests

## Objective

The objective of this test is to verify network-level connectivity
between the four macOS machines participating in the NOAA private
network.

The `ping` utility was used to send ICMP Echo Requests and verify that
the machines can successfully communicate with each other over the
private LAN.

## Machines Tested

| Machine | Role |
|---|---|
| Mac 1 | Private DNS Server |
| Mac 2 | Edge / Reverse Proxy / Load Balancer |
| Mac 3 | Backend A |
| Mac 4 | Backend B |

## Testing Method

Connectivity was tested using the following command:

```bash
ping -c 4 <destination-ip>



# LAN Topology

## Objective

The objective of this task is to document the topology of the NOAA
private network and show the role of each machine in the Phase 1
implementation.

The diagram represents the four macOS machines connected through the
Rishihood Learner College WiFi private network.

## Network Topology

The network consists of four machines:

| Machine | Role | IP Address | Service / Port |
|---|---|---|---|
| Mac 1 | DNS Server + Client | 10.7.11.132 | dnsmasq / UDP 53 |
| Mac 2 | Edge / Reverse Proxy / TLS | 10.7.11.79 | nginx / HTTPS 8443 |
| Mac 3 | Backend A | 10.7.11.131 | HTTP 3001 |
| Mac 4 | Backend B + Client | 10.7.11.144 | HTTP 3002 |

## Network Flow

The basic Phase 1 network flow is:

```text
                    RISHIHOOD LEARNER COLLEGE WiFi
                              Private LAN
                                   |
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
             ▼                     ▼                     ▼
        ┌──────────┐          ┌──────────┐          ┌──────────┐
        │  Mac 1   │          │  Mac 2   │          │  Mac 3   │
        │   DNS    │          │  nginx   │          │ Backend A│
        │ 10.7.11.132          │ 10.7.11.79          │ 10.7.11.131
        │ UDP 53   │          │ HTTPS    │          │ HTTP 3001│
        └──────────┘          │ 8443     │          └──────────┘
                              └─────┬────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │  Mac 4   │
                              │ Backend B│
                              │10.7.11.144
                              │ HTTP 3002│
                              └──────────┘
# Task B — Private DNS Configuration and Resolution

## Objective

The objective of this task is to configure and verify a private DNS
service for the NOAA private network.

The DNS server provides name resolution for the private `.test` domain
used by the project. Clients can access the service using domain names
instead of directly using IP addresses.

## DNS Server

The private DNS server is hosted on **Mac 1**.

| Component | Configuration |
|---|---|
| DNS Server | Mac 1 |
| DNS Server IP | `10.7.11.132` |
| DNS Port | `53` |
| Domain | `noaa.test` |
| Application Domain | `app.noaa.test` |
| API Domain | `api.noaa.test` |

The client machines are configured to use:

```text
10.7.11.132
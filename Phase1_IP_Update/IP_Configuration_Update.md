# Phase 1 – Updated IP Configuration and Verification

## 1. Purpose of This Update

After the initial Phase 1 implementation, the IP addresses of Mac 1 (Om) and Mac 2 (Neeraj) were updated.

To maintain consistency across the network, the DNS and nginx configurations were updated to use the current IP addresses.

The original Phase 1 submission has been preserved. This document records the subsequent configuration changes and verification.

## 2. Updated Network IP Address Table

| Machine | Team Member | Role | Updated IP Address |
|---|---|---|---|
| Mac 1 | Om | DNS Server (dnsmasq) | 10.7.5.107 |
| Mac 2 | Neeraj | Edge Server (nginx) | 10.7.27.60 |
| Mac 3 | Ayush | Backend A | 10.7.11.131 |
| Mac 4 | Aparna | Backend B | 10.7.11.144 |

## 3. Configuration Changes

### A. DNS Configuration – Mac 1

The dnsmasq configuration was updated with:

- Listening address: 10.7.5.107
- `app.team1.test` resolves to 10.7.27.60.
- `api.team1.test` resolves to 10.7.27.60.

### B. nginx Configuration – Mac 2

The nginx upstream configuration was updated:

- Backend A: 10.7.11.131:3001
- Backend B: 10.7.11.144:3002

nginx continues to distribute incoming requests between both backend servers.

### C. Backend Configuration – Mac 3 and Mac 4

- Backend A runs on port 3001.
- Backend B runs on port 3002.
- Both backend services remain accessible over the LAN.

## 4. Verification Performed

The updated network configuration was tested through:

1. DNS resolution using `dig`.
2. Connectivity tests between the four Macs.
3. Direct HTTP requests to both backend services.
4. nginx configuration validation using `nginx -t`.
5. Load-balancing tests through repeated HTTP requests.

## 5. Final Result

The updated IP configuration was successfully implemented and tested.

DNS resolution, nginx reverse proxying, and backend load balancing continued to function with the updated network addresses.

This document supplements the original Phase 1 submission and records the subsequent IP configuration changes.
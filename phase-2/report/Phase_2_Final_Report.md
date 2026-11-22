# Private Network Service Platform (Phase 2: Harden, Recover and Troubleshoot)

## 1. Title Page Information
- **Project Title:** Private Network Service Platform (Phase 2: Harden, Recover and Troubleshoot)
- **Course:** Computer Networks
- **Team Members:** Neeraj, Om, Ayush, Aparna
- **Date:** November 22, 2026
- **Architecture Overview:**
  - **Domains:** `app.noaa.test` and `api.noaa.test`
  - **Protocol & Ports:** HTTPS over Port 8443 (HTTP/2), Direct Backend HTTP Ports 3001 & 3002
  - **Security:** TLS v1.2 / v1.3 with Custom Private Certificate Authority (Root CA)
- **Node Network Roles & IP Allocations:**
  - **Mac 1 (Om):** Primary DNS Resolver (`dnsmasq`) — `10.7.5.107`
  - **Mac 2 (Neeraj):** Main Edge Reverse Proxy (`nginx`) — `10.7.27.60`
  - **Mac 3 (Ayush):** Backend Service A (Port 3001) & Standby Edge Reverse Proxy (`nginx` Port 8443) — `10.7.11.131`
  - **Mac 4 (Aparna):** Backend Service B (Port 3002), Backup DNS Resolver (`dnsmasq` Port 53), & Test Client — `10.7.11.144`

---

## 2. What Changed from Phase 1

In Phase 1, we implemented a baseline private service platform with a single edge reverse proxy, two backend nodes, and a single DNS server. While functionally sound under normal conditions, that topology lacked fault tolerance and containment. Any failure of the primary DNS server, a crash in a backend service, or maintenance on the edge proxy resulted in service downtime or client-facing HTTP 502 errors.

In Phase 2, we hardened the platform by adding a backup DNS resolver, configuring upstream retry directives in nginx, isolating Backend A with packet filtering firewall rules, testing DNS time-to-live (TTL) expiration, performing a controlled edge migration using an overlap window, and practicing a step-by-step troubleshooting routine.

| Component | Phase 1 Baseline | Phase 2 Hardened Implementation |
|---|---|---|
| **DNS Resolution Architecture** | Single primary DNS server (`dnsmasq` on Mac 1) without fallback; default cache lifetimes. | Dual redundant DNS resolvers (Primary: Mac 1, Backup: Mac 4 on port 53); client resolver failover; consistent 30-second TTL for controlled record updates. |
| **Backend Upstream & Reliability** | Static round-robin proxy pass in Nginx; no retry directives; a backend crash caused HTTP 502 Bad Gateway errors for clients. | Upstream failover configured with `max_fails=1`, `fail_timeout=10s`, `proxy_connect_timeout 2s`, and `proxy_next_upstream error timeout http_502 http_503 http_504` with 2 tries; initial failover takes ~2s during retry, then continues without error. |
| **Network Security & Access Control** | Backend ports (3001 and 3002) were directly accessible across the LAN by any device. | Service isolation via macOS Packet Filter (`pf`) applied to Backend A (port 3001 on Mac 3), permitting only edge IPs (`10.7.27.60`, `10.7.11.131`) and dropping all other packets; verified clean rollback procedure (rules for port 3002 drafted). |
| **Edge Proxy Infrastructure** | Single static Nginx edge instance on Mac 2; single point of failure during host or software maintenance. | Standby Nginx deployed on Mac 3 with custom response header (`X-Edge: standby`); service kept available through an overlap window while clients moved over as their 30s DNS cache expired. |
| **Diagnostics & Incident Management** | Ad-hoc manual pings and basic curls without structured verification methodology. | Standardized 5-step diagnostic process (Step 1: Basics $\rightarrow$ Step 2: DNS $\rightarrow$ Step 3: TCP $\rightarrow$ Step 4: TLS $\rightarrow$ Step 5: HTTP) codified in `diagnose.sh` and verified through practice drills. |

---

## 3. Extension Summaries (A to F)

### A: Backup DNS Resolver
To eliminate the primary DNS resolver as a single point of failure, we configured a secondary DNS resolver using dnsmasq on Mac 4 (10.7.11.144) to listen on port 53 alongside Backend B, matching the primary records for app.noaa.test and api.noaa.test pointing to the active edge (10.7.27.60). We tested locally with `dig @127.0.0.1` and remotely across the LAN with `dig @10.7.11.144`. When we stopped dnsmasq on the primary server (Mac 1), client requests continued to resolve successfully. The very first query experienced a brief delay while the client resolver waited for its UDP query timeout before failing over to the secondary address, after which resolution was prompt. This works because operating system stub resolvers implement automatic timeout and retry logic across configured nameservers. We learned that redundant resolvers protect domain availability against single-host outages, though maintaining consistency between separate configuration files requires disciplined coordination to prevent conflicting records. *(Owner: Aparna)*

### B: DNS TTL and Controlled Record Change
We tested DNS caching behavior and controlled record updates by setting a 30-second Time-To-Live (TTL) on Mac 1's dnsmasq server. We modified the authoritative A record for app.noaa.test to point to a test IP and monitored client resolution using `dig`, `dscacheutil -q host`, and `curl`. We observed that clients did not immediately pick up the new IP address; instead, existing client sessions continued resolving the previous edge IP until their 30-second cache expired. Once the 30-second TTL window elapsed, client lookups queried the server again and received the new address. This occurs because DNS recursive resolvers and operating system caches honor the record's TTL field to conserve network bandwidth and reduce server query loads. We learned that setting an appropriate TTL before scheduled maintenance is critical for planned migrations, and that diagnostic tools like `dig` bypass local operating system caches while user applications rely on them. *(Owner: Om)*

### C: Service Isolation with Firewall Rules (pf), Including Rollback
To restrict network access to application backends, we implemented Packet Filter (pf) firewall rules on Mac 3 hosting Backend A on port 3001, and drafted corresponding rules for Backend B on port 3002. In `noaa_pf.conf`, we permitted loopback traffic and TCP connections to port 3001 exclusively from authorized edge IP addresses (10.7.27.60 and 10.7.11.131) while blocking all others (`block drop in quick proto tcp from any to any port 3001`). When testing with `curl` and `nc`, requests from the edge succeeded normally, whereas direct connections from unauthorized LAN clients timed out. This happened because the firewall dropped incoming TCP SYN packets without sending TCP RST packets, leaving unauthorized connection attempts to hang. We verified our rollback procedure by reloading the default `/etc/pf.conf` and disabling pf, which immediately restored direct client access. We learned that firewalls enforce least-privilege transport security, but tested rollback steps are essential to avoid locking out legitimate traffic. *(Owner: Ayush)*

### D: nginx Failover Between Backends
To protect the application from backend failures, we configured upstream failover on the Mac 2 nginx edge. In `nginx.conf`, we defined our upstream with `max_fails=1 fail_timeout=10s` and added proxy directives `proxy_connect_timeout 2s`, `proxy_next_upstream error timeout http_502 http_503 http_504`, and `proxy_next_upstream_tries 2`. In normal operation, requests alternated evenly between Backend A (10.7.11.131:3001) and Backend B (10.7.11.144:3002). When we stopped Backend A, client requests still succeeded with HTTP 200. The first request after the failure took about two seconds while nginx encountered a connection refusal, marked Backend A inactive, and retried the request against Backend B. In the nginx access log, we verified this retry was recorded as `upstream_status=502, 200`. We learned that reverse proxies can absorb backend transport failures by retrying alternate servers, trading a minor initial latency penalty for uninterrupted application service. *(Owner: Neeraj)*

### E: Controlled Edge Migration Using DNS
To maintain service availability during edge proxy maintenance, we executed a controlled edge migration using a standby nginx instance on Mac 3 (10.7.11.131:8443) configured with the diagnostic header `add_header X-Edge standby always`. We ran both edges concurrently during an overlap window, confirming TLS and proxy behavior on Mac 3 before updating the DNS A record on Mac 1 from 10.7.27.60 to 10.7.11.131. During the 30-second TTL window, existing clients continued reaching Mac 2 while new resolutions shifted to Mac 3, as shown by the `x-edge: standby` header in curl responses. After client caches expired, the service continued to answer after we stopped nginx on Mac 2. We also confirmed rollback by switching the DNS record back. We learned that running edges concurrently during a planned migration prevents outages, though traffic cutover is not instantaneous and depends entirely on DNS client cache expiration. *(Owner: Ayush & Neeraj)*

### F: Troubleshooting Challenge
To build practical diagnostic skills, we conducted troubleshooting drills against injected faults using our step-by-step methodology and `diagnose.sh` script. The process followed five sequential steps: checking basic connectivity, DNS resolution, TCP port reachability, TLS certificates, and HTTP responses. In Drill 1, primary DNS on Mac 1 was stopped. Running `diagnose.sh` failed at Step 1 (`DNS FAILED: no answer`), and `dig @10.7.5.107 app.noaa.test` timed out. Restarting dnsmasq on Mac 1 immediately restored name resolution. In Drill 2, nginx on Mac 2 was stopped. The script passed DNS resolution but stopped at Step 2 (`TCP FAILED: port closed, firewall or host down`), and `nc -vz -G 3 10.7.27.60 8443` was refused. Restarting nginx on Mac 2 restored TCP handshakes and HTTP 200 responses. We learned that testing network layers sequentially pinpoints the exact failing boundary, preventing guesswork and unnecessary configuration changes. *(Owner: Om)*

---

## 4. Resilience Tests and Results

| Test | What We Broke or Changed | Expected Behavior | Observed Behavior | Layer | Evidence File |
|---|---|---|---|---|---|
| **Primary DNS Failover** | Stopped primary `dnsmasq` service on Mac 1 (`10.7.5.107`). | Client resolver falls back to secondary nameserver (`10.7.11.144`); domain continues to resolve. | Query to `10.7.5.107` timed out; query to `10.7.11.144` returned `10.7.27.60`; client lookup succeeded after initial timeout. | Application Layer (DNS) / UDP | `09_DNS_backup_working.png`, `09_DNS_remote_test.png`, `local_dns_test.txt` |
| **Controlled DNS TTL Expiration** | Set 30s TTL on Mac 1; updated A record for `app.noaa.test` to test IP. | Client uses cached record until 30s expires, then fetches updated record. | Initial lookups served previous record from cache; after 30 seconds, queries fetched new IP. | Application Layer (DNS) | `10_TTL_old_cache_established.png`, `10_TTL_dns_record_updated.jpg`, `10_TTL_cache_expiry.png`, `10_TTL_client_new_resolution.png` |
| **Backend A Isolation Enforcement** | Loaded `noaa_pf.conf` on Mac 3 blocking non-edge traffic to port 3001. | Allowed edge IPs (`10.7.27.60`, `10.7.11.131`) connect; direct LAN client requests drop/timeout. | Nginx reverse proxy forwarded traffic successfully (HTTP 200); direct client `curl` timed out as SYN packets were dropped. | Network Layer (IP filtering) / Transport Layer (TCP) | `11_ISO_edge_ok.png.jpeg`, `11_ISO_active_rules_mac3.txt` |
| **Firewall Emergency Rollback** | Flushed custom rules using `pfctl -d` and reloaded standard `/etc/pf.conf`. | Default network policy restored; direct client communication to port 3001 unblocked. | Rules returned to baseline anchors; direct client connections to Backend A succeeded without host reboot. | Network Layer / Transport Layer | `11_ISO_restored_mac3.png`, `11_ISO_restored.png.jpeg`, `11_ISO_restored_mac3.txt` |
| **Backend A Service Crash** | Terminated Backend A node process on Mac 3 (`10.7.11.131:3001`). | Nginx detects connection refused, marks node down for 10s, and retries Backend B. | Client received HTTP 200; first request delayed by ~2s connect timeout; log showed `upstream_status=502, 200`. | Application Layer (HTTP Proxy) / Transport Layer (TCP) | `12_FO_A_Down.png`, `12_FO_Logs.png`, `12_FO_Restored.png` |
| **Both Backends Down (502 Scenario)** | Stopped both Backend A (3001) and Backend B (3002) simultaneously. | Nginx attempts both upstreams, exhausts retries, and returns HTTP 502 Bad Gateway. | Client received HTTP 502 Bad Gateway error page; Nginx logged failure for all upstream attempts. | Application Layer (HTTP) | `12_FO_502.png` |
| **Blue-Green Edge Migration** | Deployed standby Nginx on Mac 3 (`10.7.11.131`), switched DNS A record, stopped Mac 2. | Service remains available through overlap; clients transition to Mac 3 as 30s cache expires. | Active traffic transitioned to Mac 3 (confirmed by `x-edge: standby`); service remained live after stopping Mac 2. | Application Layer (DNS, HTTP/2) | `13_MIG_standby_nginx.png`, `13_MIG_overlap.png.jpeg`, `13_MIG_after.png.jpeg`, `13_MIG_mac2_stopped.png.jpeg` |
| **Troubleshooting Practice Drill 1** | Shut down `dnsmasq` on primary DNS server (Mac 1). | Layered check detects failure at DNS step; system restores once service is restarted. | `diagnose.sh` halted at Step 1 (`DNS FAILED: no answer`); restarting `dnsmasq` on Mac 1 restored normal output. | Application Layer (DNS) | `14_drill1_dns_failure.png`, `14_drill1_diagnosis.png`, `14_drill1_dns_restored.png`, `14_drill1_application_restored.png` |
| **Troubleshooting Practice Drill 2** | Stopped `nginx` daemon on main edge server (Mac 2). | Layered check passes DNS but fails at TCP step; restarting Nginx restores full HTTP 200. | `diagnose.sh` passed Step 1 but halted at Step 2 (`TCP FAILED: port closed, firewall or host down`); restored on restarting Nginx. | Transport Layer (TCP Port 8443) | `14_drill2_nginx_failure.png`, `14_drill2_diagnosis.png`, `14_drill2_nginx_restored.png`, `14_drill2_application_restored.png` |

---

## 5. Troubleshooting Findings

### A. The Five-Step Diagnostic Methodology
To identify network failures efficiently without making random configuration changes, we followed a five-step diagnostic routine implemented in `diagnose.sh`:

1. **Step 1: Basics / LAN Connectivity:** Check the active interface IP (`ipconfig getifaddr en0`) and verify local link reachability using `ping`. This confirms the Mac has a valid IP and can reach other hosts on the LAN.
2. **Step 2: DNS Resolution:** Verify hostname lookup for `app.noaa.test` using `dig +time=2 +tries=1 +noall +answer $NAME` and check `/etc/hosts` for hardcoded overrides. This isolates name resolution from service reachability.
3. **Step 3: TCP Port Reachability:** Test transport-layer connection to port 8443 using `nc -vz -G 3 $IP $PORT`. This confirms that routing works, firewalls allow the port, and a listening socket completes the TCP three-way handshake.
4. **Step 4: TLS Verification:** Check the SSL/TLS handshake, private CA certificate trust, validity dates, and subject names using `curl -sv --max-time 5 -o /dev/null https://$NAME:$PORT/`. This tests transport encryption without application logic.
5. **Step 5: HTTP Application Response:** Inspect HTTP status codes and custom headers (`X-Backend`, `X-Edge`) using `curl -sI --max-time 5 https://$NAME:$PORT/api/status`. This confirms end-to-end web server and backend proxy operations.

### B. Common Symptoms and Root Cause Analysis Matrix

| Symptom / Error Message | Likely Root Causes | Verification Command | Corrective Action |
|---|---|---|---|
| `Could not resolve host: app.noaa.test` / DNS query timed out | `dnsmasq` daemon stopped; incorrect nameserver in `/etc/resolv.conf`; port 53 UDP traffic blocked. | `dig @<DNS_IP> app.noaa.test` | Restart `dnsmasq` on DNS server; verify client DNS settings. |
| `nc: connect to 10.7.27.60 port 8443: Connection refused` | Nginx service is stopped; Nginx crashed due to configuration error; listening only on `127.0.0.1`. | `sudo lsof -i :8443` or `ps aux \| grep nginx` | Validate config with `nginx -t`; start Nginx daemon (`sudo nginx`). |
| `nc: connect to 10.7.11.131 port 3001: Operation timed out` | Packet Filter (`pf`) dropping incoming TCP SYN packets; IP route missing; host down. | `sudo pfctl -sr` (on server) | Update `/etc/pf.conf` to whitelist client IP; disable blocking rules with `sudo pfctl -d`. |
| `curl: (60) SSL certificate problem: self signed certificate in certificate chain` | Tool environment (e.g. Conda curl at `/opt/anaconda3/bin/curl`) ignoring macOS System Keychain; or standby serving old certificate. | `/usr/bin/curl -v https://app.noaa.test:8443` vs `which curl` | Use system curl `/usr/bin/curl`, or replace standby certificate with the CA-signed cert. |
| `HTTP/1.1 502 Bad Gateway` returned by Nginx | Both backend nodes (3001 and 3002) are down simultaneously; firewall blocking Nginx from backends. | `nc -vz 10.7.11.131 3001` and `nc -vz 10.7.11.144 3002` from Nginx | Restart backend Node.js processes; verify firewall rules on backend nodes. |
| Client requests directed to old edge after DNS migration | Resolver cache (mDNSResponder) caching response until 30s TTL expires; stale `/etc/hosts` override. | `dscacheutil -q host -a name app.noaa.test` and `grep noaa /etc/hosts` | Wait for 30s TTL expiration or flush cache (`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`); clean `/etc/hosts`. |
| `grep` filter on HTTP response headers yields empty output | Searching for uppercase header names (`X-Edge`) over HTTP/2; RFC 7540 mandates lowercase headers. | `curl -sI https://app.noaa.test:8443/api/status \| grep -i x-edge` | Always perform case-insensitive header matches (`grep -i`) or inspect lowercase `x-edge`. |

### C. Write-Up of Practice Drills

#### Drill 1: Primary DNS Service Outage
- **Fault Injected:** The primary DNS service (`dnsmasq`) was stopped on Mac 1 (`10.7.5.107`).
- **Commands Executed in Order:**
  1. `bash ~/diagnose.sh app.noaa.test 8443` $\rightarrow$ Halted at Step 1 with `DNS FAILED: no answer`.
  2. `dig @10.7.5.107 app.noaa.test` $\rightarrow$ Query timed out with no answer returned.
  3. `dig @10.7.11.144 app.noaa.test` $\rightarrow$ Returned `10.7.27.60`, confirming the backup DNS resolver was functional.
  4. Checked Mac 1 locally $\rightarrow$ Confirmed `dnsmasq` was not running.
- **Failing Boundary:** Application Layer (DNS / UDP port 53).
- **Root Cause:** The `dnsmasq` process on Mac 1 was stopped, so port 53 was not responding.
- **Fix Applied & Verification:** Restarted `dnsmasq` on Mac 1 (`sudo brew services restart dnsmasq`). Tested `dig @10.7.5.107 app.noaa.test` directly, which returned `10.7.27.60`. Re-ran `bash ~/diagnose.sh`, passing all five checks successfully (`14_drill1_application_restored.png`).

#### Drill 2: Active Edge Reverse Proxy Outage
- **Fault Injected:** The `nginx` edge reverse proxy service was stopped on Mac 2 (`10.7.27.60`).
- **Commands Executed in Order:**
  1. `bash ~/diagnose.sh app.noaa.test 8443` $\rightarrow$ Passed Step 1 (DNS resolved to `10.7.27.60`), but halted at Step 2 with `TCP FAILED: port closed, firewall or host down`.
  2. `nc -vz -G 3 10.7.27.60 8443` $\rightarrow$ Connection refused immediately.
  3. Checked Mac 2 locally $\rightarrow$ Confirmed no active Nginx processes were listening on port 8443.
- **Failing Boundary:** Transport Layer (TCP port 8443 handshake).
- **Root Cause:** Nginx was stopped, causing the operating system kernel to reject incoming TCP SYN packets with RST packets.
- **Fix Applied & Verification:** Checked configuration with `sudo nginx -t` (syntax ok), then started Nginx with `sudo nginx`. Tested port connectivity with `nc -vz -G 3 10.7.27.60 8443` (succeeded). Ran `bash ~/diagnose.sh`, verifying complete TLS negotiation and HTTP 200 OK application responses (`14_drill2_application_restored.png`).

---

## 6. Single Point of Failure (SPOF) Analysis

### What Remains a Single Point of Failure
Even after adding a backup DNS resolver, backend failover, and firewall isolation, **the active Nginx edge reverse proxy remains a Single Point of Failure (SPOF)**.

In our current design:
1. Client requests target a single edge IP address at any given time (Mac 2 at `10.7.27.60`, or Mac 3 at `10.7.11.131`).
2. If the active edge machine experiences a sudden crash, kernel freeze, or physical network disconnection, incoming client connections immediately fail.
3. While DNS migration allows traffic to shift to the standby edge, DNS cannot provide instant automated failover. Clients and local resolvers cache records for the duration of the TTL (30 seconds). In addition, many client applications do not immediately re-query DNS when an active TCP connection drops, leading to downtime until DNS records are updated and client caches expire.

### How to Remove This Single Point of Failure
To achieve high availability without relying on manual DNS changes, we would implement:

1. **Virtual Router Redundancy Protocol (VRRP) with Keepalived:**
   - Assign a shared Virtual IP (VIP) address (e.g., `10.7.27.100`) between Mac 2 (primary) and Mac 3 (standby).
   - Both edge servers run `keepalived`, sending periodic heartbeat packets over the local network.
   - If Mac 2 stops sending heartbeats, Mac 3 claims the VIP by broadcasting Gratuitous ARP packets to the local switch.
   - DNS records point permanently to the VIP. Clients fail over within 1 to 2 seconds without requiring DNS updates or cache flushes.
2. **Anycast Routing with BGP:**
   - In a larger routed network, both edge servers announce the same IP address to network switches using BGP.
   - The network distributes traffic between both edges automatically. If one edge goes down, the routing protocol detects the dropped session and routes traffic to the surviving node.

---

## 7. Problems We Hit and How We Fixed Them

During implementation and testing, we encountered the following technical issues:

1. **Conda curl Ignored the macOS System Keychain:**
   - *Problem:* Running `curl` produced `curl: (60) SSL certificate problem: self signed certificate in certificate chain`, even though our custom CA certificate was installed and marked trusted in the macOS Keychain.
   - *Cause:* The default `curl` in the shell path was `/opt/anaconda3/bin/curl`. Because it is compiled with OpenSSL, it looks for certificates in its own static bundle rather than querying the macOS Keychain.
   - *Fix:* We called the native macOS binary explicitly using `/usr/bin/curl`, which uses Apple's native security framework and validated the certificate chain properly.
2. **Standby Edge Served Incorrect Certificate:**
   - *Problem:* During early migration tests, client HTTPS connections to the standby edge failed certificate validation.
   - *Cause:* The standby Nginx instance was initially configured with an old self-signed certificate (CN=10.7.11.79) that lacked Subject Alternative Names (SAN) for `app.noaa.test` and `api.noaa.test`.
   - *Fix:* We replaced the certificate and key in the standby Nginx configuration with the shared server certificate signed by our private Root CA covering both domain names.
3. **HTTP/2 Header Names are Lowercase:**
   - *Problem:* Scripts checking for the standby edge header failed when using `grep "X-Edge"`, even though Nginx had `add_header X-Edge standby always`.
   - *Cause:* The HTTP/2 standard (RFC 7540 Section 8.1.2) requires all header field names to be converted to lowercase during transmission.
   - *Fix:* We updated our inspection commands to use case-insensitive matching (`grep -i x-edge`) or match the lowercase string directly (`grep "x-edge"`).
4. **Stale DNS Answers on Om's Mac:**
   - *Problem:* Queries for `app.noaa.test` on Mac 1 consistently returned the old edge IP (`10.7.27.60`) instead of the updated standby IP.
   - *Cause:* Inspection of Mac 1 showed that `/etc/hosts` contained leftover static lines mapping `app.noaa.test` and `api.noaa.test` to `10.7.27.60`. We also suspected `dnsmasq` was holding stale cached entries.
   - *Fix:* Om removed the leftover lines from `/etc/hosts` and restarted `dnsmasq`, after which DNS queries consistently returned the updated IP address.
5. **DNS TTL Caching Delayed Client Migration:**
   - *Problem:* After changing the DNS record to point to Mac 3, some client requests continued going to Mac 2 for up to 30 seconds.
   - *Cause:* The operating system resolver cache (`mDNSResponder`) kept the old IP address in memory until the 30-second TTL expired.
   - *Fix:* We waited for the 30-second TTL window to clear, or flushed the local cache manually with `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.
6. **Discrepancy Between `dig`, `curl`, and `dscacheutil`:**
   - *Problem:* `dig` showed the new IP address immediately after a DNS change, but `curl` continued connecting to the old edge IP.
   - *Cause:* `dig` sends direct UDP queries to the specified nameserver and completely bypasses local operating system caches. In contrast, `curl` uses system resolution libraries (`getaddrinfo`) managed by `mDNSResponder`, which serves cached records until the TTL expires.
   - *Fix:* We separated nameserver validation (`dig @server`) from client-side resolution testing (`dscacheutil -q host -a name app.noaa.test`).

---

## 8. Conclusion

In Phase 2, we hardened our private network service platform against common failures. By setting up a backup DNS resolver, configuring nginx upstream retries, isolating backend services with pf firewall rules, and practicing planned edge migration, we improved platform resilience. Our tests confirmed that a backend failure or primary DNS stoppage does not take down the service, although failover involves brief timeout delays. The single active edge proxy remains our main single point of failure, which a shared virtual IP via VRRP could eliminate. Practicing layered troubleshooting helped us understand how DNS caching, transport timeouts, and firewall rules interact across a private network.

---

## 9. Appendix

### A. List of Configuration Files
1. **DNS Configurations:**
   - [dnsmasq_mac4.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/09_BackupDNS/dnsmasq_mac4.conf) (Backup DNS resolver configuration on Mac 4)
   - [dnsmasq_before_phase2.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/09_BackupDNS/dnsmasq_before_phase2.conf) (Baseline DNS reference configuration)
   - [dnsmasq_updated.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/Updated_phase1_IP/configs/dnsmasq_updated.conf) (Primary DNS configuration on Mac 1)
2. **Reverse Proxy (Nginx) Configurations:**
   - [nginx_phase1_backup.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/12_Failover/nginx_phase1_backup.conf) (Phase 1 Nginx baseline config)
   - [nginx_upstream_updated.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/Updated_phase1_IP/configs/nginx_upstream_updated.conf) (Updated upstream block)
   - [nginx_standby.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/13_Migration/nginx_standby.conf) (Standby Edge Nginx configuration with failover & `X-Edge` header)
3. **Firewall (Packet Filter) Configurations:**
   - [noaa_pf.conf](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/11_Isolation/noaa_pf.conf) (Active service isolation rules for port 3001)
   - [pf_rules_before.txt](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/11_Isolation/pf_rules_before.txt) (Default OS anchor baseline rules)
4. **Diagnostic Script:**
   - [diagnose.sh](file:///Users/aparnasingh/cn-phase2/noaa-private-network-service-platform/phase-2/14_Troubleshooting/diagnose.sh) (Automated 5-step network diagnostic test suite)

### B. List of Evidence Files

#### Extension A: Backup DNS Resolver (`phase-2/09_BackupDNS/`)
- `09_DNS_backup_config.png` — Configuration verification on Mac 4.
- `09_DNS_service_running.png` — Service status showing dnsmasq active on port 53.
- `09_DNS_local_test.png` — Local resolution query test (`dig @127.0.0.1`).
- `09_DNS_remote_test.png` — Remote resolution test across LAN (`dig @10.7.11.144`).
- `09_DNS_backup_working.png` — Verification of client failover to backup resolver.
- `local_dns_test.txt`, `port53_status.txt`, `service_status.txt` — Log output verifications.

#### Extension B: DNS TTL & Record Updates (`phase-2/10_TTL/`)
- `10_TTL_old_cache_established.png` — Baseline query caching under 30s TTL.
- `10_TTL_dns_record_updated.jpg` — DNS authoritative record modification in dnsmasq.
- `10_TTL_cache_expiry.png` — Observation of local cache TTL expiration timing.
- `10_TTL_client_new_resolution.png` — Successful client resolution of updated address after 30s.
- `10_TTL_old_vs_new.png` — Comparative output showing old vs new resolution behavior.
- `10_TTL_restored_configuration.jpg` — Restoration of stable DNS production records.

#### Extension C: Service Isolation with pf (`phase-2/11_Isolation/`)
- `11_ISO_edge_ok.png.jpeg` — Nginx successfully proxying to isolated Backend A (HTTP 200).
- `11_ISO_active_rules_mac3.txt` — Dump of active pf firewall rules restricting port 3001.
- `11_ISO_restored_mac3.png` — Terminal verification of flushed pf rules.
- `11_ISO_restored.png.jpeg` — Restored direct client connectivity to backend port.
- `11_ISO_restored_mac3.txt` — Diff confirming clean match with baseline firewall state.

#### Extension D: Nginx Upstream Failover (`phase-2/12_Failover/`)
- `12_Nginx_Baseline.png` — Baseline Nginx service status.
- `12_DNS_Verification.png` — Verification of domain resolution to edge IP.
- `12_Load_Balancing.png` — Steady-state round-robin distribution between Backends A and B.
- `12_Nginx_Config.png` — Nginx upstream configuration containing failover parameters.
- `12_FO_A_Down.png` — Simulated outage: Backend A process terminated.
- `12_FO_Logs.png` — Access logs showing upstream failover (`upstream_status=502, 200`).
- `12_FO_Restored.png` — Recovery verification once Backend A process restarted.
- `12_FO_502.png` — Error capture during dual backend failure scenario returning HTTP 502.

#### Extension E: Controlled Edge Migration (`phase-2/13_Migration/`)
- `13_MIG_standby_nginx.png` — Standby Nginx listening on port 8443 on Mac 3.
- `13_MIG_overlap.png.jpeg` — Concurrent execution of both edges during migration window.
- `13_MIG_after.png.jpeg` — Client requests reaching standby edge (`x-edge: standby`).
- `13_MIG_mac2_stopped.png.jpeg` — Service availability verified after stopping main edge on Mac 2.
- `13_MIG_rollback.png.jpeg` — Rollback verification returning traffic to Mac 2.

#### Extension F: Troubleshooting Drills & Scripts (`phase-2/14_Troubleshooting/`)
- `14_diagnose_healthy.png` — Output of `diagnose.sh` passing all 5 steps under normal state.
- `14_drill1_dns_failure.png` — Drill 1: `diagnose.sh` isolating failure at Step 1 (`DNS FAILED: no answer`).
- `14_drill1_diagnosis.png` — Drill 1: Direct dig query confirming port 53 timeout.
- `14_drill1_dns_restored.png` — Drill 1: DNS service restarted and verified.
- `14_drill1_application_restored.png` — Drill 1: Full system diagnostic pass after DNS fix.
- `14_drill2_nginx_failure.png` — Drill 2: `diagnose.sh` isolating failure at Step 2 (`TCP FAILED: port closed, firewall or host down`).
- `14_drill2_diagnosis.png` — Drill 2: Netcat connection refused verification.
- `14_drill2_nginx_restored.png` — Drill 2: Nginx restarted and port 8443 listening.
- `14_drill2_application_restored.png` — Drill 2: Full system diagnostic pass after Nginx fix.
- `14_mac1_dns_healthy.png`, `14_mac2_nginx_healthy.png`, `14_mac3_backendA_healthy.png`, `14_mac4_backendB_dns_healthy.png` — Node health verifications.
- `14_full_system_healthy01.png`, `14_full_system_healthy02.png` — Complete platform end-to-end operational verifications.
- `14_learning_notes.md` — Detailed engineering notes on layered troubleshooting methodology.

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
  - **Mac 4 (Aparna):** Backend Service B (Port 3002), Backup DNS Resolver (`dnsmasq`), & Test Client — `10.7.11.144`

---

## 2. What Changed from Phase 1

In Phase 1, we implemented a baseline working private service platform with a single edge reverse proxy, two backend nodes, and a single DNS server. While functionally sound under ideal conditions, that initial topology lacked fault tolerance, containment, and operational resilience. Any failure in the primary DNS server, a backend service crash, or maintenance on the edge server resulted in total service disruption or client-facing HTTP 502 errors. 

In Phase 2, we hardened the entire service platform by adding secondary infrastructure, configuring automated upstream retry mechanisms, isolating backend services with stateful packet filtering, testing dynamic DNS time-to-live (TTL) expiration, enabling zero-downtime blue-green edge migrations, and codifying a strict multi-layer troubleshooting practice.

| Component | Phase 1 Baseline | Phase 2 Hardened Implementation |
|---|---|---|
| **DNS Resolution Architecture** | Single primary DNS server (`dnsmasq` on Mac 1) without fallback; default/long cache lifetimes. | Dual redundant DNS resolvers (Primary: Mac 1, Backup: Mac 4 on port 53); automatic client stub failover; tuned low TTL (5s) for deterministic record updates. |
| **Backend Upstream & Reliability** | Static round-robin proxy pass in Nginx; no health checking, timeout tuning, or retries; backend crash caused direct HTTP 502 Bad Gateway to clients. | High-availability upstream with `max_fails=1`, `fail_timeout=10s`, `proxy_connect_timeout 2s`, and `proxy_next_upstream error timeout http_502 http_503 http_504` with 2 tries; 100% transparent failover. |
| **Network Security & Access Control** | Backend ports (3001 and 3002) were fully exposed across the LAN to any device; zero layer-3/layer-4 access control. | Service isolation via macOS Packet Filter (`pf`); strictly whitelisted edge IPs (`10.7.27.60`, `10.7.11.131`) to backend port 3001 and dropped unauthorized packets; tested clean rollback procedure. |
| **Edge Proxy Infrastructure** | Single static Nginx edge instance on Mac 2; physical single point of failure during hardware maintenance or host failure. | Active/Standby edge architecture; Standby Nginx deployed on Mac 3 with custom identification header (`X-Edge: standby`); zero-downtime blue-green migration via DNS. |
| **Diagnostics & Incident Management** | Ad-hoc manual pings and basic curls without structured verification methodology. | Standardized 5-layer diagnostic methodology (Basics $\rightarrow$ DNS $\rightarrow$ TCP $\rightarrow$ TLS $\rightarrow$ HTTP/2) codified in automated script `diagnose.sh` and verified with fault injection drills. |

---

## 3. Extension Summaries (A to F)

### A: Backup DNS Resolver
To eliminate the primary DNS server as a single point of failure, we configured a secondary DNS resolver using dnsmasq on Mac 4 (10.7.11.144) to listen on port 53 alongside Backend B, matching the primary records for app.noaa.test and api.noaa.test pointing to the active edge (10.7.27.60). We verified locally using `dig @127.0.0.1` and remotely across the LAN from client machines using `dig @10.7.11.144`. We observed that clients configured with both primary (10.7.5.107) and secondary (10.7.11.144) nameservers seamlessly resolved domain queries without user disruption even when the primary dnsmasq service was stopped. This works because operating system stub resolvers implement automatic transport-layer UDP timeout and retry mechanisms across listed nameservers; when query datagrams to the primary timeout without response, the resolver falls back to the secondary. We learned how redundant resolvers provide fault tolerance, but also realized that maintaining consistency between independent flat configuration files requires disciplined synchronization to prevent stale resolutions. *(Owner: Aparna)*

### B: DNS TTL and Controlled Record Change
We investigated DNS caching behavior and controlled address migration by lowering the Time-To-Live (TTL) of records on Mac 1's dnsmasq server from default long caching intervals down to 5 seconds. We updated the authoritative A record for app.noaa.test to point to a test address and used repeated `dig` queries alongside `dscacheutil -q host` and `curl` to track propagation. We observed that immediately after the zone update, client applications continued resolving the previous IP until their local 5-second TTL expired, after which fresh queries fetched the updated address immediately. This behavior occurs because recursive resolvers and local OS resolver caches (such as mDNSResponder on macOS) honor the TTL field embedded within the DNS resource record to reduce network query volume, serving cached responses until expiration. We learned that lowering TTL well before scheduled maintenance is essential for deterministic cutovers, and that debugging caching requires understanding that diagnostic utilities like `dig` issue direct network queries that bypass the OS cache entirely. *(Owner: Om)*

### C: Service Isolation with Firewall Rules (pf), Including Rollback
To enforce network-layer access control and secure our application architecture, we implemented Packet Filter (pf) firewall rules on Mac 3 hosting Backend A on port 3001. We configured rules in `noaa_pf.conf` allowing loopback traffic and incoming TCP connections to port 3001 strictly from authorized edge IP addresses (10.7.27.60 and 10.7.11.131) while blocking and dropping all other packets (`block drop in quick proto tcp from any to any port 3001`). When testing with `curl` and `nc`, requests from the edge succeeded with HTTP 200, whereas direct connection attempts from unauthorized client machines timed out because dropped SYN packets silently discarded connection attempts without RST generation. We then executed a clean rollback by reloading the default `/etc/pf.conf` and disabling pf, verifying complete restoration via `pfctl -sr`. We learned that firewalls enforce least-privilege transport-layer isolation protecting vulnerable microservices, but proper operational procedures require backup rule verification to prevent accidental administrator lockouts or permanent disruptions. *(Owner: Ayush)*

### D: nginx Failover Between Backends
To make the application resilient against backend server outages, we enhanced the nginx edge configuration on Mac 2 by adding active failover directives within the upstream block and proxy handling. Specifically, we configured `max_fails=1 fail_timeout=10s` for each backend server and enabled `proxy_connect_timeout 2s`, `proxy_next_upstream error timeout http_502 http_503 http_504`, and `proxy_next_upstream_tries 2`. During steady state, round-robin load balancing evenly alternated requests between Backend A (10.7.11.131:3001) and Backend B (10.7.11.144:3002). When we stopped Backend A's process, the client experienced zero failed requests; nginx received an immediate TCP connection refusal, marked Backend A temporarily unavailable, and transparently retried the active request against Backend B within milliseconds. In nginx access logs, we observed the upstream status transition recorded as `502 : 200`. We learned that application-layer reverse proxies provide high availability by hiding upstream transport failures, converting potential 502 Bad Gateway outages into seamless downstream user experiences. *(Owner: Neeraj)*

### E: Controlled Edge Migration Using DNS
To upgrade or service edge infrastructure without service interruption, we executed a controlled edge migration by spinning up an identical standby nginx reverse proxy on Mac 3 (10.7.11.131:8443) featuring custom diagnostic header `add_header X-Edge standby always`. We ran both edges concurrently during an overlap window, validating end-to-end TLS, HTTP/2 negotiation, and backend proxying on Mac 3. Next, we updated DNS records in dnsmasq from Mac 2 (10.7.27.60) to Mac 3 (10.7.11.131). We observed that traffic gradually shifted over the 30-second TTL window; once client DNS caches expired, all incoming requests hit the standby edge as confirmed by `x-edge: standby` headers in `/usr/bin/curl` responses. Finally, we gracefully stopped Mac 2's nginx with zero dropped requests and later demonstrated clean rollback by reverting DNS records. We learned that DNS-directed blue-green migration decouples physical hardware maintenance from availability, provided TTL caching windows, upstream parity, and simultaneous TLS certificate validity across edges are rigorously maintained. *(Owner: Ayush & Neeraj)*

### F: Troubleshooting Challenge
To build rapid incident response capability, our team conducted structured troubleshooting drills against deliberately injected system faults using our automated script `diagnose.sh`. The diagnostic workflow followed an orderly bottom-up layered model: LAN connectivity, DNS resolution, TCP port reachability, TLS handshakes, and HTTP application responses. In Drill 1, when primary DNS was disabled on Mac 1, `dig @10.7.5.107` timed out, immediately pinpointing the DNS layer and leading us to restart dnsmasq. In Drill 2, when nginx was stopped on Mac 2, DNS resolved correctly but `nc -vz -G 3 10.7.27.60 8443` failed with connection refused, isolating the issue strictly to the TCP/web server layer and prompting an nginx service restart. We observed that evaluating layers sequentially prevented erroneous diagnosis and saved crucial time. We learned that effective network operations depend on deterministic diagnostic chains and standardized tooling rather than blind trial and error, enabling rapid identification of exact failure domains. *(Owner: Team / Neeraj)*

---

## 4. Resilience Tests and Results

The table below catalogs the fault injection experiments conducted across the platform to evaluate system recovery, detection, and containment.

| Test | What We Broke or Changed | Expected Behavior | Observed Behavior | Layer | Evidence File |
|---|---|---|---|---|---|
| **Primary DNS Failover** | Stopped primary `dnsmasq` service on Mac 1 (`10.7.5.107`). | Client resolver falls back to secondary nameserver (`10.7.11.144`); zero DNS resolution failure. | Query to `10.7.5.107` timed out; query to `10.7.11.144` returned `10.7.27.60` instantly; client queries resolved seamlessly. | Application / Transport (UDP 53) | `09_DNS_backup_working.png`, `09_DNS_remote_test.png`, `local_dns_test.txt` |
| **Controlled DNS TTL Expiration** | Reduced TTL to 5s on Mac 1; updated A record for `app.noaa.test` to test target. | Client utilizes cached record until 5s expires, then immediately retrieves updated record. | Initial resolution served old record from OS cache; at $t > 5\text{s}$, subsequent lookups resolved new IP address. | Application (DNS) | `10_TTL_old_cache_established.png`, `10_TTL_dns_record_updated.jpg`, `10_TTL_cache_expiry.png`, `10_TTL_client_new_resolution.png` |
| **Backend Isolation Enforcement** | Loaded `noaa_pf.conf` on Mac 3 blocking non-edge traffic to port 3001. | Allowed edge IPs (`10.7.27.60`, `10.7.11.131`) connect; direct LAN client requests drop/timeout. | Nginx reverse proxy forwarded traffic successfully (HTTP 200); direct client `curl` timed out as SYN packets were dropped. | Network / Transport (TCP Port 3001) | `11_ISO_edge_ok.png.jpeg`, `11_ISO_active_rules_mac3.txt` |
| **Firewall Emergency Rollback** | Flushed custom rules using `pfctl -d` and reloaded standard `/etc/pf.conf`. | Complete restoration of default network policy; direct client communication to port 3001 unblocked. | Rules returned to baseline anchors; direct client connections to Backend A succeeded without host reboot. | Network / Transport | `11_ISO_restored_mac3.png`, `11_ISO_restored.png.jpeg`, `11_ISO_restored_mac3.txt` |
| **Backend A Service Crash** | Terminated Backend A node process on Mac 3 (`10.7.11.131:3001`). | Nginx catches connection refused, marks node down for 10s, and retries Backend B. | Client experienced zero HTTP errors; received HTTP 200; Nginx log recorded `upstream_status=502 : 200`. | Application (HTTP Reverse Proxy) / Transport | `12_FO_A_Down.png`, `12_FO_Logs.png`, `12_FO_Restored.png`, `12_FO_502.png` |
| **Blue-Green Edge Migration** | Deployed standby Nginx on Mac 3 (`10.7.11.131`), switched DNS A record, stopped Mac 2. | Clients migrate to standby edge over 30s TTL window; zero dropped requests during cutover. | Active traffic transitioned to Mac 3 (evidenced by header `x-edge: standby`); service remained live after stopping Mac 2. | Application (DNS, HTTP/2, TLS) | `13_MIG_standby_nginx.png`, `13_MIG_overlap.png.jpeg`, `13_MIG_after.png.jpeg`, `13_MIG_mac2_stopped.png.jpeg` |
| **Troubleshooting Practice Drill 1** | Shut down `dnsmasq` on primary DNS server (Mac 1). | Layered check detects failure at DNS step; system restores once service is restarted. | `diagnose.sh` halted at Step 1 (`DNS FAILED: No IP address returned`); restarting `dnsmasq` restored full pass. | Application (DNS) | `14_drill1_dns_failure.png`, `14_drill1_diagnosis.png`, `14_drill1_dns_restored.png`, `14_drill1_application_restored.png` |
| **Troubleshooting Practice Drill 2** | Stopped `nginx` daemon on main edge server (Mac 2). | Layered check passes DNS but fails at TCP handshake; restarting Nginx restores full HTTP 200. | `diagnose.sh` succeeded at Step 1 but halted at Step 2 (`TCP FAILED: Port 8443 is unreachable`); restored upon starting Nginx. | Transport (TCP Port 8443) | `14_drill2_nginx_failure.png`, `14_drill2_diagnosis.png`, `14_drill2_nginx_restored.png`, `14_drill2_application_restored.png` |

---

## 5. Troubleshooting Findings

### A. The Five-Layer Diagnostic Methodology
When troubleshooting networked distributed platforms, leaping directly to application log inspection or modifying configuration files causes confusion. We codified and adhered to an orderly five-layer diagnostic procedure implemented in our automated script `diagnose.sh`:

1. **Layer 1: Basics / Physical & Network Connectivity (LAN):** Verify network interface status, local IP assignment (`ipconfig getifaddr en0`), and bidirectional LAN reachability using ICMP `ping`. This confirms that link-layer framing and IPv4 routing are intact.
2. **Layer 2: Domain Name System (DNS):** Verify resolution of service domain names (`app.noaa.test`, `api.noaa.test`) via `dig +time=2 +tries=1 +noall +answer $NAME` and inspect `/etc/hosts` for stale static overrides. This isolates name resolution from service availability.
3. **Layer 3: Transport Layer (TCP):** Test end-to-end transport-layer port reachability using `nc -vz -G 3 $IP $PORT`. This confirms that the remote host is reachable, firewall filters allow the packet, and a listening socket accepted the SYN packet with a SYN-ACK.
4. **Layer 4: Transport Layer Security (TLS):** Inspect cryptographic handshake, certificate authority validation, Common Name / SAN matching, and cipher negotiation using `curl -sv --max-time 5 -o /dev/null https://$NAME:$PORT/`. This validates PKI trust chains without application interference.
5. **Layer 5: Application Layer (HTTP/2):** Evaluate end-to-end application protocol responses, status codes, and proxy routing headers (`X-Backend`, `X-Edge`) using `curl -sI --max-time 5 https://$NAME:$PORT/api/status`.

### B. Common Symptoms and Root Cause Analysis Matrix

| Symptom / Error Message | Likely Root Causes | Verification Command | Corrective Action |
|---|---|---|---|
| `Could not resolve host: app.noaa.test` / DNS query timed out | `dnsmasq` daemon stopped; incorrect nameserver in `/etc/resolv.conf`; port 53 UDP traffic blocked. | `dig @<DNS_IP> app.noaa.test` | Restart `dnsmasq` (`sudo brew services restart dnsmasq`); fix client DNS settings. |
| `nc: connect to 10.7.27.60 port 8443: Connection refused` | Nginx service is stopped; Nginx crashed due to configuration error; listening only on `127.0.0.1`. | `sudo lsof -i :8443` or `ps aux \| grep nginx` | Validate config with `nginx -t`; start Nginx daemon (`sudo nginx`). |
| `nc: connect to 10.7.11.131 port 3001: Operation timed out` | Packet Filter (`pf`) dropping incoming TCP SYN packets; IP route missing; host down. | `sudo pfctl -sr` (on server) | Update `/etc/pf.conf` to whitelist client IP; disable blocking rules with `sudo pfctl -d`. |
| `curl: (60) SSL certificate problem: self signed certificate in certificate chain` | Tool environment (e.g. Conda) not reading macOS System Keychain; root CA missing from local trust store. | `/usr/bin/curl -v https://app.noaa.test:8443` vs `which curl` | Use system curl `/usr/bin/curl` or pass CA explicitly via `--cacert /path/to/ca.crt`. |
| `HTTP/1.1 502 Bad Gateway` returned by Nginx | Both backend nodes (3001 and 3002) are down simultaneously; firewall blocking Nginx from backends. | `nc -vz 10.7.11.131 3001` and `nc -vz 10.7.11.144 3002` from Nginx | Restart backend Node.js processes; verify firewall rules on backend nodes. |
| Client requests directed to old edge after DNS migration | Resolver cache (mDNSResponder) caching response until TTL expires; stale `/etc/hosts` override. | `dscacheutil -q host -a name app.noaa.test` and `grep noaa /etc/hosts` | Flush local cache (`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`); clean `/etc/hosts`. |
| `grep` filter on HTTP response headers yields empty output | Searching for uppercase header names (`X-Edge`) over HTTP/2; RFC 7540 mandates lowercase headers. | `curl -sI https://app.noaa.test:8443/api/status \| grep -i x-edge` | Always perform case-insensitive header matches (`grep -i`) or inspect lowercase `x-edge`. |

### C. Write-Up of Practice Drills

#### Drill 1: Primary DNS Service Outage
- **Fault Injected:** The primary DNS service (`dnsmasq`) was stopped on Mac 1 (`10.7.5.107`).
- **Commands Executed in Order:**
  1. `./diagnose.sh app.noaa.test 8443` $\rightarrow$ Failed immediately at Step 1 (`DNS FAILED: No IP address returned`).
  2. `dig @10.7.5.107 app.noaa.test` $\rightarrow$ Query timed out after 2000 ms with no answer.
  3. `dig @10.7.11.144 app.noaa.test` $\rightarrow$ Responded with `10.7.27.60`, confirming backup DNS operational.
  4. `ssh om@10.7.5.107 "sudo brew services list"` $\rightarrow$ Showed `dnsmasq` stopped.
- **Failing Layer:** Layer 2 (DNS Resolution / Application Layer UDP 53).
- **Root Cause:** The `dnsmasq` process on Mac 1 was terminated, leaving port 53 unresponsive.
- **Fix Applied & Verification:** Executed `sudo brew services start dnsmasq` on Mac 1. Re-running `dig @10.7.5.107 app.noaa.test` returned `10.7.27.60` in 2 ms. Re-executed `./diagnose.sh`, achieving 100% SUCCESS across all five layers (`14_drill1_application_restored.png`).

#### Drill 2: Active Edge Reverse Proxy Outage
- **Fault Injected:** The `nginx` edge reverse proxy service was stopped on Mac 2 (`10.7.27.60`).
- **Commands Executed in Order:**
  1. `./diagnose.sh app.noaa.test 8443` $\rightarrow$ Step 1 (DNS) reported SUCCESS (`10.7.27.60`), but Step 2 halted with `TCP FAILED: Port 8443 is unreachable`.
  2. `nc -vz -G 3 10.7.27.60 8443` $\rightarrow$ Connection refused immediately.
  3. `ssh neeraj@10.7.27.60 "ps aux | grep nginx"` $\rightarrow$ Confirmed no active master or worker processes.
- **Failing Layer:** Layer 3 (Transport Layer / TCP port 8443 handshake).
- **Root Cause:** Nginx daemon was terminated, resulting in kernel sending TCP RST upon receiving SYN packets on port 8443.
- **Fix Applied & Verification:** Tested configuration on Mac 2 with `sudo nginx -t` (syntax ok), then restarted daemon with `sudo nginx`. Repeated `nc -vz -G 3 10.7.27.60 8443` (succeeded). Executed `./diagnose.sh`, verifying complete TLS handshake, certificate validity, and HTTP/2 200 OK application response (`14_drill2_application_restored.png`).

---

## 6. Single Point of Failure (SPOF) Analysis

### What Remains a Single Point of Failure
Despite hardening our platform with redundant DNS resolvers, backend load balancing failover, and firewall isolation, **the active Nginx edge reverse proxy remains a Single Point of Failure (SPOF)**. 

In our Phase 2 architecture:
1. At any given moment, client traffic is directed towards a single active IP address (Mac 2 at `10.7.27.60`, or Mac 3 at `10.7.11.131` post-migration).
2. If the active edge machine suffers an unannounced catastrophic failure (hardware crash, kernel panic, physical interface disconnection, or power loss), incoming client traffic is instantly blackholed.
3. Although we proved that DNS migration can shift traffic to the standby edge, DNS is fundamentally **not** an instantaneous failover mechanism. Clients and recursive resolvers cache DNS answers according to the TTL (e.g., 5 to 30 seconds). Furthermore, many client operating systems and applications fail to re-query DNS immediately upon TCP failure, resulting in client-visible downtime until manual intervention or automated health checks update the DNS zone and client caches purge.

### How to Completely Eliminate This SPOF
To achieve true, enterprise-grade high availability at the edge without single points of failure, the platform would require:

1. **Virtual Router Redundancy Protocol (VRRP) with Keepalived:**
   - Configure a single shared Virtual IP (VIP) address (e.g., `10.7.27.100`) between Mac 2 (Master) and Mac 3 (Backup).
   - Both nodes run `keepalived` exchanging periodic multicast heartbeat advertisements.
   - If Mac 2 drops heartbeats for more than a configured threshold (e.g., 1–2 seconds), Mac 3 automatically claims the VIP by broadcasting Gratuitous ARP packets across the LAN switch.
   - Client DNS records point permanently to the VIP. Clients experience sub-second failover without requiring any DNS record changes or cache flushes.
2. **Anycast BGP / Equal-Cost Multi-Path (ECMP) Routing:**
   - In a routed network environment, both edge servers announce the same IP prefix to top-of-rack switches using BGP.
   - Switches distribute connections across both edges simultaneously. If one edge fails, the BGP peering session terminates (or BFD triggers), and the router immediately diverts subsequent TCP flows to the surviving edge.

---

## 7. Problems We Hit and How We Fixed Them

During implementation and testing, we encountered five distinct network-layer and toolchain challenges:

1. **Conda curl Ignored macOS System Keychain:**
   - *Problem:* When verifying HTTPS connections using `curl`, requests failed with `curl: (60) SSL certificate problem: self signed certificate in certificate chain`, even though our custom CA certificate (`ca.crt`) was explicitly trusted in the macOS System Keychain.
   - *Root Cause:* The active shell session defaulted to Anaconda's bundled `curl` binary (`~/miniconda3/bin/curl`), which is compiled against OpenSSL and relies on its own static CA bundle rather than querying the native macOS Security framework / Keychain Services.
   - *Fix:* Executed the native operating system binary explicitly via `/usr/bin/curl`, which uses SecureTransport / Apple Keychain natively and validated our private CA certificate without error.
2. **HTTP/2 Header Names are Lowercase:**
   - *Problem:* Our automated scripts and verification commands failed to detect the custom standby edge identification header, reporting missing headers despite Nginx emitting `add_header X-Edge standby always`.
   - *Root Cause:* Case-sensitive pattern matching (`grep "X-Edge"`) was used on HTTP responses. Under the HTTP/2 specification (RFC 7540 Section 8.1.2), all HTTP header field names MUST be converted by processors to lowercase characters prior to transmission.
   - *Fix:* Modified all inspection filters to use case-insensitive matching (`grep -i x-edge`) or explicitly match the RFC-compliant lowercase token (`grep "x-edge"`).
3. **Stale DNS Answers from Orphaned Processes and Local Hosts File:**
   - *Problem:* During edge migration testing, DNS resolution queries to Om's Mac (Mac 1) intermittently returned obsolete Phase 1 IP addresses rather than the updated standby edge IP.
   - *Root Cause:* Two compounding issues were discovered: an orphaned, background `dnsmasq` process was running concurrently with the primary service binding to old configuration files, and lingering hardcoded mappings for `app.noaa.test` existed in `/etc/hosts` on Mac 1.
   - *Fix:* Killed all running instances (`sudo killall dnsmasq`), sanitized `/etc/hosts` by removing manual test overrides, and cleanly restarted the service using Homebrew services (`sudo brew services restart dnsmasq`).
4. **Client DNS TTL Caching Delay During Migration:**
   - *Problem:* Following the authoritative DNS record update pointing `app.noaa.test` to Mac 3, several client requests continued hitting Mac 2 for approximately 30 seconds before cutover occurred.
   - *Root Cause:* Operating system resolver daemons (macOS `mDNSResponder`) maintain a local DNS cache that honors the previously fetched record's TTL window, preventing immediate re-querying until cache expiry.
   - *Fix:* For testing and controlled switchovers, we documented the requirement to lower TTL values prior to migration windows and utilized manual cache invalidation commands (`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`) on client testbeds.
5. **Tool Discrepancy Between `dig`, `curl`, and `dscacheutil`:**
   - *Problem:* Running `dig` showed the updated DNS record instantly, while `curl` concurrently connected to the old IP address, creating apparent contradictions during diagnosis.
   - *Root Cause:* `dig` (Domain Information Groper) is an administrative network diagnostic tool that constructs raw UDP datagrams directly to specified nameservers, deliberately bypassing the OS resolver cache. Conversely, standard user-space applications like `curl` make system library calls (`getaddrinfo`) managed by macOS `mDNSResponder`, which serves cached entries until local TTL expiration.
   - *Fix:* Formulated our troubleshooting methodology to separate authoritative server checks (`dig @<server>`) from local resolver cache inspections (`dscacheutil -q host -a name <domain>`).

---

## 8. Conclusion

In Phase 2, we advanced our private network service platform from a fragile, single-server setup into a hardened, resilient infrastructure. By implementing redundant DNS resolvers, dynamic nginx upstream failover, Packet Filter packet isolation, low-TTL blue-green edge migration, and rigorous multi-layer diagnostic drills, we systematically addressed several critical failure domains. Our resilience tests verified that backend or primary DNS outages no longer degrade end-user availability. While the active edge server remains a remaining architectural single point of failure, we developed a clear roadmap using Anycast BGP or VRRP/keepalived to achieve true high availability. Phase 2 provided invaluable practical insight into transport, routing, application, and security protocols across modern networks.

---

## 9. Appendix

### A. List of Configuration Files
1. **DNS Configurations:**
   - `phase-2/09_BackupDNS/dnsmasq_mac4.conf` (Backup DNS resolver configuration on Mac 4)
   - `phase-2/09_BackupDNS/dnsmasq_before_phase2.conf` (Baseline DNS reference configuration)
   - `phase-2/Updated_phase1_IP/configs/dnsmasq_updated.conf` (Primary DNS configuration on Mac 1)
2. **Reverse Proxy (Nginx) Configurations:**
   - `phase-2/12_Failover/nginx_phase1_backup.conf` (Phase 1 Nginx baseline config)
   - `phase-2/Updated_phase1_IP/configs/nginx_upstream_updated.conf` (Updated upstream block)
   - `phase-2/13_Migration/nginx_standby.conf` (Standby Edge Nginx configuration with failover & `X-Edge` header)
3. **Firewall (Packet Filter) Configurations:**
   - `phase-2/11_Isolation/noaa_pf.conf` (Active service isolation rules for port 3001)
   - `phase-2/11_Isolation/pf_rules_before.txt` (Default OS anchor baseline rules)
4. **Diagnostic Script:**
   - `phase-2/14_Troubleshooting/diagnose.sh` (Automated 5-layer network diagnostic test suite)

### B. List of Evidence Files

#### Extension A: Backup DNS Resolver (`phase-2/09_BackupDNS/`)
- `09_DNS_backup_config.png` — Configuration verification on Mac 4.
- `09_DNS_service_running.png` — Service status showing dnsmasq active on port 53.
- `09_DNS_local_test.png` — Local resolution query test (`dig @127.0.0.1`).
- `09_DNS_remote_test.png` — Remote resolution test across LAN (`dig @10.7.11.144`).
- `09_DNS_backup_working.png` — Verification of client failover to backup resolver.
- `local_dns_test.txt`, `port53_status.txt`, `service_status.txt` — Log output verifications.

#### Extension B: DNS TTL & Record Updates (`phase-2/10_TTL/`)
- `10_TTL_old_cache_established.png` — Baseline query caching under initial TTL.
- `10_TTL_dns_record_updated.jpg` — DNS authoritative record modification in dnsmasq.
- `10_TTL_cache_expiry.png` — Observation of local cache TTL expiration timing.
- `10_TTL_client_new_resolution.png` — Successful client resolution of updated address.
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
- `12_FO_Logs.png` — Access logs showing upstream failover (`upstream_status=502 : 200`).
- `12_FO_Restored.png` — Recovery verification once Backend A process restarted.
- `12_FO_502.png` — Error capture during dual backend failure scenario.

#### Extension E: Controlled Edge Migration (`phase-2/13_Migration/`)
- `13_MIG_standby_nginx.png` — Standby Nginx listening on port 8443 on Mac 3.
- `13_MIG_overlap.png.jpeg` — Concurrent execution of both edges during migration window.
- `13_MIG_after.png.jpeg` — Client requests reaching standby edge (`x-edge: standby`).
- `13_MIG_mac2_stopped.png.jpeg` — Zero downtime verified after stopping main edge on Mac 2.
- `13_MIG_rollback.png.jpeg` — Rollback verification returning traffic to Mac 2.

#### Extension F: Troubleshooting Drills & Scripts (`phase-2/14_Troubleshooting/`)
- `14_diagnose_healthy.png` — Output of `diagnose.sh` passing all 5 layers under normal state.
- `14_drill1_dns_failure.png` — Drill 1: `diagnose.sh` isolating failure at DNS layer.
- `14_drill1_diagnosis.png` — Drill 1: Direct dig query confirming port 53 timeout.
- `14_drill1_dns_restored.png` — Drill 1: DNS service restarted and verified.
- `14_drill1_application_restored.png` — Drill 1: Full system diagnostic pass after DNS fix.
- `14_drill2_nginx_failure.png` — Drill 2: `diagnose.sh` isolating failure at TCP port 8443.
- `14_drill2_diagnosis.png` — Drill 2: Netcat connection refused verification.
- `14_drill2_nginx_restored.png` — Drill 2: Nginx restarted and port 8443 listening.
- `14_drill2_application_restored.png` — Drill 2: Full system diagnostic pass after Nginx fix.
- `14_mac1_dns_healthy.png`, `14_mac2_nginx_healthy.png`, `14_mac3_backendA_healthy.png`, `14_mac4_backendB_dns_healthy.png` — Node health verifications.
- `14_full_system_healthy01.png`, `14_full_system_healthy02.png` — Complete platform end-to-end operational verifications.
- `14_learning_notes.md` — Detailed engineering notes on layered troubleshooting methodology.

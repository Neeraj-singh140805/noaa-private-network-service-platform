# Phase 1 — Step 7: Packet Capture Evidence

**Evidence folder:** `07_Wireshark`  
**Client used for capture:** Mac 4 (`10.7.11.144`)  
**Nginx / HTTPS server:** Mac 2 (`10.7.11.79`)  
**DNS server:** `10.7.11.132`  
**HTTPS hostname and port:** `app.noaa.test:8443`

This file lists the screenshots in serial order and explains what each one demonstrates.

## Screenshot index

| No. | Filename | What it shows |
|---:|---|---|
| 01 | `01_dns_query_response.png` | Wireshark DNS query for `app.noaa.test` from Mac 4 to the DNS server, followed by the response resolving the hostname to `10.7.11.79` (Mac 2). Shows DNS over UDP port 53. |
| 02 | `02_tcp_three_way_handshake.png` | TCP three-way handshake for the HTTPS connection: SYN from Mac 4 to Mac 2, SYN-ACK from Mac 2 to Mac 4, and ACK from Mac 4. The server port is 8443 and the client uses an ephemeral port. |
| 03 | `03_tcp_sequence_acknowledgement.png` | Expanded TCP packet details showing sequence and acknowledgement numbers. These fields demonstrate TCP's numbering and acknowledgement mechanism. A second screenshot or crop of screenshot 02 can be used if the values are readable. |
| 04 | `04_tls_clienthello_serverhello.png` | Filtered Wireshark view showing the ClientHello from Mac 4 and ServerHello from Mac 2 for the `app.noaa.test` HTTPS connection. Demonstrates the TLS negotiation. |
| 05 | `05_tls12_certificate.png` | TLS 1.2 Certificate handshake packet, preferably with the TLS details expanded. Shows the server certificate sent during the TLS 1.2 handshake. |
| 06 | `06_tls_change_cipher_spec.png` | TLS Change Cipher Spec packet(s) from the TLS 1.2 connection. Use this screenshot as evidence of the Change Cipher Spec message. |
| 07 | `07_tls_encrypted_application_data.png` | TLS Application Data packets filtered with `tls.record.content_type == 23`. The application payload is encrypted and is not readable in the packet view. |
| 08 | `08_https_curl_success.png` | Terminal output from a successful `curl -v` request to `https://app.noaa.test:8443/api/status`, showing certificate verification, an HTTP 200 response, and the JSON status body. |
| 09 | `09_load_balancing_six_requests.png` | Final six-request test through Nginx showing one `X-Backend` header per request and traffic alternating between Backend A and Backend B. Use the final clean output, not earlier attempts. |
| 10 | `10_port_table.png` | Screenshot of the port table prepared for the project. It documents DNS using UDP port 53 and HTTPS using TCP port 8443, along with the observed client ephemeral ports. |
| 11 | `11_wireshark_unfiltered_live_capture.png` | Unfiltered Wireshark screenshot showing a live capture on Wi-Fi interface `en0` and a mixed packet list. It serves as a general view of the packet capture in progress; protocol-specific evidence is shown in the filtered screenshots. |
| 12 | `12_wireshark_unfiltered_packet_overview.png` | Unfiltered Wireshark screenshot showing the broader packet list and the selected packet's details, without a display filter. It provides a general overview of captured network traffic; use the filtered screenshots for individual protocol evidence. |

## Packet-capture files

| Filename | What it contains |
|---|---|
| `phase1_full.pcapng` | Full capture of a normal HTTPS request negotiated with TLS 1.3. Use it for TLS 1.3 handshake and encrypted application-data evidence. |
| `phase1_tls12.pcapng` | Capture made with TLS limited to version 1.2. Use it to show the Certificate handshake packet and Change Cipher Spec message. |

## Port table

| Layer / protocol | Client IP | Client port | Transport | Server IP | Server port |
|---|---|---:|---|---|---:|
| DNS | `10.7.11.144` | `6106` (observed ephemeral port; may vary) | UDP | `10.7.11.132` | `53` |
| HTTPS | `10.7.11.144` | `54793` (observed ephemeral port; may vary) | TCP | `10.7.11.79` | `8443` |

Client ephemeral ports can change between connections. The values above are examples from the captures discussed; retain the values visible in the final screenshots if they differ.

## Screenshot notes

- Save all evidence in `07_Wireshark` using the filenames above.
- Keep the relevant Wireshark display filter visible for filtered screenshots.
- For DNS, show both the query and the response, with the answer expanded to show `10.7.11.79`.
- For TCP, keep the SYN, SYN-ACK and ACK packets visible. Expand TCP details for the sequence and acknowledgement evidence.
- Use the TLS 1.2 capture for the Certificate and Change Cipher Spec evidence. In TLS 1.3, parts of the handshake, including the certificate, are encrypted.
- Useful annotations include `DNS answer = 10.7.11.79`, `SYN`, `SYN-ACK`, `ACK`, and `Encrypted Application Data`.
- The two unfiltered Wireshark screenshots are general overviews and do not replace the protocol-filtered evidence screenshots.

## Completion check

Before submitting, confirm that the folder contains the required screenshots, both `.pcapng` files, and this `description.md`. Save the port-table photo as `10_port_table.png` and the successful curl terminal screenshot as `08_https_curl_success.png` if either has not yet been added.

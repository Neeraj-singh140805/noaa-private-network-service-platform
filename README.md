# 🌐 NOAA — Private Network Service Platform

### Computer Networks Course Project — Phase 1

A fully local private network service platform demonstrating:

**LAN → DNS → TCP → TLS → HTTPS → nginx Reverse Proxy → Load Balancing → HTTP Caching → Wireshark Analysis**

---

## 📌 Project Overview

Team **NOAA** is implementing a private network service platform using multiple macOS machines connected to the same local network.

The client accesses a private `.test` domain:

```text
app.noaa.test



Client
   │
   │ DNS
   ▼
Private DNS Server
   │
   │ IP address of Edge
   ▼
nginx Edge / Reverse Proxy
   │
   │ HTTPS / TLS
   ▼
Load Balancer
   │
   ├──────────────► Backend A :3001
   │
   └──────────────► Backend B :3002
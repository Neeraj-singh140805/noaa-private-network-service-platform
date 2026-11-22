
# Phase 2 — Extension F: Troubleshooting Practice

## 1. Objective

The objective was to practise identifying and resolving network failures using a systematic, layered troubleshooting approach.

## 2. Troubleshooting Method

We followed this sequence:

1. Basics / LAN — Check network connectivity.
2. DNS — Verify hostname resolution.
3. TCP — Check whether the required port is reachable.
4. TLS — Verify HTTPS connection and certificate.
5. HTTP / Application — Check the application response.

## 3. Drill 1 — Primary DNS Failure

**Fault introduced:** Primary DNS service (dnsmasq) was stopped on Mac 1.

**Diagnosis:** The client could not resolve app.noaa.test using the primary DNS server.

**Diagnostic command:**
dig @10.7.5.107 app.noaa.test

**Affected layer:** DNS.

**Root cause:** dnsmasq was not running.

**Fix:** Restarted dnsmasq on Mac 1.

**Verification:** DNS resolution was restored and the application was tested again.

## 4. Drill 2 — nginx Failure

**Fault introduced:** nginx was stopped on Mac 2.

**Diagnosis:** DNS resolution continued working, but the client could not establish a TCP connection to port 8443.

**Diagnostic command:**
nc -vz -G 3 10.7.27.60 8443

**Affected layer:** TCP / Web server.

**Root cause:** nginx was not listening on port 8443.

**Fix:** Restarted nginx on Mac 2.

**Verification:** TCP connectivity was restored and the application returned HTTP 200.

## 5. Diagnostic Script

We created diagnose.sh to automate checks for:

- DNS resolution
- TCP connectivity
- TLS certificate and handshake
- HTTP response

The script was tested in healthy and faulty conditions.

## 6. Learning Outcomes

This exercise demonstrated the importance of troubleshooting network systems layer by layer. We learned that a DNS failure, a closed TCP port and an application failure require different diagnostic methods. Checking each layer in sequence helps identify the actual failure point instead of making unnecessary configuration changes.


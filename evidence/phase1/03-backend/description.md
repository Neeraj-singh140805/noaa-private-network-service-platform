# Task C — Backend Services

## Objective

The objective of this task is to configure and verify two backend
application servers that provide the services used by the NOAA private
network.

Two backend instances are used:

- Backend A
- Backend B

Each backend runs on a separate machine and listens on a different
HTTP port.

## Backend Architecture

| Backend | Machine | IP Address | HTTP Port |
|---|---|---|---|
| Backend A | Mac 3 | `10.7.11.131` | `3001` |
| Backend B | Mac 4 | `10.7.11.144` | `3002` |

The backend services are accessed directly using HTTP during the
backend verification stage.

## Backend A

Backend A is hosted on Mac 3.

```text
IP Address: 10.7.11.131
HTTP Port: 3001
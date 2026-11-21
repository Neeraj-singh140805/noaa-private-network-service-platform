# TLS Configuration

## Objective

Configure HTTPS on the Nginx edge server using a locally created
Certificate Authority (CA).

## Certificate Details

The server certificate was generated using OpenSSL for the NOAA
private network service.

### Domains

- `app.noaa.test`
- `api.noaa.test`

### HTTPS

- Port: `8443`
- TLS versions: `TLSv1.2` and `TLSv1.3`

## Certificate Generation

The certificate was generated previously using OpenSSL.

The process included:

1. Creating a local NOAA Certificate Authority.
2. Generating the server private key.
3. Generating a Certificate Signing Request (CSR).
4. Creating a Subject Alternative Name (SAN) configuration.
5. Signing the server certificate using the local CA.
6. Verifying the generated certificate.
7. Configuring the certificate in Nginx.
8. Testing the Nginx configuration using `nginx -t`.
9. Reloading Nginx.

## Nginx TLS Configuration

The Nginx edge server uses HTTPS on port `8443`.

```nginx
server {
    listen 8443 ssl;
    http2 on;

    server_name app.noaa.test api.noaa.test;

    ssl_certificate /path/to/server.crt;
    ssl_certificate_key /path/to/server.key;

    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://app_backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

#!/bin/bash

NAME=${1:-app.noaa.test}
PORT=${2:-8443}

echo "================================"
echo " NETWORK DIAGNOSTIC REPORT"
echo "================================"

echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "IP: $(ipconfig getifaddr en0)"

echo ""
echo "== 1. DNS CHECK =="

dig +time=2 +tries=1 +noall +answer "$NAME"

IP=$(dig +short +time=2 +tries=1 "$NAME" | head -1)

if [ -z "$IP" ]; then
    echo "DNS FAILED: No IP address returned."
    exit 1
fi

echo "DNS SUCCESS: $NAME resolves to $IP"

grep -i noaa /etc/hosts

echo ""
echo "== 2. TCP CHECK =="

nc -vz -G 3 "$IP" "$PORT"

if [ $? -ne 0 ]; then
    echo "TCP FAILED: Port $PORT is unreachable."
    exit 1
fi

echo ""
echo "== 3. TLS CHECK =="

curl -sv --max-time 5 -o /dev/null "https://$NAME:$PORT/" 2>&1 | grep -E "SSL connection|subject:|issuer:|verify|expire|error"

echo ""
echo "== 4. HTTP CHECK =="

curl -sI --max-time 5 "https://$NAME:$PORT/api/status" | grep -E "HTTP|X-Backend|X-Edge"

echo ""
echo "================================"
echo " DIAGNOSTIC CHECK COMPLETE"
echo "================================"


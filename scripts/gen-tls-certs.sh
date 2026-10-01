#!/usr/bin/env bash
# ==============================================================================
# Script: gen-tls-certs.sh
# Purpose: Generate self-signed TLS certificates for local Nginx reverse proxy
# ==============================================================================
set -euo pipefail

CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../nginx/certs" && pwd)"
mkdir -p "$CERTS_DIR"

echo "Generating local TLS certificates in $CERTS_DIR ..."

if command -v openssl >/dev/null 2>&1; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERTS_DIR/key.pem" \
    -out "$CERTS_DIR/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=ShopMate Enterprise/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
  echo "TLS certificates created successfully with openssl."
else
  python -c "
import ipaddress
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

certs_dir = Path('$CERTS_DIR')
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ShopMate Enterprise'),
    x509.NameAttribute(NameOID.COMMON_NAME, 'localhost'),
])
cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.now(datetime.timezone.utc)
).not_valid_after(
    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.IPv4Address('127.0.0.1'))]),
    critical=False,
).sign(key, hashes.SHA256())

with open(certs_dir / 'key.pem', 'wb') as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

with open(certs_dir / 'cert.pem', 'wb') as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
print('TLS certificates created successfully with Python cryptography.')
"
fi

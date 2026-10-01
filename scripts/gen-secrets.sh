#!/usr/bin/env bash
# ==============================================================================
# Script: gen-secrets.sh
# Purpose: Generate high-entropy secrets and RS256 asymmetric keys for production
# ==============================================================================
set -euo pipefail

echo "================================================================="
echo "  GENERATING PRODUCTION SECRETS FOR SHOPMATE AAAS PLATFORM"
echo "================================================================="

gen_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
  fi
}

POSTGRES_PW=$(gen_secret)
POSTGRES_APP_PW=$(gen_secret)
REDIS_PW=$(gen_secret)
SESSION_SECRET=$(gen_secret)
ENCRYPTION_SECRET=$(gen_secret)

# Generate RS256 Asymmetric Key Pair
TMP_DIR=$(mktemp -d)
if command -v openssl >/dev/null 2>&1; then
  openssl genpkey -algorithm RSA -out "$TMP_DIR/private.pem" -pkeyopt rsa_keygen_bits:2048 2>/dev/null
  openssl rsa -pubout -in "$TMP_DIR/private.pem" -out "$TMP_DIR/public.pem" 2>/dev/null
  PRIVATE_KEY_B64=$(base64 < "$TMP_DIR/private.pem" | tr -d '\r\n')
  PUBLIC_KEY_B64=$(base64 < "$TMP_DIR/public.pem" | tr -d '\r\n')
else
  KEYS_JSON=$(node -e "
    const crypto = require('crypto');
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });
    console.log(JSON.stringify({
      priv: Buffer.from(privateKey).toString('base64'),
      pub: Buffer.from(publicKey).toString('base64')
    }));
  ")
  PRIVATE_KEY_B64=$(echo "$KEYS_JSON" | node -e "let data=''; process.stdin.on('data', c=>data+=c); process.stdin.on('end', ()=>console.log(JSON.parse(data).priv));")
  PUBLIC_KEY_B64=$(echo "$KEYS_JSON" | node -e "let data=''; process.stdin.on('data', c=>data+=c); process.stdin.on('end', ()=>console.log(JSON.parse(data).pub));")
fi
rm -rf "$TMP_DIR"

echo ""
echo "# Generated on $(date -u)"
echo "POSTGRES_PASSWORD=\"${POSTGRES_PW}\""
echo "POSTGRES_APP_PASSWORD=\"${POSTGRES_APP_PW}\""
echo "REDIS_PASSWORD=\"${REDIS_PW}\""
echo "SESSION_JWT_SECRET=\"${SESSION_SECRET}\""
echo "SERVICE_JWT_PRIVATE_KEY=\"${PRIVATE_KEY_B64}\""
echo "SERVICE_JWT_PUBLIC_KEY=\"${PUBLIC_KEY_B64}\""
echo "ENCRYPTION_KEY=\"${ENCRYPTION_SECRET}\""
echo ""
echo "================================================================="
echo "Copy these values into your .env or CI deployment secrets."
echo "================================================================="

import asyncio
import os
import time
import unittest

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate RS256 test keypair
test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PRIVATE_PEM = test_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode("utf-8")
TEST_PUBLIC_PEM = test_private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode("utf-8")

os.environ["SERVICE_JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_acceptance.db"

from fastapi import HTTPException

from app.auth import (
    DISALLOWED_DEFAULT_SECRETS,
    decode_token,
    get_service_public_key,
    verify_service_jwt,
)
from app.db.database import init_db
from app.rag import execute_rag_pipeline
from app.tools import lookup_order


class TestAcceptanceHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SERVICE_JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM
        asyncio.run(init_db())

    def setUp(self):
        os.environ["SERVICE_JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM

    def test_01_service_secret_strength_validation(self):
        """Service public key rejects known insecure default strings."""
        old_env = os.environ.get("SERVICE_JWT_PUBLIC_KEY")
        try:
            # Disallowed repo default secret
            os.environ["SERVICE_JWT_PUBLIC_KEY"] = DISALLOWED_DEFAULT_SECRETS[0]
            with self.assertRaises(RuntimeError):
                get_service_public_key()
        finally:
            os.environ["SERVICE_JWT_PUBLIC_KEY"] = old_env

    def test_02_old_default_token_rejected_with_401(self):
        """Tokens signed with old default secret string are rejected with 401."""
        old_secret = "super_secret_jwt_key_enterprise_grade_aaas_platform_2026"
        old_token = jwt.encode(
            {"workspace_id": "ws_acme_corp", "sub": "attacker", "exp": 9999999999},
            old_secret,
            algorithm="HS256"
        )
        with self.assertRaises(HTTPException) as ctx:
            decode_token(old_token)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_03_valid_service_jwt_verification(self):
        """Valid asymmetric service JWT with iss:aaas-node, aud:aaas-python, exp succeeds."""
        token = jwt.encode(
            {
                "workspace_id": "ws_acme_corp",
                "sub": "service_node_01",
                "role": "ADMIN",
                "iss": "aaas-node",
                "aud": "aaas-python",
                "exp": int(time.time()) + 3600
            },
            TEST_PRIVATE_PEM,
            algorithm="RS256"
        )
        claims = verify_service_jwt(f"Bearer {token}")
        self.assertEqual(claims["workspace_id"], "ws_acme_corp")
        self.assertEqual(claims["role"], "ADMIN")

    def test_04_service_jwt_rejects_wrong_audience_or_issuer(self):
        """Service JWT rejects invalid audience or issuer with 401."""
        token = jwt.encode(
            {
                "workspace_id": "ws_acme_corp",
                "sub": "attacker",
                "iss": "wrong-issuer",
                "aud": "wrong-audience",
                "exp": int(time.time()) + 3600
            },
            TEST_PRIVATE_PEM,
            algorithm="RS256"
        )
        with self.assertRaises(HTTPException) as ctx:
            verify_service_jwt(f"Bearer {token}")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_05_order_lookup_requires_matching_customer_email(self):
        """Order lookup requires customer email and matches case-insensitively; mismatch returns not found."""
        # 1. Matching email succeeds
        res = lookup_order("ws_acme_corp", "#10482", "sarah.connor@example.com")
        self.assertTrue(res.get("found"))
        self.assertEqual(res["order"]["order_number"], "#10482")

        # 2. Mismatched email returns not found (no enumeration)
        res_mismatch = lookup_order("ws_acme_corp", "#10482", "attacker@evil.com")
        self.assertFalse(res_mismatch.get("found"))

        # 3. Missing email returns not found
        res_missing = lookup_order("ws_acme_corp", "#10482", "")
        self.assertFalse(res_missing.get("found"))

    def test_06_empty_tenant_rag_returns_zero_citations(self):
        """Empty workspace returns 0 citations and no invented policy text."""
        res = execute_rag_pipeline(
            question="What is the store return and warranty policy?",
            workspace_id="ws_empty_tenant",
            tenant_chunks=[]
        )
        self.assertEqual(len(res["citations"]), 0)
        self.assertIn("do not have", res["natural_answer"].lower())

    def test_07_valid_tenant_rag_returns_grounded_citations(self):
        """Valid tenant chunks return grounded citations."""
        res = execute_rag_pipeline(
            question="What is your return policy?",
            workspace_id="ws_acme_corp",
            tenant_chunks=[{
                "chunk_id": "chk_01",
                "workspace_id": "ws_acme_corp",
                "doc_name": "Return Policy",
                "content": "Customers may return unworn items with tags within 30 days of delivery.",
                "embedding": [0.1] * 128
            }]
        )
        self.assertGreater(len(res["citations"]), 0)
        self.assertTrue(res["grounding_verification"]["is_grounded"])

if __name__ == "__main__":
    unittest.main()

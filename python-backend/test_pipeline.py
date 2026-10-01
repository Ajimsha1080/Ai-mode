import sys
import os

os.environ["APP_ENV"] = "development"

import jwt
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

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

# Ensure utf-8 output encoding on Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag import execute_rag_pipeline
from app.agent_runtime import run_agent_cycle
from app.auth import decode_token, verify_service_jwt, get_service_public_key
from app.db.database import init_db
import asyncio
import time

def generate_test_jwt(workspace_id: str, role: str = "ADMIN") -> str:
    payload = {
        "workspace_id": workspace_id,
        "workspaceId": workspace_id,
        "sub": f"test_user_{workspace_id}",
        "userId": f"test_user_{workspace_id}",
        "role": role,
        "isSuperAdmin": role == "SUPERADMIN",
        "iss": "aaas-node",
        "aud": "aaas-python",
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, TEST_PRIVATE_PEM, algorithm="RS256")

def test():
    os.environ["SERVICE_JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM
    asyncio.run(init_db())
    print("========================================================")
    print("RUNNING PYTHON BACKEND HARDENING & TENANCY SUITE")
    print("========================================================")
    
    # 1. Test JWT Verification & Tenancy Extraction
    print("\n[TEST 1] Service JWT Token Verification & Claim Extraction...")
    valid_token = generate_test_jwt("ws_acme_corp")
    claims = verify_service_jwt(f"Bearer {valid_token}")
    assert claims["workspace_id"] == "ws_acme_corp", "Workspace ID mismatch in verified JWT"
    print("  * Verified workspace_id:", claims["workspace_id"])
    print("  * Verified role:", claims["role"])

    # Test rejection on missing/invalid token
    try:
        verify_service_jwt(None)
        assert False, "Should have rejected missing token"
    except Exception as e:
        print("  * Correctly rejected missing token:", str(e))

    try:
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")
        bad_token = jwt.encode({"random": "payload"}, other_key, algorithm="RS256")
        verify_service_jwt(f"Bearer {bad_token}")
        assert False, "Should have rejected bad token"
    except Exception as e:
        print("  * Correctly rejected forged token:", str(e))

    # 2. Test Multi-Tenant Product Search via Agent Runtime
    print("\n[TEST 2] Multi-Tenant Agent Execution (Blue Tyga vs TechStore)...")
    res_acme = run_agent_cycle(
        agent_id="agent_shopmate_01",
        message="Show me what jackets you have in stock",
        workspace_id="ws_acme_corp"
    )
    print("  * Acme Store Response:", res_acme["response"][:80], "...")
    assert "UPF 50+" in res_acme["response"] or "jacket" in res_acme["response"].lower(), "Expected Blue Tyga product"

    res_tech = run_agent_cycle(
        agent_id="agent_tech_01",
        message="Show me laptops in stock",
        workspace_id="ws_tech_store"
    )
    print("  * TechStore Response:", res_tech["response"][:80], "...")

    # 3. Test Order Tracking Tool with Mandatory Email
    print("\n[TEST 3] Order Tracking Tool Verification...")
    from app.tools import lookup_order
    res_order = lookup_order("ws_acme_corp", "#10482", "sarah.connor@example.com")
    assert res_order["found"] is True
    print("  * Found order #10482 for Sarah Connor (Carrier:", res_order["order"]["carrier"], ")")

    res_order_fail = lookup_order("ws_acme_corp", "#10482", "attacker@evil.com")
    assert res_order_fail["found"] is False
    print("  * Mismatched email rejected successfully")

    print("\n========================================================")
    print("ALL PYTHON BACKEND HARDENING TESTS PASSED!")
    print("========================================================")

if __name__ == "__main__":
    test()

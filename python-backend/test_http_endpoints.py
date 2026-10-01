import os
import sys
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

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
os.environ["APP_ENV"] = "development"

# Add python-backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.main import app


def generate_token(workspace_id: str, role: str = "ADMIN") -> str:
    payload = {
        "workspace_id": workspace_id,
        "workspaceId": workspace_id,
        "role": role,
        "iss": "aaas-node",
        "aud": "aaas-python",
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, TEST_PRIVATE_PEM, algorithm="RS256")

def run_http_tests():
    print("=" * 65)
    print("HTTP-LEVEL FASTAPI SECURITY & MULTI-TENANCY TEST SUITE")
    print("=" * 65)

    with TestClient(app) as client:
        token_a = generate_token("ws_acme_corp", "ADMIN")
        token_b = generate_token("ws_tech_store", "ADMIN")

        # 1. Test 401 Unauthorized when no token is supplied
        endpoints_to_test = [
            ("GET", "/api/v1/db/status", None),
            ("POST", "/api/v1/agents/agent_shopmate_01/chat", {"message": "Hello"}),
            ("POST", "/api/v1/rag/query", {"question": "What is the return policy?"}),
            ("GET", "/api/v1/orders/10482?customer_email=sarah.connor@example.com", None),
        ]

        print("\n[TEST 1] Verifying 401 Unauthorized for Unauthenticated Requests...")
        for method, path, body in endpoints_to_test:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json=body)
            assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"
            print(f"  * {method} {path} -> 401 Unauthorized (PASSED)")

        # 2. Test 403 Forbidden when Token A attempts to operate on Workspace B
        print("\n[TEST 2] Verifying 403 Forbidden on Cross-Tenant Workspace Mismatch...")
        cross_tenant_chat = client.post(
            "/api/v1/agents/agent_shopmate_01/chat",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"message": "Show catalog", "workspace_id": "ws_tech_store"}
        )
        assert cross_tenant_chat.status_code == 403, f"Expected 403 Forbidden on tenant mismatch, got {cross_tenant_chat.status_code}"
        print("  * Cross-tenant chat mismatch blocked with 403 Forbidden (PASSED)")

        # 3. Test Authorized Agent Chat for Tenant A
        print("\n[TEST 3] Verifying Authorized Chat & Tool Execution...")
        auth_chat = client.post(
            "/api/v1/agents/agent_shopmate_01/chat",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"message": "Show products in store"}
        )
        assert auth_chat.status_code == 200, f"Expected 200 OK, got {auth_chat.status_code}"
        chat_data = auth_chat.json()
        assert "response" in chat_data
        assert chat_data["interactive_payload"] is not None
        print(f"  * Authorized chat execution returned HTTP 200 with {len(chat_data['interactive_payload'].get('data', []))} products (PASSED)")

        # 4. Test RAG Query Execution for Tenant A
        print("\n[TEST 4] Verifying 12-Stage RAG Execution via API...")
        rag_resp = client.post(
            "/api/v1/rag/query",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"question": "What is the return policy?", "top_k": 3}
        )
        assert rag_resp.status_code == 200, f"Expected 200 OK, got {rag_resp.status_code}"
        rag_data = rag_resp.json()
        assert "citations" in rag_data
        assert "natural_answer" in rag_data
        print(f"  * RAG query returned HTTP 200 with {len(rag_data['citations'])} citations and natural answer (PASSED)")

        print("\n" + "=" * 65)
        print("ALL HTTP SECURITY & MULTI-TENANCY TESTS PASSED SUCCESSFULLY!")
        print("=" * 65)

if __name__ == "__main__":
    run_http_tests()

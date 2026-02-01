#!/usr/bin/env python3
"""
Simple test client for the VA Decision Analysis API.

Run the API first:
    python api/main.py

Then run this script:
    python api/test_client.py
"""
import httpx
import json


BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint."""
    print("\n" + "=" * 70)
    print("TEST: Health Check")
    print("=" * 70)

    response = httpx.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_search():
    """Test search endpoint."""
    print("\n" + "=" * 70)
    print("TEST: Search BVA Decisions")
    print("=" * 70)

    payload = {
        "query": "tinnitus granted",
        "year": 2024,
        "max_results": 3
    }

    response = httpx.post(f"{BASE_URL}/api/v1/search", json=payload, timeout=30)
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nFound {data['count']} results:")
    for result in data["results"]:
        print(f"  - {result['case_number']} ({result['year']})")
        print(f"    URL: {result['url']}")


def test_fetch_decision():
    """Test fetch decision endpoint."""
    print("\n" + "=" * 70)
    print("TEST: Fetch Specific Decision")
    print("=" * 70)

    case_number = "A24084938"
    year = 2024

    response = httpx.get(
        f"{BASE_URL}/api/v1/decision/{case_number}",
        params={"year": year},
        timeout=30
    )
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nCase Number: {data['case_number']}")
    print(f"Year: {data['year']}")
    print(f"Text Length: {data['text_length']} chars")
    print(f"Parsed Outcome: {data['parsed']['outcome']}")
    print(f"Issues: {len(data['parsed']['issues'])}")


def test_similar_cases():
    """Test similar cases query."""
    print("\n" + "=" * 70)
    print("TEST: Query Similar Cases")
    print("=" * 70)

    payload = {
        "query_text": "tinnitus noise exposure",
        "limit": 5,
        "outcome_filter": "Granted"
    }

    response = httpx.post(
        f"{BASE_URL}/api/v1/query/similar",
        json=payload,
        timeout=30
    )
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nFound {data['count']} similar cases:")
    for case in data["results"][:3]:
        print(f"  - {case['decision_id']}: {case['outcome']} ({case['condition']})")


def test_evidence_chain():
    """Test evidence chain query."""
    print("\n" + "=" * 70)
    print("TEST: Query Evidence Chain")
    print("=" * 70)

    issue_id = 1

    response = httpx.get(
        f"{BASE_URL}/api/v1/query/evidence-chain/{issue_id}",
        timeout=30
    )
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nIssue ID: {data['issue_id']}")
    print(f"Condition: {data['condition']}")
    print(f"Outcome: {data['outcome']}")
    print(f"Evidence Types: {data['evidence_types']}")
    print(f"Provider Types: {data['provider_types']}")
    print(f"Authorities: {data['authorities'][:3]}")


def test_evidence_diff():
    """Test evidence diff query."""
    print("\n" + "=" * 70)
    print("TEST: Query Evidence Diff")
    print("=" * 70)

    response = httpx.get(
        f"{BASE_URL}/api/v1/query/evidence-diff",
        params={"condition": "tinnitus"},
        timeout=30
    )
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nFound {data['count']} evidence/outcome combinations:")
    for item in data["results"][:5]:
        print(f"  - {item['evidence_type']}: {item['outcome']} ({item['count']})")


def test_authority_stats():
    """Test authority stats query."""
    print("\n" + "=" * 70)
    print("TEST: Query Authority Stats")
    print("=" * 70)

    response = httpx.get(
        f"{BASE_URL}/api/v1/query/authority-stats",
        params={"condition": "tinnitus"},
        timeout=30
    )
    print(f"Status: {response.status_code}")

    data = response.json()
    print(f"\nFound {data['count']} authority/outcome combinations:")
    for item in data["results"][:5]:
        print(f"  - {item['citation']}: {item['outcome']} ({item['count']})")


def run_all_tests():
    """Run all tests."""
    try:
        test_health()
        test_search()
        test_fetch_decision()
        test_similar_cases()
        test_evidence_chain()
        test_evidence_diff()
        test_authority_stats()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except httpx.ConnectError:
        print("\n❌ Connection Error: Is the API running?")
        print("Start it with: python api/main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    run_all_tests()

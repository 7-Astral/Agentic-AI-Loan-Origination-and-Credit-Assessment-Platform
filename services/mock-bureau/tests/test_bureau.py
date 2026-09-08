from fastapi.testclient import TestClient

from core.config import settings
from main import app


def _get_token(client: TestClient) -> str:
    response = client.post(
        "/oauth2/v1/token",
        json={
            "client_id": settings.mock_bureau_client_id,
            "client_secret": settings.mock_bureau_client_secret,
            "grant_type": "client_credentials",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_token_issued_for_valid_client_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/oauth2/v1/token",
            json={
                "client_id": settings.mock_bureau_client_id,
                "client_secret": settings.mock_bureau_client_secret,
                "grant_type": "client_credentials",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_token_rejected_for_invalid_client_credentials() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/oauth2/v1/token",
            json={"client_id": "wrong", "client_secret": "wrong", "grant_type": "client_credentials"},
        )
    assert response.status_code == 401


def test_credit_report_rejects_missing_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/credit-report/v1",
            json={"name": "Daniel Osei", "dob": "1990-07-22", "address": "x"},
        )
    assert response.status_code == 401


def test_credit_report_rejects_invalid_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/credit-report/v1",
            json={"name": "Daniel Osei", "dob": "1990-07-22", "address": "x"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    assert response.status_code == 401


def test_credit_report_matches_known_identity() -> None:
    with TestClient(app) as client:
        token = _get_token(client)
        response = client.post(
            "/credit-report/v1",
            json={
                "name": "Daniel Osei",
                "dob": "1990-07-22",
                "address": "45 Banksia Avenue, Marrickville NSW 2204",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["score"] == 742
    assert body["band"] == "good"


def test_credit_report_no_match_returns_200_not_matched() -> None:
    with TestClient(app) as client:
        token = _get_token(client)
        response = client.post(
            "/credit-report/v1",
            json={"name": "Nobody Real", "dob": "2000-01-01", "address": "nowhere"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.json() == {"matched": False}

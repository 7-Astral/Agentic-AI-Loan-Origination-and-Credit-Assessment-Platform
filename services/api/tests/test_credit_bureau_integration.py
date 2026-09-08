import httpx

from integration.credit_bureau import get_credit_report


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://mock-bureau.test", transport=httpx.MockTransport(handler)
    )


async def test_matched_identity_returns_score_and_band() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/v1/token":
            return httpx.Response(
                200, json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}
            )
        return httpx.Response(
            200,
            json={
                "matched": True,
                "score": 742,
                "band": "good",
                "report_summary": {"enquiries_last_6_months": 2, "adverse_events": 0},
            },
        )

    result = await get_credit_report(
        "Daniel Osei", "1990-07-22", "45 Banksia Ave", client=_client(handler)
    )
    assert result.matched is True
    assert result.score == 742
    assert result.band == "good"
    assert result.error is None


async def test_no_match_returns_matched_false_not_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/v1/token":
            return httpx.Response(
                200, json={"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}
            )
        return httpx.Response(200, json={"matched": False})

    result = await get_credit_report(
        "Nobody Real", "2000-01-01", "nowhere", client=_client(handler)
    )
    assert result.matched is False
    assert result.score is None
    assert result.error is None


async def test_timeout_degrades_to_error_not_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    result = await get_credit_report(
        "Daniel Osei", "1990-07-22", "45 Banksia Ave", client=_client(handler)
    )
    assert result.matched is None
    assert result.error == "timeout"


async def test_connection_error_degrades_to_error_not_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    result = await get_credit_report(
        "Daniel Osei", "1990-07-22", "45 Banksia Ave", client=_client(handler)
    )
    assert result.matched is None
    assert result.error == "request_failed"


async def test_auth_failure_degrades_to_error_not_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/v1/token":
            return httpx.Response(401, json={"detail": "invalid_client"})
        raise AssertionError("should not reach credit-report endpoint without a token")

    result = await get_credit_report(
        "Daniel Osei", "1990-07-22", "45 Banksia Ave", client=_client(handler)
    )
    assert result.matched is None
    assert result.error == "auth_failed"

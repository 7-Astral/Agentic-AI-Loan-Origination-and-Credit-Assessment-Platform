from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio

from core.config import settings
from integration.abr import lookup_abn


@pytest_asyncio.fixture(autouse=True)
async def _with_guid() -> AsyncGenerator[None, None]:
    """Most of this module's tests need ABR_GUID set to exercise the lookup path; the
    no-GUID-configured test overrides it back to None for that one case."""
    original = settings.abr_guid
    settings.abr_guid = "test-guid"
    yield
    settings.abr_guid = original


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_no_guid_configured_degrades_to_unavailable() -> None:
    settings.abr_guid = None
    result = await lookup_abn("51824753556")
    assert result.found is None
    assert result.error == "no_guid"


async def test_jsonp_response_is_unwrapped_and_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = (
            'callback({"Abn":"51824753556","AbnStatus":"Active",'
            '"EntityName":"Example Pty Ltd","EntityTypeName":"Australian Private Company",'
            '"Gst":[{"Effective":"2010-01-01"}],"AddressState":"NSW"})'
        )
        return httpx.Response(200, text=body, headers={"content-type": "application/javascript"})

    result = await lookup_abn("51824753556", client=_client(handler))
    assert result.found is True
    assert result.entity_name == "Example Pty Ltd"
    assert result.abn_status == "Active"
    assert result.entity_type == "Australian Private Company"
    assert result.gst_registered is True
    assert result.address_state == "NSW"


async def test_invalid_abn_returns_200_with_exception_message_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = (
            'callback({"Exception":"The ABN provided (12345) is not in a valid format","Abn":null})'
        )
        return httpx.Response(200, text=body)

    result = await lookup_abn("12345", client=_client(handler))
    assert result.found is False
    assert result.error is None


async def test_unknown_abn_no_record_returns_found_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = 'callback({"Message":"No record found","Abn":null})'
        return httpx.Response(200, text=body)

    result = await lookup_abn("99999999999", client=_client(handler))
    assert result.found is False


async def test_timeout_degrades_to_unavailable_not_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    result = await lookup_abn("51824753556", client=_client(handler))
    assert result.found is None
    assert result.error == "timeout"


async def test_no_gst_registration_reflects_empty_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = (
            'callback({"Abn":"51824753556","AbnStatus":"Cancelled",'
            '"EntityName":"Example Pty Ltd","EntityTypeName":"Australian Private Company",'
            '"Gst":[],"AddressState":"VIC"})'
        )
        return httpx.Response(200, text=body)

    result = await lookup_abn("51824753556", client=_client(handler))
    assert result.found is True
    assert result.abn_status == "Cancelled"
    assert result.gst_registered is False

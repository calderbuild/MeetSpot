"""The page 302.AI sends the buyer back to after checkout."""

from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)


def _redirect(query: str):
    response = client.get(f"/api/payment/success?{query}", follow_redirects=False)
    assert response.status_code in (302, 307)
    return urlsplit(response.headers["location"])


def test_checkout_id_is_passed_on_to_the_finder():
    target = _redirect("checkout_id=chk_123")
    assert target.path == "/public/meetspot_finder.html"
    assert parse_qs(target.query) == {"payment": ["success"], "checkout_id": ["chk_123"]}


def test_checkout_id_cannot_add_parameters_or_a_fragment():
    """The id is copied from the query string; unencoded, "&" and "#" in it became
    extra parameters and a fragment of the finder URL."""
    target = _redirect("checkout_id=abc%26lang%3Den%26payment%3Dfailed%23frag")
    assert target.fragment == ""
    assert parse_qs(target.query) == {
        "payment": ["success"],
        "checkout_id": ["abc&lang=en&payment=failed#frag"],
    }

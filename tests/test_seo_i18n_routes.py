import re

from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)
BASE = "https://meetspot-irq2.onrender.com"
HTML = {"accept": "text/html"}


def _canonical(html):
    return re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)


def test_zh_homepage_is_its_own_canonical_and_hreflang_target():
    html = client.get("/zh/").text
    assert _canonical(html) == f"{BASE}/zh/"
    assert f'hreflang="zh" href="{BASE}/zh/"' in html
    # x-default must be a canonical URL; / canonicalizes to /en/
    assert f'hreflang="x-default" href="{BASE}/en/"' in html


def test_sitemap_lists_zh_homepage_not_bare_root_as_zh():
    xml = client.get("/sitemap.xml").text
    assert f"<loc>{BASE}/zh/</loc>" in xml
    assert f'hreflang="zh" href="{BASE}/"' not in xml
    assert "meetspot_finder.html?lang=en" not in xml


def test_english_city_page_has_english_title():
    title = re.search(r"<title>([^<]*)", client.get("/en/meetspot/beijing").text).group(
        1
    )
    assert "聚会" not in title and "Beijing" in title


def test_language_switch_from_zh_home_points_to_existing_route():
    html = client.get("/zh/").text
    href = re.search(r'href="([^"]+)"\s+class="lang-switch"', html).group(1)
    assert href == "/en/"
    assert client.get(href).status_code == 200


def test_404_is_html_for_browsers_and_json_for_api():
    page = client.get("/no-such-page", headers=HTML)
    assert page.status_code == 404 and "text/html" in page.headers["content-type"]
    api = client.get("/api/no-such-endpoint", headers=HTML)
    assert api.status_code == 404 and api.json() == {"detail": "Not Found"}

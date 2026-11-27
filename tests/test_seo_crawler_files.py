"""robots.txt and llms.txt as crawlers read them."""

import re
from urllib.robotparser import RobotFileParser

import pytest
from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)
BASE = "https://meetspot-irq2.onrender.com"


def _robots() -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(client.get("/robots.txt").text.splitlines())
    return parser


@pytest.mark.parametrize(
    "bot",
    [
        "Googlebot",
        "Baiduspider",
        "GPTBot",
        "ChatGPT-User",
        "PerplexityBot",
        "ClaudeBot",
        "Google-Extended",
        "SomeOtherBot",
    ],
)
def test_search_and_ai_bots_may_read_pages_but_not_the_api(bot):
    """A crawler obeys only the most specific group naming it, so a bare
    "Allow: /" group for a bot cancels the Disallow rules of the * group."""
    robots = _robots()
    assert robots.can_fetch(bot, f"{BASE}/")
    assert robots.can_fetch(bot, f"{BASE}/meetspot/beijing")
    assert not robots.can_fetch(bot, f"{BASE}/api/find_meetspot")
    assert not robots.can_fetch(bot, f"{BASE}/admin/")


def test_training_only_crawler_stays_blocked():
    assert not _robots().can_fetch("CCBot", f"{BASE}/")


def test_robots_still_points_at_the_sitemap():
    assert f"Sitemap: {BASE}/sitemap.xml" in client.get("/robots.txt").text


def test_llms_txt_links_put_the_url_in_the_parentheses():
    """llms.txt links are Markdown: [title](url)."""
    text = client.get("/llms.txt").text
    links = re.findall(r"^- \[([^\]]+)\]\(([^)]+)\)", text, flags=re.M)
    assert len(links) == 6
    for title, url in links:
        assert url.startswith(f"{BASE}/"), (title, url)
        assert not title.startswith("http"), title
        path = url[len(BASE):]
        assert client.get(path).status_code == 200, path

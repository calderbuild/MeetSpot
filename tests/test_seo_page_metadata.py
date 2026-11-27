"""Meta tags and structured data of the server-rendered pages."""

import json
import re

import pytest
from fastapi.testclient import TestClient

from api.index import app
from api.services.seo_content import clip_meta
from app.i18n import get_translations

client = TestClient(app)


def _description(path: str) -> str:
    html = client.get(path).text
    return re.search(r'<meta name="description" content="([^"]*)"', html).group(1)


def _json_ld(path: str) -> list:
    html = client.get(path).text
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S
    )
    items = []
    for block in blocks:
        data = json.loads(block)
        items.extend(data if isinstance(data, list) else [data])
    return items


def test_clip_meta_leaves_short_text_alone():
    assert clip_meta("Frequently asked questions", 155) == "Frequently asked questions"


def test_clip_meta_does_not_cut_a_word_in_half():
    text = "Spherical geometry for fair midpoint calculation in 350+ cities"
    clipped = clip_meta(text, 30)
    assert clipped == "Spherical geometry for fair…"
    assert len(clipped) <= 30


def test_clip_meta_keeps_the_last_whole_word_when_the_cut_falls_on_a_space():
    assert clip_meta("one two three four", 8) == "one two…"


def test_clip_meta_cuts_text_without_spaces_by_length():
    text = "球面几何算法计算公平中心" * 20
    clipped = clip_meta(text, 155)
    assert len(clipped) == 155 and clipped.endswith("…")


@pytest.mark.parametrize(
    "path,key",
    [
        ("/en/", "seo.home.description"),
        ("/en/about", "seo.about.description"),
        ("/en/compare", "compare.seo_desc"),
    ],
)
def test_long_english_descriptions_end_on_a_whole_word(path, key):
    """These three descriptions are longer than 155 characters."""
    full = get_translations("en")[key]
    assert len(full) > 155
    description = _description(path)
    assert len(description) <= 155 and description.endswith("…")
    shown = description[:-1]
    assert full.startswith(shown)
    assert full[len(shown)] in " ,.;:"


@pytest.mark.parametrize(
    "path,language", [("/how-it-works", "zh-CN"), ("/en/how-it-works", "en")]
)
def test_how_to_structured_data_names_the_page_language(path, language):
    how_to = [item for item in _json_ld(path) if item.get("@type") == "HowTo"]
    assert len(how_to) == 1
    assert how_to[0]["inLanguage"] == language


@pytest.mark.parametrize(
    "path,lang", [("/meetspot/beijing", "zh"), ("/en/meetspot/beijing", "en")]
)
def test_city_page_opens_the_finder_in_the_page_language(path, lang):
    html = client.get(path).text
    links = re.findall(r'href="(/public/meetspot_finder\.html[^"]*)"', html)
    assert links
    assert all(link.endswith(f"?lang={lang}") for link in links), links

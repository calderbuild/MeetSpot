import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import yaml


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "postmortem_check.py"
SPEC = spec_from_file_location("postmortem_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
postmortem_check = module_from_spec(SPEC)
SPEC.loader.exec_module(postmortem_check)


def build_match(
    pm_id: str,
    kind: str,
    reason: str,
    confidence: float,
    is_specific: bool = False,
):
    return postmortem_check.MatchResult(
        pm_id=pm_id,
        kind=kind,
        reason=reason,
        confidence=confidence,
        is_specific=is_specific,
    )


def test_extract_changed_lines_ignores_headers_and_context():
    diff = """diff --git a/api/index.py b/api/index.py
index 1234567..89abcde 100644
--- a/api/index.py
+++ b/api/index.py
@@ -10,2 +10,2 @@ def sitemap():
 context line that should be ignored
-old robots line
+new robots line
 another context line
"""

    changed = postmortem_check.extract_changed_lines(diff)

    assert changed == "old robots line\nnew robots line"


def test_extract_changed_lines_by_file_keeps_files_separate():
    diff = """diff --git a/api/index.py b/api/index.py
--- a/api/index.py
+++ b/api/index.py
@@ -1 +1 @@
-old cache header
+new cache header
diff --git a/templates/pages/home.html b/templates/pages/home.html
--- a/templates/pages/home.html
+++ b/templates/pages/home.html
@@ -1 +1 @@
-old hero
+new hero
"""

    changed = postmortem_check.extract_changed_lines_by_file(diff)

    assert changed == {
        "api/index.py": "old cache header\nnew cache header",
        "templates/pages/home.html": "old hero\nnew hero",
    }


def test_file_only_match_stays_below_block_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()

    aggregated = matcher.aggregate_matches(
        [
            build_match(
                "PM-1",
                "file",
                "File: api/index.py ~ api/index.py",
                postmortem_check.PostmortemMatcher.WEIGHT_FILE_EXACT,
                True,
            )
        ],
        [],
    )

    assert aggregated["PM-1"].final_confidence < 0.7


def test_file_and_pattern_match_stays_blocking(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()

    aggregated = matcher.aggregate_matches(
        [
            build_match(
                "PM-1",
                "file",
                "File: api/index.py ~ api/index.py",
                postmortem_check.PostmortemMatcher.WEIGHT_FILE_EXACT,
                True,
            )
        ],
        [
            build_match(
                "PM-1",
                "pattern",
                "Pattern: @app.api_route",
                postmortem_check.PostmortemMatcher.WEIGHT_PATTERN_STRONG,
                True,
            )
        ],
    )

    assert aggregated["PM-1"].final_confidence >= 0.7


def test_content_matching_only_uses_related_files(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()
    matcher.postmortems = [
        {
            "id": "PM-1",
            "triggers": {
                "files": ["api/index.py"],
                "patterns": ["Cache-Control"],
            },
        }
    ]

    matches = matcher.match_diff_content(
        {
            "api/index.py": "no matching content here",
            "templates/pages/home.html": "Cache-Control appears in another file",
        }
    )

    assert matches == []


def test_pattern_specificity_distinguishes_broad_regex_from_precise_route(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()

    assert matcher._is_specific_pattern(".*sitemap.*") is False
    assert matcher._is_specific_pattern("Cache-Control") is False
    assert matcher._is_specific_pattern('@router.api_route\\(.*methods=\\[.*HEAD.*\\]\\)') is True


def test_keyword_specificity_downgrades_generic_terms(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()

    assert matcher._is_specific_keyword("cache") is False
    assert matcher._is_specific_keyword("payment") is False
    assert matcher._is_specific_keyword("robots.txt") is True


def test_generic_pattern_and_keywords_do_not_block_hot_function_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    matcher = postmortem_check.PostmortemMatcher()

    aggregated = matcher.aggregate_matches(
        [
            build_match(
                "PM-1",
                "file",
                "File: api/routers/seo_pages.py ~ api/routers/seo_pages.py",
                postmortem_check.PostmortemMatcher.WEIGHT_FILE_EXACT,
                True,
            )
        ],
        [
            build_match(
                "PM-1",
                "function",
                "Function: sitemap",
                postmortem_check.PostmortemMatcher.WEIGHT_FUNCTION,
                False,
            ),
            build_match(
                "PM-1",
                "pattern",
                "Pattern: .*sitemap.*",
                postmortem_check.PostmortemMatcher.WEIGHT_PATTERN_GENERIC,
                False,
            ),
            build_match(
                "PM-1",
                "keyword",
                "Keyword: robots.txt",
                postmortem_check.PostmortemMatcher.WEIGHT_KEYWORD_STRONG,
                True,
            ),
        ],
    )

    assert aggregated["PM-1"].final_confidence < 0.7


def test_json_output_is_machine_readable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(postmortem_check, "POSTMORTEM_DIR", tmp_path)
    (tmp_path / "PM-1.yaml").write_text(
        """
id: PM-1
title: Example PM
severity: high
triggers:
  files:
    - api/index.py
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(postmortem_check, "get_changed_files", lambda base_ref: ["api/index.py"])
    monkeypatch.setattr(postmortem_check, "get_diff_content", lambda base_ref: "")
    monkeypatch.setattr(
        postmortem_check,
        "extract_changed_lines_by_file",
        lambda diff: {},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["postmortem_check.py", "--base", "main", "--output", "json"],
    )

    try:
        postmortem_check.main()
    except SystemExit as exc:
        assert exc.code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"] == {"blocking": 0, "warnings": 1}
    assert payload["results"][0]["id"] == "PM-1"


def test_high_confidence_without_specific_pattern_is_only_warn():
    agg = postmortem_check.AggregatedMatch(pm_id="PM-1")
    agg.final_confidence = 0.95
    agg.has_specific_pattern_match = False

    assert postmortem_check.classify_match_level(agg, 0.7) == "WARN"


def test_workflow_triggers_on_self_edits_and_manual_dispatch():
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "postmortem-check.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_on = workflow.get("on", workflow.get(True))

    assert "workflow_dispatch" in workflow_on
    assert ".github/workflows/postmortem-check.yml" in workflow_on["push"]["paths"]
    assert ".github/workflows/postmortem-check.yml" in workflow_on["pull_request"]["paths"]

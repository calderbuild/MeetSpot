from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "postmortem_check.py"
SPEC = spec_from_file_location("postmortem_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
postmortem_check = module_from_spec(SPEC)
SPEC.loader.exec_module(postmortem_check)


def build_match(pm_id: str, kind: str, reason: str, confidence: float):
    return postmortem_check.MatchResult(
        pm_id=pm_id,
        kind=kind,
        reason=reason,
        confidence=confidence,
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
            )
        ],
        [
            build_match(
                "PM-1",
                "pattern",
                "Pattern: @app.api_route",
                postmortem_check.PostmortemMatcher.WEIGHT_PATTERN,
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

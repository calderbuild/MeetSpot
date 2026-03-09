#!/usr/bin/env python3
"""
Postmortem 匹配检查脚本
检查当前变更是否触发历史 postmortem

使用方法:
    python tools/postmortem_check.py [--base main] [--mode warn|block]

返回码:
    0 - 无匹配或仅警告
    1 - 发现高置信度匹配（blocking mode）
    2 - 错误
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

POSTMORTEM_DIR = Path(__file__).parent.parent / "postmortem"
GENERIC_KEYWORDS = {
    "cache",
    "cache-control",
    "ci",
    "db",
    "faq",
    "finder",
    "fix",
    "general",
    "html",
    "label",
    "map",
    "payment",
}


@dataclass
class MatchResult:
    """单个匹配结果"""

    pm_id: str
    kind: str
    reason: str
    confidence: float
    is_specific: bool = False


@dataclass
class AggregatedMatch:
    """聚合后的匹配结果"""

    pm_id: str
    reasons: List[str] = field(default_factory=list)
    match_count: int = 0
    final_confidence: float = 0.0
    exact_file_matches: int = 0
    pattern_file_matches: int = 0
    function_match_count: int = 0
    specific_pattern_count: int = 0
    generic_pattern_count: int = 0
    specific_keyword_count: int = 0
    generic_keyword_count: int = 0
    has_file_match: bool = False
    has_specific_pattern_match: bool = False
    has_specific_keyword_match: bool = False


class PostmortemMatcher:
    """Postmortem 匹配器"""

    # 匹配权重
    WEIGHT_FILE_EXACT = 0.20
    WEIGHT_FILE_PATTERN = 0.15
    WEIGHT_FUNCTION = 0.20
    WEIGHT_PATTERN_STRONG = 0.40
    WEIGHT_PATTERN_GENERIC = 0.12
    WEIGHT_KEYWORD_STRONG = 0.12
    WEIGHT_KEYWORD_GENERIC = 0.05

    def __init__(self):
        self.postmortems = self._load_all_postmortems()

    def _load_all_postmortems(self) -> List[Dict]:
        """加载所有 postmortem 文件"""
        pms = []
        if not POSTMORTEM_DIR.exists():
            return pms

        for f in POSTMORTEM_DIR.glob("PM-*.yaml"):
            try:
                with open(f, encoding="utf-8") as fp:
                    pm = yaml.safe_load(fp)
                    if pm:
                        pms.append(pm)
            except Exception as e:
                print(f"Warning: Failed to load {f}: {e}", file=sys.stderr)

        return pms

    def match_files(self, changed_files: List[str]) -> List[MatchResult]:
        """匹配修改的文件"""
        matches = []

        for pm in self.postmortems:
            triggers = pm.get("triggers", {})
            pm_files = triggers.get("files", [])
            pm_id = pm.get("id", "unknown")

            for changed in changed_files:
                for pattern in pm_files:
                    if self._file_matches(changed, pattern):
                        # 精确匹配 vs 模式匹配
                        is_exact = "*" not in pattern and "?" not in pattern
                        confidence = (
                            self.WEIGHT_FILE_EXACT if is_exact else self.WEIGHT_FILE_PATTERN
                        )
                        matches.append(
                            MatchResult(
                                pm_id=pm_id,
                                kind="file",
                                reason=f"File: {changed} ~ {pattern}",
                                confidence=confidence,
                                is_specific=is_exact,
                            )
                        )

        return matches

    def match_diff_content(self, diff_by_file: Dict[str, str]) -> List[MatchResult]:
        """匹配 diff 内容中的函数名和模式"""
        matches = []

        for pm in self.postmortems:
            triggers = pm.get("triggers", {})
            pm_id = pm.get("id", "unknown")
            pm_files = triggers.get("files", [])
            relevant_diff_parts = []

            for filepath, changed_text in diff_by_file.items():
                if not pm_files or any(self._file_matches(filepath, pattern) for pattern in pm_files):
                    relevant_diff_parts.append(changed_text)

            diff = "\n".join(part for part in relevant_diff_parts if part)
            if not diff:
                continue

            # 函数名匹配
            for func in triggers.get("functions", []):
                if not func:
                    continue
                try:
                    if re.search(rf"\b{re.escape(func)}\b", diff):
                        matches.append(
                            MatchResult(
                                pm_id=pm_id,
                                kind="function",
                                reason=f"Function: {func}",
                                confidence=self.WEIGHT_FUNCTION,
                                is_specific=False,
                            )
                        )
                except re.error:
                    continue

            # 正则模式匹配
            for pattern in triggers.get("patterns", []):
                if not pattern:
                    continue
                try:
                    if re.search(pattern, diff, re.IGNORECASE):
                        is_specific = self._is_specific_pattern(pattern)
                        matches.append(
                            MatchResult(
                                pm_id=pm_id,
                                kind="pattern",
                                reason=f"Pattern: {pattern}",
                                confidence=(
                                    self.WEIGHT_PATTERN_STRONG
                                    if is_specific
                                    else self.WEIGHT_PATTERN_GENERIC
                                ),
                                is_specific=is_specific,
                            )
                        )
                except re.error:
                    continue

            # 关键词匹配
            for keyword in triggers.get("keywords", []):
                if not keyword:
                    continue
                if keyword.lower() in diff.lower():
                    is_specific = self._is_specific_keyword(keyword)
                    matches.append(
                        MatchResult(
                            pm_id=pm_id,
                            kind="keyword",
                            reason=f"Keyword: {keyword}",
                            confidence=(
                                self.WEIGHT_KEYWORD_STRONG
                                if is_specific
                                else self.WEIGHT_KEYWORD_GENERIC
                            ),
                            is_specific=is_specific,
                        )
                    )

        return matches

    def _file_matches(self, filepath: str, pattern: str) -> bool:
        """检查文件路径是否匹配模式"""
        # 支持 glob 模式
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # 也尝试匹配文件名部分
        if fnmatch.fnmatch(Path(filepath).name, pattern):
            return True
        # 检查是否包含（用于简单的路径匹配）
        if "*" not in pattern and "?" not in pattern:
            return pattern in filepath
        return False

    def _is_specific_pattern(self, pattern: str) -> bool:
        """区分精确风险模式和泛化关键词式模式。"""
        stripped = pattern.strip()
        if not stripped:
            return False

        wildcard_like = stripped.replace(r"\.", ".").replace(r"\-", "-")
        if re.fullmatch(r"\.\*[A-Za-z0-9_./:\-\s]+(?:\\\.[A-Za-z0-9_./:\-\s]+)*\.\*", stripped):
            return False
        if re.fullmatch(r"[A-Za-z0-9_./:\-\s]+", wildcard_like):
            return len(wildcard_like) >= 20 or "@" in wildcard_like or "(" in stripped
        if stripped.count(".*") >= 1 and not any(
            token in stripped for token in ["^", "$", "\\(", "\\)", "[", "]", "{", "}", '="', "methods="]
        ):
            return False
        return True

    def _is_specific_keyword(self, keyword: str) -> bool:
        normalized = keyword.strip().lower()
        if not normalized:
            return False
        if normalized in GENERIC_KEYWORDS:
            return False
        if len(normalized) <= 4:
            return False
        if " " not in normalized and normalized.isalpha() and len(normalized) <= 8:
            return False
        return True

    def aggregate_matches(
        self, file_matches: List[MatchResult], content_matches: List[MatchResult]
    ) -> Dict[str, AggregatedMatch]:
        """聚合匹配结果，计算综合置信度"""
        result: Dict[str, AggregatedMatch] = {}

        all_matches = file_matches + content_matches
        for match in all_matches:
            if match.pm_id not in result:
                result[match.pm_id] = AggregatedMatch(pm_id=match.pm_id)

            agg = result[match.pm_id]
            agg.reasons.append(match.reason)
            agg.match_count += 1

            if match.kind == "file":
                agg.has_file_match = True
                if match.is_specific:
                    agg.exact_file_matches += 1
                else:
                    agg.pattern_file_matches += 1
            if match.kind == "function":
                agg.function_match_count += 1
            if match.kind == "pattern":
                if match.is_specific:
                    agg.specific_pattern_count += 1
                    agg.has_specific_pattern_match = True
                else:
                    agg.generic_pattern_count += 1
            if match.kind == "keyword":
                if match.is_specific:
                    agg.specific_keyword_count += 1
                    agg.has_specific_keyword_match = True
                else:
                    agg.generic_keyword_count += 1

        # 计算综合置信度
        for pm_id, agg in result.items():
            file_score = min(
                0.25,
                agg.exact_file_matches * self.WEIGHT_FILE_EXACT
                + agg.pattern_file_matches * self.WEIGHT_FILE_PATTERN,
            )
            function_score = min(0.25, agg.function_match_count * self.WEIGHT_FUNCTION)
            pattern_score = min(
                0.50,
                agg.specific_pattern_count * self.WEIGHT_PATTERN_STRONG
                + agg.generic_pattern_count * self.WEIGHT_PATTERN_GENERIC,
            )
            keyword_score = min(
                0.18,
                agg.specific_keyword_count * self.WEIGHT_KEYWORD_STRONG
                + agg.generic_keyword_count * self.WEIGHT_KEYWORD_GENERIC,
            )

            cross_bonus = 0.0
            if agg.has_file_match and agg.has_specific_pattern_match:
                cross_bonus += 0.10
            if agg.function_match_count and agg.has_specific_pattern_match:
                cross_bonus += 0.05
            if agg.function_match_count and agg.specific_keyword_count >= 2:
                cross_bonus += 0.05

            agg.final_confidence = min(
                1.0, file_score + function_score + pattern_score + keyword_score + cross_bonus
            )

        return result

    def get_postmortem_details(self, pm_id: str) -> Optional[Dict]:
        """获取 postmortem 详情"""
        for pm in self.postmortems:
            if pm.get("id") == pm_id:
                return pm
        return None


def get_changed_files(base_ref: str) -> List[str]:
    """获取相对于 base 的变更文件"""
    cwd = POSTMORTEM_DIR.parent

    # 尝试不同的 diff 方式
    # 1. 三点 diff（用于 PR）
    cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        # 2. 两点 diff
        cmd = ["git", "diff", "--name-only", f"{base_ref}..HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        # 3. 直接对比
        cmd = ["git", "diff", "--name-only", base_ref]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    return [f for f in result.stdout.strip().split("\n") if f]


def get_diff_content(base_ref: str) -> str:
    """获取相对于 base 的 diff 内容"""
    cwd = POSTMORTEM_DIR.parent

    # 只看代码文件的 diff
    extensions = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]
    cmd = ["git", "diff", "--unified=0", f"{base_ref}...HEAD", "--"] + extensions
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        cmd = ["git", "diff", "--unified=0", f"{base_ref}..HEAD", "--"] + extensions
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        cmd = ["git", "diff", "--unified=0", base_ref, "--"] + extensions
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    return result.stdout


def extract_changed_lines(diff: str) -> str:
    """只保留真正变更的行，避免 diff 上下文导致误报"""
    return "\n".join(extract_changed_lines_by_file(diff).values())


def extract_changed_lines_by_file(diff: str) -> Dict[str, str]:
    """按文件提取真正变更的行，避免跨文件拼接造成误报"""
    changed_by_file: Dict[str, List[str]] = {}
    current_file: Optional[str] = None

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3][2:] if parts[3].startswith("b/") else parts[3]
                changed_by_file.setdefault(current_file, [])
            else:
                current_file = None
            continue
        if line.startswith(("+++", "---", "@@")):
            continue
        if current_file and line.startswith(("+", "-")):
            changed_by_file[current_file].append(line[1:])

    return {
        filepath: "\n".join(lines)
        for filepath, lines in changed_by_file.items()
        if lines
    }


def classify_match_level(agg: AggregatedMatch, threshold: float) -> str:
    """只有命中高特异性模式时，才允许升级为 BLOCK。"""
    if agg.final_confidence >= threshold and agg.has_specific_pattern_match:
        return "BLOCK"
    return "WARN"


def main():
    parser = argparse.ArgumentParser(description="Postmortem Check")
    parser.add_argument("--base", default="main", help="Base branch/commit")
    parser.add_argument(
        "--mode",
        choices=["warn", "block"],
        default="warn",
        help="warn: only print, block: exit 1 on high confidence",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Confidence threshold for blocking (default: 0.7)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    if not POSTMORTEM_DIR.exists():
        print("No postmortem directory found. Run postmortem_init.py first.")
        sys.exit(0)

    matcher = PostmortemMatcher()

    if not matcher.postmortems:
        print("No postmortems found.")
        sys.exit(0)

    # 获取变更
    changed_files = get_changed_files(args.base)
    diff_content_by_file = extract_changed_lines_by_file(get_diff_content(args.base))

    if not changed_files:
        print("No changes detected.")
        sys.exit(0)

    if args.output == "text":
        print(
            f"Checking {len(changed_files)} changed files against {len(matcher.postmortems)} postmortems..."
        )

    # 执行匹配
    file_matches = matcher.match_files(changed_files)
    content_matches = matcher.match_diff_content(diff_content_by_file)

    # 聚合结果
    results = matcher.aggregate_matches(file_matches, content_matches)

    if not results:
        print("No postmortem matches found.")
        sys.exit(0)

    # 输出结果
    blocking = []
    warnings = []
    output_items = []

    sorted_results = sorted(
        results.items(), key=lambda x: x[1].final_confidence, reverse=True
    )

    for pm_id, agg in sorted_results:
        confidence = agg.final_confidence
        level = classify_match_level(agg, args.threshold)
        is_blocking = level == "BLOCK"

        # 获取 postmortem 详情
        pm = matcher.get_postmortem_details(pm_id)
        if not pm:
            pm = {"title": "Unknown", "severity": "unknown"}

        if args.output == "text":
            print(f"\n[{level}] {pm_id} ({confidence:.0%} confidence)")
            print(f"  Title: {pm.get('title', 'N/A')}")
            print(f"  Severity: {pm.get('severity', 'N/A')}")
            print(f"  Reasons:")
            for reason in agg.reasons[:5]:  # 最多显示5个原因
                print(f"    - {reason}")

            if pm.get("verification"):
                print(f"  Verification checklist:")
                for check in pm["verification"]:
                    print(f"    [ ] {check}")

        output_items.append(
            {
                "id": pm_id,
                "level": level,
                "confidence": round(confidence, 4),
                "title": pm.get("title", "N/A"),
                "severity": pm.get("severity", "N/A"),
                "reasons": agg.reasons,
                "verification": pm.get("verification", []),
            }
        )

        if is_blocking:
            blocking.append(pm_id)
        else:
            warnings.append(pm_id)

    # 总结
    if args.output == "json":
        print(
            json.dumps(
                {
                    "summary": {
                        "blocking": len(blocking),
                        "warnings": len(warnings),
                    },
                    "results": output_items,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"\n{'=' * 50}")
        print(f"Summary: {len(blocking)} blocking, {len(warnings)} warnings")

    # 决定退出码
    if blocking and args.mode == "block":
        print(f"\n{len(blocking)} postmortem(s) triggered with high confidence.")
        print("Please review the changes and verify they don't reintroduce past issues.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

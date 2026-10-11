"""Synthetic editorial intake tests. No user articles, network or model spending."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import article_intake as intake
import agent_team as team
import agent_role_contracts as roles
import director


def sample_article():
    return """# 城市里的一天

## 绪论
这一章收集几个生活建议。这段不是一个独立短视频选题。

### 1. 下雨前先关好窗
- 成本：不额外花钱。
- 说人话：天空渐渐变暗。小林发现窗边的纸张被风吹动。他起身关窗，桌上的信封没有被淋湿。
- 收益：这里是写作示例，不是专业研究。
- 证据等级：B
- 来源：https://example.invalid/rain
- 备注：不要把这个故事当成实际天气预报。

### 2. 离开图书馆前整理桌面
- 成本：只需一分钟。
- 说人话：她放下借来的书，检查桌面有没有留下笔。工作人员看见桌面整洁，笑着点头。
- 收益：这只是虚构事件。
- 来源：https://example.invalid/library

### 3. 晚上关掉走廊的灯
- 说人话：他关掉走廊的灯。走廊安静了。
"""


def synthetic_long_article():
    parts = ["# 虚构的生活百科", "\n介绍"]
    for i in range(1, 19):
        parts.append(f"""
### {i}. 虚构测试选题第{i}条
- 成本：假设免费。
- 说人话：主人公把信放到桌上。他认真看了看信封，然后轻轻打开。
- 收益：纯虚构练习，不得称作科学证据。
- 来源：https://example.invalid/{i}
""")
    return "".join(parts)


class ArticleIntakeTests(unittest.TestCase):
    def setUp(self):
        self.article = sample_article()

    def test_18_sections_detected_without_including_opening_chapter(self):
        source = synthetic_long_article()
        catalog = intake.episode_catalog(source)
        self.assertEqual(catalog["section_count"], 18)
        self.assertEqual([x["episode_id"] for x in catalog["episodes"]],
                         [f"EP{i:02d}" for i in range(1, 19)])
        self.assertTrue(catalog["automatic_series_split_is_proposal"])
        self.assertFalse(catalog["approved_for_publication"])
        self.assertNotIn("信封", json.dumps(catalog, ensure_ascii=False))

    def test_per_episode_source_spans_exact_original(self):
        source = self.article
        result = intake.prepare_episode(source, "EP01")
        self.assertEqual(result["status"], "editorial_review_required")
        self.assertEqual(result["source_sha256"], hashlib.sha256(source.encode()).hexdigest())
        for trace in result["shot_source_spans"]:
            i, j = trace["source_span"]
            shot = next(x for x in result["plan"]["shots"]
                        if x["id"] == trace["shot_id"])
            self.assertEqual(source[i:j], shot["narration"])
        self.assertNotIn("整理桌面", result["plan"]["editorial"]["narration_script"])

    def test_existing_director_plan_schema_validates(self):
        result = intake.prepare_episode(self.article, "EP01")
        errors, warnings = director.validate(result["plan"])
        self.assertEqual(errors, [])
        self.assertEqual(result["plan"]["production"]["publishing_status"],
                         "review_required")
        self.assertFalse(result["review"]["ready_for_video_model"])
        self.assertFalse(result["review"]["visual_directing_complete"])
        self.assertTrue(all(c["status"] == "needs_review"
                            for c in result["plan"]["claims"]))
        self.assertGreater(len(result["plan"]["shots"]), 1)
        self.assertEqual(result["plan"]["duration"], sum(
            x["duration"] for x in result["plan"]["shots"]))

    def test_legacy_storyboard_preview_renders_from_intake_draft(self):
        candidate = intake.prepare_episode(self.article, "EP01")
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "synthetic-storyboard.html"
            director.render_preview(candidate["plan"], destination)
            html = destination.read_text("utf-8")
            self.assertIn(candidate["plan"]["title"], html)
            self.assertIn(candidate["plan"]["shots"][0]["narration"], html)
            self.assertIn("不是实际视频", html)
            self.assertFalse(candidate["review"]["ready_for_video_model"])

    def test_native_team_first_department_gets_same_authoritative_base(self):
        result, packet = intake.prepare_first_department(self.article, "EP02")
        self.assertEqual(packet["task_id"], "director_brief")
        self.assertEqual(result["team"]["base_digest"],
                         team.fingerprint(result["plan"]))
        self.assertEqual(team.ready(result["team"]), ["director_brief"])
        episode_text = intake.episode_source_for_team(self.article, "EP02")
        self.assertTrue(team.source_matches(result["team"], episode_text))
        self.assertFalse(team.source_matches(result["team"], self.article))
        req = roles.build_role_messages(
            result["plan"], result["team"], "director_brief",
            source_text=episode_text)
        self.assertTrue(req["contains_private_material"])
        self.assertFalse(req["external_model_call_authorized"])
        self.assertIn("图书馆", req["messages"][1]["content"])
        self.assertTrue(all(t["revision"] == 0
                            for t in result["team"]["tasks"].values()))

    def test_readonly_private_text_is_not_stored_in_ledger_or_catalog(self):
        c = intake.episode_catalog(self.article)
        e = intake.prepare_episode(self.article, "EP01")
        self.assertNotIn("桌上的信封没有被淋湿", json.dumps(c, ensure_ascii=False))
        self.assertNotIn("桌上的信封没有被淋湿",
                         json.dumps(e["team"], ensure_ascii=False))
        self.assertFalse(e["team"]["release"]["human_approved"])
        self.assertFalse(e["team"]["release"]["paid_api_authorized"])
        self.assertFalse(e["no_api_calls"] is False)

    def test_storyboard_is_placeholders_not_fake_director_or_ai_video(self):
        e = intake.prepare_episode(self.article, "EP01")
        self.assertTrue(all(s["visual_type"] in ("text_card", "data_graphic")
                            for s in e["plan"]["shots"]))
        self.assertEqual(director.compile_prompts(e["plan"]), [])
        self.assertIn("SHOT_VISUALS_ARE_POST_PLACEHOLDERS_NOT_AI_CREATION",
                      e["warnings"])
        self.assertFalse(e["review"]["narration_approved"])

    def test_numbered_headers_preserve_author_ordinal_even_when_skipped(self):
        source = """# Notes
### 1. 小故事
- 说人话：她打开门。
### 3. 另一个故事
- 说人话：她关好门。"""
        c = intake.episode_catalog(source)
        self.assertEqual([x["episode_id"] for x in c["episodes"]],
                         ["EP01", "EP03"])
        with self.assertRaisesRegex(ValueError, "UNKNOWN_EPISODE_ID"):
            intake.prepare_episode(source, "EP02")

    def test_duplicate_episode_number_fails_not_silent_merge(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID"):
            intake.episode_catalog("""### 1. A
- 说人话：出发。
### 1. B
- 说人话：回来。
""")

    def test_fenced_markdown_numbered_heading_is_ignored(self):
        source = """# Script
```markdown
### 99. Never create this fake episode
```
### 1. Real example
- 说人话：主人公整理书桌。"""
        c = intake.episode_catalog(source)
        self.assertEqual(c["section_count"], 1)
        self.assertEqual(c["episodes"][0]["episode_id"], "EP01")

    def test_plain_script_without_headings_is_supported(self):
        text = "她打开房门，看到桌上放着一封信。她走近桌子，拿起信封。"
        e = intake.prepare_episode(text)
        self.assertEqual(e["status"], "editorial_review_required")
        self.assertEqual(e["plan"]["title"], "完整短文")
        self.assertEqual(e["plan"]["editorial"]["narration_script"], text)

    def test_notes_with_no_spoken_summary_must_not_fake_narration(self):
        article = """# 资料
### 1. 观察
- 成本：很小。
- 收益：我不知道是否应该上镜。
- 来源：https://example.invalid/unknown"""
        e = intake.prepare_episode(article)
        self.assertEqual(e["status"], "needs_script_editor")
        self.assertIsNone(e["plan"])
        self.assertIsNone(e["team"])
        self.assertIn("NO_SPOKEN_SUMMARY: MANUAL_SCRIPT_EDIT_REQUIRED",
                      e["warnings"])

    def test_long_spoken_section_is_cut_with_explicit_omissions(self):
        opening = "她把信放到桌上。" * 50
        article = "### 1. 信封故事\n- 说人话：" + opening
        e = intake.prepare_episode(article)
        self.assertEqual(e["status"], "editorial_review_required")
        self.assertIn("NARRATION_ABRIDGED_WITH_EXPLICIT_OMISSIONS",
                      e["warnings"])
        self.assertTrue(any("preview length" in x["reason"]
                            for x in e["plan"]["editorial"]["omissions"]))
        self.assertLessEqual(e["plan"]["duration"], 75)
        self.assertLessEqual(len(e["plan"]["shots"]), 20)
        self.assertLessEqual(len(e["plan"]["editorial"]["narration_script"]), 185)

    def test_all_claims_needs_review_and_sources_are_unverified(self):
        source = """# 课堂
### 1. 预防某种疾病
- 说人话：在虚构试验里，50个人中有20个人出现症状。其他人并未报告。
- 来源：https://example.invalid/experiment"""
        e = intake.prepare_episode(source)
        self.assertEqual(e["plan"]["risk_domain"], "medical")
        self.assertTrue(all(c["status"] == "needs_review"
                            for c in e["plan"]["claims"]))
        self.assertEqual(e["source_evidence_urls_unverified"],
                         ["https://example.invalid/experiment"])
        self.assertIn("SOURCE_CLAIMS_UNVERIFIED", e["warnings"])
        self.assertTrue(any(s["visual_type"] == "data_graphic"
                            for s in e["plan"]["shots"]))

    def test_source_tampering_invalidates_started_team(self):
        e = intake.prepare_episode(self.article)
        self.assertFalse(team.source_matches(e["team"], self.article + " edits"))
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            roles.build_role_messages(e["plan"], e["team"], "director_brief",
                                      source_text=self.article + " edits")
        self.assertTrue(team.source_matches(
            e["team"], intake.episode_source_for_team(self.article)))

    def test_section_count_limit_fails_closed(self):
        source = "\n".join(f"### {i}. A\n- 说人话：安全。" for i in range(1, 124))
        with self.assertRaisesRegex(ValueError, "TOO_MANY_SECTIONS"):
            intake.episode_catalog(source)

    def test_large_source_or_empty_source_rejected(self):
        for source in ("", " ", "\0", "a" * 250001):
            with self.assertRaises(ValueError):
                intake.episode_catalog(source)

    def test_reviewable_series_episode_has_no_actual_media_or_model_call(self):
        e = intake.prepare_episode(synthetic_long_article(), "EP01")
        self.assertEqual(e["status"], "editorial_review_required")
        self.assertFalse(e["review"]["paid_model_authorized"])
        self.assertFalse(e["review"]["data_claims_verified"])
        self.assertFalse(e["review"]["ready_for_video_model"])
        self.assertEqual(e["team"]["budget_policy"]["llm_requests_enabled"], False)


if __name__ == "__main__":
    unittest.main()

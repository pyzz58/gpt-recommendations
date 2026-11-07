"""Context-aware Chinese copy editing within the existing issue budget.

Keeps English sentences/paragraph IDs unchanged. Structural/numeric checks are
not full semantic verification; each failed article retains its MT draft.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal
import json
import logging
from pathlib import Path
import re
import requests
from edition_budget import BudgetExhausted
from translation_editor import polish_translation

LOG = logging.getLogger("newspaper.chinese_editor")
REJECTION_CODES = {"missing_sentences", "invalid_sentence_id", "invalid_translation_length",
                   "changed_numbers", "translation_qa", "uncertainty_requires_review",
                   "changed_percent_unit"}


def _numbers(text):
    # Compare quantities, not their language-specific notation. Never round.
    text = re.sub(r"\bY2K\b|千年虫", "millennium_bug", text)
    text = re.sub(r"(\d{1,2})世纪(\d0)年代", lambda m: str((int(m[1])-1)*100+int(m[2])), text)
    text = re.sub(r"第([一二三四五六七八九十])天", lambda m: "第"+str("一二三四五六七八九十".index(m[1])+1)+"天", text)
    text = re.sub(r"([$£€]\s*\d+(?:\.\d+)?)m\b", r"\1 million", text)
    months = "January February March April May June July August September October November December".split()
    for month, number in zip(months, range(1, 13)):
        text = re.sub(r"\b" + month + r"\b", str(number) + "月", text)
    for number, word in enumerate(("first", "second", "third", "fourth"), 1):
        text = re.sub(r"\b" + word + r"[- ]+quarter\b", str(number) + "季度", text, flags=re.I)
        text = text.replace("第" + "一二三四"[number-1] + "季度", str(number) + "季度")
    text = re.sub(r"\bQ([1-4])\b", r"\1季度", text)
    scales = {"thousand": 1000, "million": 10**6, "billion": 10**9, "trillion": 10**12,
              "bn": 10**9, "mn": 10**6, "千": 1000, "万": 10**4, "百万": 10**6,
              "千万": 10**7, "亿": 10**8, "十亿": 10**9, "万亿": 10**12}
    pattern = r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(thousand\b|million\b|billion\b|trillion\b|bn\b|mn\b|万亿|十亿|千万|百万|亿|万|千)?"
    return Counter(Decimal(n.replace(",", "")) * scales.get((unit or "").lower(), 1)
                   for n, unit in re.findall(pattern, text, flags=re.I))


def edit_chinese_reports(grouped, key, ledger, *, transport=None, before_request=None):
    """One request per article, no retries; keep the highest-impact stories first.

    All calls use the same issue ledger. Shortage/oversized prompts fall back to
    the already built draft; no new source fetching, translation model or service.
    """
    output = {section: [dict(a) for a in articles] for section, articles in grouped.items()}
    if not key or ledger is None:
        return output
    system = Path(__file__).with_name("CHINESE_NEWS_EDITOR.md").read_text(encoding="utf-8")
    articles = sorted((a for row in output.values() for a in row
                       if a.get("source_language") != "zh" and a.get("bilingual_pairs")),
                      key=lambda a: a.get("importance_score", 0), reverse=True)
    for article in articles:
        pairs = article["bilingual_pairs"]
        records = [{"id": "title", "en": article["title"], "draft_zh": article.get("title_zh", "")}]
        records.extend({"id": str(i), "paragraph": p.get("paragraph_id", 0),
                        "en": p["en"], "draft_zh": p["zh"]} for i, p in enumerate(pairs))
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps({"sentences": records}, ensure_ascii=False)}]
        try:
            raw = ledger.request(messages, 4200, key, purpose="chinese",
                                 transport=transport, before_request=before_request)
            translations = json.loads(raw)["translations"]
            if not isinstance(translations, list) or len(translations) != len(records):
                raise ValueError("missing_sentences")
            by_id = {}
            source = {r["id"]: r["en"] for r in records}
            for item in translations:
                identifier, text = item["id"], item["zh"]
                if not isinstance(identifier, str) or identifier not in source or identifier in by_id:
                    raise ValueError("invalid_sentence_id")
                if not isinstance(text, str) or not text.strip() or len(text) > 8 * len(source[identifier]) + 100:
                    raise ValueError("invalid_translation_length")
                scope = source[identifier]
                if identifier == "title":
                    ids = item.get("source_ids", ["title"])
                    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in source for i in ids):
                        raise ValueError("invalid_sentence_id")
                    scope = "\n".join(source[i] for i in ids)
                numeric_source = scope
                numbers_ok = (_numbers(text) <= _numbers(numeric_source) if identifier == "title"
                              else _numbers(text) == _numbers(numeric_source))
                if not numbers_ok:
                    raise ValueError("changed_numbers")
                qa_scope = re.sub(r"\bnot least\b", "especially", scope, flags=re.I)
                if "匿名" in text:
                    qa_scope = re.sub(r"\bnot to be named\b", "to remain anonymous", qa_scope, flags=re.I)
                if "冻结" in text:
                    qa_scope = re.sub(r"\bwithout access to money\b", "with money frozen", qa_scope, flags=re.I)
                text, flags = polish_translation(qa_scope, text)
                # Percentage equivalence is checked below using numeric values.
                flags = [flag for flag in flags if flag != "percentage_requires_review"]
                if flags or not re.search(r"[\u4e00-\u9fff]", text):
                    raise ValueError("translation_qa")
                uncertainty_scope = scope
                if re.search(r"管制|约束", text):
                    uncertainty_scope = re.sub(r"\bsubject to\b(?=.{0,30}\bexport controls\b)", "regulated by", scope, flags=re.I)
                if re.search(r"\b(?:may|might|could|possible|potential|preliminary|expected|subject to|unless)\b", uncertainty_scope, re.I):
                    undecided = "尚未决定" in text and re.search(r"\b(?:unclear|decide|undecided)\b", scope, re.I)
                    if not undecided and not re.search(r"可能|或许|可以|可望|潜在|初步|预计|预期|预料|有待|取决于|除非|或将|或非|有望|能否|是否|不清楚|不确定|尚待|未定|拟|计划", text):
                        raise ValueError("uncertainty_requires_review")
                # A percentage symbol must remain attached to the same value;
                # matching digits alone must not turn 5% into an ordinary count.
                percentages = re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b|per cent\b)", scope, re.I)
                if identifier == "title":
                    percentages = [v for v in percentages if Decimal(v) in _numbers(text)]
                expected_percent = Counter(Decimal(value) for value in percentages)
                actual_percent = Counter(Decimal(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", text))
                actual_percent.update(Decimal(value) for value in re.findall(r"百分之\s*(\d+(?:\.\d+)?)", text))
                if expected_percent != actual_percent:
                    raise ValueError("changed_percent_unit")
                by_id[identifier] = text
            # Commit only after every sentence/title passes; no mixed half-edited story.
            article["title_zh"] = by_id["title"]
            article["title_qa_flags"] = []
            article["bilingual_pairs"] = [{**p, "zh": by_id[str(i)]} for i, p in enumerate(pairs)]
            article["reading_zh"] = "\n\n".join(
                " ".join(by_id[str(i)] for i, p in enumerate(pairs) if p.get("paragraph_id", 0) == pid)
                for pid in dict.fromkeys(p.get("paragraph_id", 0) for p in pairs))
            article["translation_qa_flags"] = []
            article["chinese_editing_mode"] = "context_edited"
            zh_by_en = {p["en"]: by_id[str(i)] for i, p in enumerate(pairs)}
            article["grammar_lessons"] = [
                {**lesson, "sentence_zh": zh_by_en.get(lesson.get("sentence_en"), lesson.get("sentence_zh", ""))}
                for lesson in (article.get("grammar_lessons") or [])]
        except BudgetExhausted:
            LOG.warning("CHINESE_EDITOR_BUDGET_STOP; remaining stories retain MT drafts")
            break
        except (RuntimeError, ValueError, TypeError, KeyError, requests.RequestException) as exc:
            reason = str(exc) if str(exc) in REJECTION_CODES else type(exc).__name__
            http = re.fullmatch(r"Editorial API HTTP (\d{3})", str(exc))
            if http:
                reason = "http_" + http.group(1)
            LOG.warning("CHINESE_EDITOR_FALLBACK reason=%s", reason)
            article["chinese_editing_mode"] = "mt_fallback"
            article["chinese_editing_reason"] = reason
            # Never replay a potentially billed request or expose provider text.
    LOG.info("CHINESE_EDITOR_AUDIT=%s", json.dumps(dict(Counter(
        a.get("chinese_editing_mode", "mt_budget_or_not_attempted") for a in articles)), sort_keys=True))
    return output

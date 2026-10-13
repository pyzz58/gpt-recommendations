"""In-article vocabulary and grammar notes from actual published reading excerpts.

Uses spaCy pretrained English tagger/parser. Every displayed grammar example
comes from the article itself. Does not generate fictional quotations.
"""
from __future__ import annotations

import functools
import re

# Only explicitly attested words get their pre-reviewed Chinese gloss.
VOCABULARY = {
    "federal reserve": "美国联邦储备系统／美联储",
    "central bank": "中央银行",
    "interest rate": "利率",
    "rate cut": "降息",
    "rate hike": "加息",
    "monetary policy": "货币政策",
    "inflation": "通货膨胀",
    "deflation": "通货紧缩",
    "consumer price index": "消费者价格指数",
    "gross domestic product": "国内生产总值",
    "unemployment": "失业",
    "employment": "就业",
    "recession": "经济衰退",
    "economic outlook": "经济前景",
    "forecast": "预测",
    "treasury": "国债／财政部（依语境而定）",
    "bond yield": "债券收益率",
    "yields": "收益率（需结合语境）",
    "earnings": "企业收益／财报",
    "revenue": "营收",
    "profit margin": "利润率",
    "volatility": "波动性",
    "dividend": "股息",
    "stock market": "股票市场",
    "shareholders": "股东",
    "investors": "投资者",
    "valuation": "估值",
    "quarterly": "季度的",
    "guidance": "业绩指引／指导（依语境而定）",
    "merger": "合并",
    "acquisition": "收购",
    "initial public offering": "首次公开募股",
    "funding round": "融资轮次",
    "venture capital": "风险投资",
    "startup": "初创企业",
    "entrepreneur": "创业者",
    "business model": "商业模式",
    "cash flow": "现金流",
    "profitability": "盈利能力",
    "intellectual property": "知识产权",
    "regulation": "监管规定",
    "sanctions": "制裁",
    "legislation": "法律制定／立法",
    "diplomacy": "外交",
    "ceasefire": "停火",
    "agreement": "协议",
    "tariff": "关税",
    "supply chain": "供应链",
    "artificial intelligence": "人工智能",
    "machine learning": "机器学习",
    "semiconductor": "半导体",
    "inference": "推理（AI语境）",
    "breakthrough": "突破",
    "researchers": "研究人员",
    "clinical trial": "临床试验",
    "drug discovery": "药物发现",
    "efficacy": "有效性／疗效",
    "adverse events": "不良事件",
    "peer reviewed": "经过同行评审的",
    "randomized": "随机化的",
    "treatment": "治疗",
    "diagnosis": "诊断",
    "approval": "批准",
}
EXPLANATIONS = {
    "present_perfect": (
        "现在完成时 · Present Perfect",
        "have/has + 过去分词",
        "表示过去发生的动作与现在有关；注意区分一般过去时。",
    ),
    "passive": (
        "被动语态 · Passive Voice",
        "be + 过去分词",
        "强调动作的承受者，新闻里常用于报道决定、政策或研究结果。",
    ),
    "conditional": (
        "条件从句 · Conditional Clause",
        "if/unless + 从句，主句",
        "说明在某个条件成立或不成立时可能出现的结果。",
    ),
    "relative": (
        "定语从句 · Relative Clause",
        "先行词 + who/which/that（有时省略）+ 从句",
        "给前面的名词补充描述、限定其范围。",
    ),
    "modal": (
        "情态动词 · Modal Verb",
        "may/might/could/must/should + 动词原形",
        "表达可能性、义务或判断；尤其要留意新闻中的不确定语气。",
    ),
    "infinitive": (
        "不定式 · Infinitive",
        "to + 动词原形",
        "常用于表达目的、意图或紧随某些动词之后。",
    ),
    "past": (
        "一般过去时 · Simple Past",
        "动词过去式",
        "用于叙述已发生的事件；不要与现在完成时混淆。",
    ),
}


@functools.lru_cache(maxsize=1)
def english_parser():
    try:
        import spacy
        return spacy.load("en_core_web_sm", disable=["ner"])
    except (OSError, ImportError) as exc:
        raise RuntimeError(
            "spaCy en_core_web_sm is required for evidence-based grammar examples. "
            "Install with: python -m spacy download en_core_web_sm"
        ) from exc


def _grammar_type(sent) -> str | None:
    """High-precision patterns based on spaCy's parser + POS and morphology."""
    tokens = list(sent)
    # Prioritize distinctive constructs rather than just past tense.
    for tok in tokens:
        if tok.pos_ in {"VERB", "AUX"} and tok.tag_ == "VBN":
            if any(child.lemma_ == "have" and child.lower_ in {"has", "have", "'ve"} and child.dep_ in {"aux", "auxpass"} for child in tok.children):
                return "present_perfect"
    if any(tok.dep_ == "auxpass" or "Pass" in tok.morph.get("Voice")
           for tok in tokens):
        return "passive"
    if any(tok.lower_ in {"if", "unless"} and tok.dep_ == "mark"
           for tok in tokens):
        return "conditional"
    if any(tok.dep_ == "relcl" for tok in tokens):
        return "relative"
    if any(tok.pos_ == "AUX" and tok.lower_ in
           {"may", "might", "could", "must", "should", "would"}
           and tok.dep_ == "aux" and tok.head.pos_ == "VERB"
           for tok in tokens):
        return "modal"
    for idx, tok in enumerate(tokens[:-1]):
        if tok.lower_ == "to" and tok.pos_ == "PART" and tokens[idx + 1].pos_ == "VERB":
            return "infinitive"
    if any(tok.pos_ == "VERB" and tok.tag_ == "VBD" and tok.dep_ in
           {"ROOT", "conj", "advcl", "ccomp"} for tok in tokens):
        return "past"
    return None


def _pick_grammar(english: str, nlp, count: int = 3) -> list[dict]:
    doc = nlp(english)
    found = []
    seen_types = set()
    for sentence in doc.sents:
        raw = sentence.text.strip()
        if not (35 <= len(raw) <= 245) or len(sentence) < 7:
            continue
        if raw.count("\n") > 0:
            raw = " ".join(raw.split())
        if not raw or len(raw) > 245:
            continue
        grammar_type = _grammar_type(sentence)
        if not grammar_type or grammar_type in seen_types:
            continue
        title, pattern, note = EXPLANATIONS[grammar_type]
        found.append({
            "type": grammar_type,
            "title": title,
            "pattern": pattern,
            "explanation": note,
            "sentence_en": raw,
        })
        seen_types.add(grammar_type)
        if len(found) >= count:
            break
    return found


def _pick_vocab(english: str, nlp, maximum: int = 5) -> list[dict]:
    # Longer multiword expressions before single words.
    found = []
    text = english.lower()
    for term in sorted(VOCABULARY, key=lambda x: (-len(x.split()), -len(x))):
        match = re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)
        if match:
            found.append({
                "word": english[match.start():match.end()],
                "definition": VOCABULARY[term],
                "position": match.start(),
            })
    # Select earliest attested topical terms, avoiding nested phrases.
    found.sort(key=lambda x: x["position"])
    chosen = []
    for candidate in found:
        start = candidate["position"]
        if any(abs(start - other["position"]) < 3 and
               (candidate["word"].lower() in other["word"].lower() or
                other["word"].lower() in candidate["word"].lower())
               for other in chosen):
            continue
        chosen.append(candidate)
        if len(chosen) == maximum:
            break
    return [{"word": item["word"], "definition": item["definition"]}
            for item in chosen]


def attach_lessons(grouped: dict, translator, grammar_limit: int = 3, vocab_limit: int = 5) -> dict:
    nlp = english_parser()
    result = {}
    for category, articles in grouped.items():
        result[category] = []
        for article in articles:
            entry = dict(article)
            if entry.get("source_language") == "zh":
                entry["grammar_lessons"] = []
                entry["vocabulary"] = []
                result[category].append(entry)
                continue
            original = entry["reading_en"]
            lessons = _pick_grammar(original, nlp, count=grammar_limit)
            for grammar in lessons:
                grammar["sentence_zh"] = translator.translate(grammar["sentence_en"])
            entry["grammar_lessons"] = lessons
            # Newspaper adviser mode has no vocabulary glossary. Preserve the
            # key for backward compatibility, but never fill or render it.
            entry["vocabulary"] = []
            result[category].append(entry)
    return result

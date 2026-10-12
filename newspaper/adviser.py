"""Source-bounded global situation advisory notes — no generative model needed.

Editorial architecture inspired by research-first approaches (STORM,
GPT-Researcher), but this is intentionally a deterministic, auditable fallback,
NOT a deployed STORM/LLM agent and NOT expert forecasts.
"""
from __future__ import annotations
import re
from collections import Counter

DOMAIN_CONTEXT = {
    "全球新闻": (
        "全球政治与公共安全",
        "观察政策、冲突、能源运输、供应链和跨境贸易是否出现实际变化，而不只看报道热度。",
        "后续需要核对政府正式公告、伤亡或贸易数据、跨境运费及是否出现独立媒体的新增确认。",
    ),
    "美股与投资": (
        "美国股市与公司经营",
        "区分股价反应和企业基本面；关注营收、利润率、现金流、指引及估值对利率的敏感性。",
        "关注正式财报、监管披露、管理层指引和市场是否已提前反映这些消息。",
    ),
    "美联储与宏观": (
        "货币政策与宏观经济",
        "观察通胀、就业、政府债券收益率以及政策预期之间的传导，而不是从单条新闻直接推断降息。",
        "重点核对美联储公告、FOMC 会议纪要、CPI/PCE、就业与国债收益率。",
    ),
    "创业与商业模式": (
        "创业、融资与商业模式",
        "分开考察融资估值、实际付费客户、收入质量、单位经济模型以及是否存在可持续竞争优势。",
        "关注用户留存、毛利、真实交易条款、投资人表述与企业自己的公开披露。",
    ),
    "AI与科技": (
        "人工智能与产业技术",
        "判断技术是否经过可重复验证，是否有成本、性能和商业化收益的可核实数据。",
        "关注论文/代码、独立基准测试、生产部署、推理成本以及真实商业付费。",
    ),
    "医疗与科学": (
        "医学研究与前沿科学",
        "区分早期实验、观察性相关、临床试验与获批上市；不将研究结论直接等同于临床有效性。",
        "查看研究设计、样本量、主要终点、不良事件、同行评审和监管机构意见。",
    ),
}
SIGNALS = {
    "政策信号": re.compile(r"\b(fomc|federal reserve|central bank|rate (?:cut|hike)|tariffs?|regulation|sanctions?)\b", re.I),
    "能源与供应链": re.compile(r"\b(oil|gas|energy|shipping|supply chain|strait|refiner(?:y|ies))\b", re.I),
    "企业经营": re.compile(r"\b(earnings|revenue|profit|merger|acquisition|ipo|guidance|quarterly)\b", re.I),
    "技术突破": re.compile(r"\b(ai|artificial intelligence|machine learning|semiconductor|fusion|breakthrough)\b", re.I),
    "健康证据": re.compile(r"\b(vaccine|clinical trial|patient|fda|placebo|dementia|drug)\b", re.I),
}

def domain_advice(category: str, articles: list[dict]) -> dict:
    title, lens, followup = DOMAIN_CONTEXT.get(
        category, (category, "关注原始事实、证据与背景。", "持续核查后续官方来源。")
    )
    sources = {a.get("source", "").strip() for a in articles if a.get("source")}
    signals = Counter()
    for a in articles:
        text = str(a.get("title", "")) + " " + str(a.get("summary", ""))
        for name, pattern in SIGNALS.items():
            if pattern.search(text):
                signals[name] += 1
    if not articles:
        situation = "该领域在严格日期与可读取正文筛选后没有足够证据，不作当天局势判断。"
    else:
        signal_text = "、".join(f"{k}（{n}篇标题或摘要出现相关词）" for k, n in signals.most_common(3))
        situation = (
            f"在本期已选入的{len(articles)}篇报道、{len(sources)}个发布来源中，"
            + (f"可以观察到{signal_text}等线索。" if signal_text else "尚无足够共同主题可供归纳。")
            + " 此处反映本次采集样本，而不是全球所有事件的统计。"
        )
    return {
        "heading": title,
        "situation": situation,
        "analytical_lens": lens,
        "what_to_watch": followup,
        "confidence": (
            "已核实的是新闻来源和选择数量；事件因果与政策后果尚需额外研究。"
            if articles else "没有有效样本，勿据此推断该领域平静。"
        ),
    }

def article_advice(article: dict) -> dict:
    category = article.get("category", "")
    heading, lens, followup = DOMAIN_CONTEXT.get(
        category, (category, "需要更多独立事实验证。", "关注权威机构后续发布。")
    )
    related = article.get("related_sources") or []
    sources_text = (
        f"同类标题涉及 {len(related)} 个来源，但标题相似不等于独立事实核验。"
        if len(related) > 1 else
        "本期仅有单个来源的可读正文，无法据此确认存在广泛一致的独立报道。"
    )
    score = article.get("importance_score")
    judgement = (
        f"此事件在自动筛选中的参考分为 {int(score)}/100；这是主题规则分，不是影响概率。"
        if isinstance(score, (int, float)) else "未计算出可审计的排序参考分。"
    )
    return {
        "key_question": "这件事真正改变了什么？",
        "assessment": lens,
        "watch": followup,
        "uncertainty": sources_text + judgement,
        "evidence": "来源：" + str(article.get("source", "未注明来源")) +
                    "；可核查原始报道链接：" + str(article.get("url", "")),
    }

def global_linkages(grouped: dict) -> list[dict]:
    """Explicit scenario pathways rather than claiming relationships occurred."""
    populated = {category for category, articles in grouped.items() if articles}
    chains = [
        ({"全球新闻", "美联储与宏观"},
         "地缘政治 → 能源/贸易 → 通胀 → 央行政策",
         "仅当实际能源供应或贸易数据发生变化时才可沿这条路径讨论影响；当前报道不足以预测方向。"),
        ({"美联储与宏观", "美股与投资"},
         "通胀/就业 → 政策利率预期 → 资金成本 → 股票估值",
         "需结合企业盈利和市场预期，不能把货币政策变化自动等同于股市涨跌。"),
        ({"创业与商业模式", "AI与科技"},
         "技术进展 → 产品效率 → 客户付费 → 企业现金流",
         "融资金额或模型跑分不是商业成功；关注真实客户、毛利与部署成本。"),
        ({"医疗与科学", "AI与科技"},
         "研究结果 → 独立验证 → 监管/临床应用",
         "新论文不等于获批治疗，AI 医疗需要临床效果和安全证据。"),
    ]
    return [
        {"title": title, "caution": caution}
        for required, title, caution in chains if required <= populated
    ]

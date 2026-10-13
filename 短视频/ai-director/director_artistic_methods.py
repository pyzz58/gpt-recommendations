#!/usr/bin/env python3
"""QO-D17: one director's transferable artistic judgment, not style imitation.

Professional sources and differing methods are references, not unquestionable
formulas. Comedy/absurdity is OPT-IN based on the screenplay's own needs.
All authoring is in-memory, UNSENT, and source/director-lock version-bound.
The deterministic contract validates instructions, never artistic merit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import agent_team
import director_department_command as conference

VERSION = "director-artistic-methods-v1"
MODES = frozenset({
    "fiction", "essay", "documentary", "hybrid",
    "absurd_comedy", "character_comedy", "satire",
})
COMIC_MODES = frozenset({
    "off", "absurdist", "character_based", "physical", "satirical", "mixed",
})
GAG_FUNCTIONS = frozenset({
    "none", "setup", "expectation", "disruption",
    "escalation", "reversal", "reaction", "callback", "emotional_payoff",
})
GAG_LADDER = (
    "character_need", "credible_expectation", "comic_disruption",
    "escalation", "reversal", "human_payoff",
)

# These are ORIGINAL project formulations of transferable creative mechanisms,
# not copied screenplays, actor likenesses, shots or protected jokes.
METHOD_LIBRARY = {
    "scorsese_emotion_reveal": {
        "artist": "Martin Scorsese", "transferable_principle":
        "Control what a performance and cut reveal about character, and when.",
        "failure": "A stylish cut prematurely states an emotion that should emerge.",
        "source": "https://www.bfi.org.uk/sight-and-sound/interviews/martin-scorsese-age-innocence",
    },
    "wong_repetition_transformed": {
        "artist": "Wong Kar-wai", "transferable_principle":
        "Return to a visual or sonic motif only when its human meaning changes.",
        "failure": "Same beautiful shot repeated with no new relational meaning.",
        "source": "https://www.bfi.org.uk/sight-and-sound/interviews/wong-kar-wai-in-mood-love",
    },
    "nolan_sound_structure": {
        "artist": "Christopher Nolan", "transferable_principle":
        "Design information order and sound/silence as embodied audience experience.",
        "failure": "Loud sound or shuffled chronology with no cognitive purpose.",
        "source": "https://www.bfi.org.uk/sight-and-sound/interviews/christopher-nolan-showmans-odyssey-oppenheimer",
    },
    "leigh_truthful_behavior": {
        "artist": "Mike Leigh", "transferable_principle":
        "Find characters' real wants and actions through specificity and alternatives.",
        "failure": "Actors merely illustrate adjectives or serve a prefabricated gag.",
        "source": "https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2024-mike-leigh/",
    },
    "ozu_stillness_and_space": {
        "artist": "Yasujiro Ozu", "transferable_principle":
        "Let stable human-scale space, duration and ordinary objects hold emotion.",
        "failure": "Empty static shots without concrete relationship or change.",
        "source": "https://www.criterion.com/current/posts/5845-yasujiro-ozu-s-cinematic-style",
    },
    "chow_absurdity_from_character": {
        "artist": "Stephen Chow", "transferable_principle":
        "A sincere, legible character desire can generate surprising absurd causality.",
        "failure": "Random surreal punchlines unrelated to the character's aim.",
        "source": "https://indielondon.co.uk/film/kung_fu_hustle_chow.html",
    },
    "chow_visual_gag_over_verbal_label": {
        "artist": "Stephen Chow", "transferable_principle":
        "Prefer readable action, spatial reversals and reaction timing over explaining jokes.",
        "failure": "Physical comedy only described in voiceover or impossible AI microactions.",
        "source": "https://outnow.ch/en/News/2005/05/23/Kung-Fu-Hustle-The-Interview-with-Stephen-Chow",
    },
    "chow_underdog_laughter_and_pathos": {
        "artist": "Stephen Chow", "transferable_principle":
        "The underdog's socially awkward attempt may be funny while their need remains real.",
        "failure": "Mock humiliation replaces emotional truth or undermines dignity.",
        "source": "https://www.latimes.com/archives/la-xpm-2005-apr-10-ca-kungfu10-story.html",
    },
    "chow_genre_mixture_story_first": {
        "artist": "Stephen Chow", "transferable_principle":
        "Combine cartoon logic, action and sadness only under intelligible story structure.",
        "failure": "Effects, tonal whiplash or self-referential references bury the narrative.",
        "source": "https://indielondon.co.uk/film/kung_fu_hustle_chow.html",
    },
    "fair_documentary_compression": {
        "artist": "Frederick Wiseman", "transferable_principle":
        "Condense observed reality without manipulating facts or creating false causality.",
        "failure": "Invented reactions or fabricated agreement from documentary cuts.",
        "source": "https://www.bfi.org.uk/sight-and-sound/interviews/when-you-stop-shooting-thats-when-best-thing-going-happen-you-have-persevere-interview-with-frederick-wiseman",
    },
}
DIRECTOR_FIELDS = (
    "story_understanding", "deep_emotional_or_ideational_question",
    "directorial_position", "audience_start_and_end",
    "artistic_style_reason", "visual_motif_and_evolution",
    "sound_silence_and_rhythm", "protect_meaning_over_spectacle",
    "what_the_director_refuses", "departmental_creative_freedom",
)
SHOT_FIELDS = (
    "shot_id", "applied_methods", "audience_before", "audience_after",
    "visible_or_audible_change", "chosen_screen_language",
    "rejected_alternative", "why_choice_works_better",
    "emotion_or_meaning_lost_if_generic", "acting_direction",
    "camera_art_direction", "sound_direction", "editing_direction",
    "ai_production_fallback", "gag_function",
)
COMIC_FIELDS = (
    "why_comedy_belongs_here", "real_character_need",
    "worlds_internal_logic", "comic_target_not_a_vulnerable_person",
    "timing_and_visual_readability", "underlying_emotional_stakes",
    "avoid_random_gags_and_fake_facts", "beat_ladder",
)
LADDER_FIELDS = ("stage", "concrete_story_event", "audience_expectation_shift")

class ArtisticMethodError(ValueError):
    """Stable privacy-safe validation error."""


def _need(condition, error):
    if not condition:
        raise ArtisticMethodError(error)


def _string(value, error, minimum=20):
    _need(isinstance(value, str) and
          minimum <= len(value.strip()) <= 2500 and "\0" not in value,
          error)


def _shape(value, fields, error):
    _need(isinstance(value, dict) and set(value) == set(fields), error)


def _source_lock(base, state, director_command):
    try:
        conference_receipt = conference.validate_command(
            base, state, director_command)
    except (ValueError, KeyError, TypeError):
        raise ArtisticMethodError("ARTISTIC_DIRECTOR_MEETING_NOT_LOCKED") from None
    _need(agent_team.fingerprint(base) == state["base_digest"],
          "ARTISTIC_BASE_STALE")
    return {
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": conference_receipt["director_lock_digest"],
        "director_command_digest": conference_receipt["command_digest"],
    }


def request(base, state, director_command, *, genre, source_text=None):
    """Build UNSENT *same director* craft analysis after existing lock/meeting."""
    _need(genre in MODES, "ARTISTIC_UNSUPPORTED_GENRE")
    version = _source_lock(base, state, director_command)
    if source_text is not None:
        _need(isinstance(source_text, str) and
              hashlib.sha256(source_text.encode("utf-8")).hexdigest() ==
              state["source_digest"], "ARTISTIC_SOURCE_STALE")
    return {
        "kind": "unsent_director_creative_craft_decision",
        "version": VERSION, "dispatch_allowed": False,
        "artistic_quality_certified": False,
        "messages": [
            {"role": "system", "content": (
                "你是同一个电影总导演，必须用自己的戏剧理解选择电影手法，而不是"
                "模仿名导演的色彩、台词、镜头外观或人格。原编剧故事、事实、"
                "人物决定和已定90秒单集时间线是权威，不能暗改。"
                "国际职业电影导演值得学习的是因果选择："
                "斯科塞斯选择何时让观众发现情绪；王家卫让重复的母题改变意义；"
                "诺兰利用声画顺序/沉默造成身体认知；迈克·李从人物真实愿望"
                "与动作中发现戏；小津用日常空间和真实等待形成情绪。"
                "周星驰的方法仅在故事适合荒诞/喜剧时主动考虑："
                "清楚的人物愿望+具体的社会/生活处境→可信期待→意外偏差"
                "→荒诞有因果的升级→反转→小人物的情绪/价值余韵。"
                "物理动作、构图、反应与剪辑的笑点常胜于让旁白讲一个笑话。"
                "无厘头绝不是随机胡闹；正剧、科学、法律、纪实不需要硬插笑料。"
                "荒诞不能假造科普/纪实事实，或把脆弱群体当嘲笑对象。"
                "周星驰访谈强调故事结构、笑与悲并存、视觉行动、跨职业协作，"
                "并非要求所有项目都变成周星驰式影片。"
                "仔细阅读全文和导演锁定创意，以题材/观众体验匹配方法，"
                "每个真实shot要有可见或可听的认知/情感变化，"
                "比较至少一项有根据的替代拍法并说明为什么选这个。"
                "详细讲给演员、摄影美术、声音、剪辑、AI制作人员听："
                "他们分别如何促成同一种观众体验；不得代替专家所有技术判断。"
                "如模型不能完成复杂特技，选择合理分镜/静态/后期方案保留笑点逻辑。"
                "不要为了看起来很有电影感而使用推镜、摇摄、鼓点、爆炸。"
                "可保留沉默或克制；短视频每集最多90秒且clip限制由技术岗处理。"
                "输出指定JSON，不伪造已试拍、已审片、已批准。")},
            {"role": "user", "content": json.dumps({
                "genre": genre,
                "complete_source_script": source_text,
                "director_brief": state["tasks"]["director_brief"]["deliverable"],
                "director_lock": state["tasks"]["director_lock"]["deliverable"],
                "existing_department_conference": director_command,
                "episode_base": base,
                "shot_ids": list(state["shot_ids"]),
                "provenance": version,
                "available_transferable_methods": deepcopy(METHOD_LIBRARY),
                "output_required": {
                    "top_level": [
                        "version", "genre", "provenance", "director",
                        "comic_mode", "comic_design", "chosen_methods", "shots"],
                    "director_fields": DIRECTOR_FIELDS,
                    "method_fields": [
                        "method_id", "why_this_story", "when_to_reject",
                        "audience_effect", "alternative_and_cost"],
                    "comic_fields": COMIC_FIELDS,
                    "comic_ladder_fields": LADDER_FIELDS,
                    "shot_fields": SHOT_FIELDS,
                    "gag_functions": sorted(GAG_FUNCTIONS),
                    "comic_mode_options": sorted(COMIC_MODES),
                },
                "unpaid_without_model_dispatch": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(base, state, director_command, plan):
    version = _source_lock(base, state, director_command)
    _shape(plan, {
        "version", "genre", "provenance", "director",
        "comic_mode", "comic_design", "chosen_methods", "shots",
    }, "ARTISTIC_PLAN_SHAPE")
    _need(plan["version"] == VERSION and plan["provenance"] == version,
          "ARTISTIC_DIRECTOR_PLAN_STALE")
    _need(plan["genre"] in MODES and plan["comic_mode"] in COMIC_MODES,
          "ARTISTIC_GENRE_OR_COMIC_MODE")
    director = plan["director"]
    _shape(director, DIRECTOR_FIELDS, "ARTISTIC_DIRECTOR_INTENT_SHAPE")
    for text in director.values():
        _string(text, "ARTISTIC_THESIS_TOO_SHALLOW", minimum=28)
    choices = plan["chosen_methods"]
    _need(isinstance(choices, list) and 1 <= len(choices) <= 5,
          "ARTISTIC_METHOD_COUNT")
    picked = set()
    for row in choices:
        _shape(row, ("method_id", "why_this_story", "when_to_reject",
                     "audience_effect", "alternative_and_cost"),
               "ARTISTIC_METHOD_SHAPE")
        ident = row["method_id"]
        _need(isinstance(ident, str) and ident in METHOD_LIBRARY
              and ident not in picked, "ARTISTIC_METHOD_UNKNOWN_OR_DUPLICATE")
        picked.add(ident)
        for key in ("why_this_story", "when_to_reject",
                    "audience_effect", "alternative_and_cost"):
            _string(row[key], "ARTISTIC_METHOD_NOT_REASONED")
    is_comic = plan["comic_mode"] != "off"
    if is_comic:
        _need(isinstance(plan["comic_design"], dict),
              "ARTISTIC_COMEDY_WITHOUT_CHARACTER_LOGIC")
        _shape(plan["comic_design"], COMIC_FIELDS, "ARTISTIC_COMEDY_SHAPE")
        for field in COMIC_FIELDS:
            if field != "beat_ladder":
                _string(plan["comic_design"][field],
                        "ARTISTIC_COMEDY_CAUSALITY_MISSING", minimum=25)
        ladder = plan["comic_design"]["beat_ladder"]
        _need(isinstance(ladder, list) and
              [row.get("stage") for row in ladder if isinstance(row, dict)]
              == list(GAG_LADDER) and len(ladder) == len(GAG_LADDER),
              "ARTISTIC_COMEDY_LADDER_CAUSALITY")
        for step in ladder:
            _shape(step, LADDER_FIELDS, "ARTISTIC_COMEDY_LADDER_SHAPE")
            _string(step["concrete_story_event"], "ARTISTIC_COMEDY_EVENT_VAGUE")
            _string(step["audience_expectation_shift"],
                    "ARTISTIC_COMEDY_EXPECTATION_VAGUE")
        # A serious idea can contain comic relief, but an explicit
        # comedy/absurdity mode must trace to a relevant serious principle,
        # not a one-word claim that a 'Stephen Chow style' was used.
        _need(any(x.startswith("chow_") for x in picked),
              "ARTISTIC_COMEDY_CRAFT_NOT_SELECTED")
    else:
        _need(plan["comic_design"] is None,
              "ARTISTIC_UNREQUESTED_COMEDY_BLUEPRINT")
    if plan["genre"] in ("absurd_comedy", "character_comedy", "satire"):
        _need(is_comic, "ARTISTIC_COMEDY_GENRE_MUST_EXPLAIN_GAG")
    shots = plan["shots"]
    shot_ids = state["shot_ids"]
    _need(isinstance(shots, list) and len(shots) == len(shot_ids),
          "ARTISTIC_SCENES_NOT_COVERED")
    prior = set()
    has_comic = False
    for expected, shot in zip(shot_ids, shots):
        _shape(shot, SHOT_FIELDS, "ARTISTIC_SHOT_SHAPE")
        _need(shot["shot_id"] == expected, "ARTISTIC_SHOT_ORDER")
        ids = shot["applied_methods"]
        _need(isinstance(ids, list) and 1 <= len(ids) <= 3 and
              len(set(ids)) == len(ids) and set(ids) <= picked,
              "ARTISTIC_SHOT_UNKNOWN_METHOD")
        _need(shot["gag_function"] in GAG_FUNCTIONS,
              "ARTISTIC_BAD_GAG_ROLE")
        if not is_comic:
            _need(shot["gag_function"] == "none",
                  "ARTISTIC_COMEDY_FORCED_INTO_SERIOUS_FILM")
        else:
            has_comic |= shot["gag_function"] != "none"
        for field in SHOT_FIELDS:
            if field not in ("shot_id", "applied_methods", "gag_function"):
                _string(shot[field], "ARTISTIC_SHOT_LACKS_CRAFT_REASON",
                        minimum=25)
        _need(shot["audience_before"].strip() !=
              shot["audience_after"].strip(),
              "ARTISTIC_NO_AUDIENCE_CHANGE")
        _need(shot["chosen_screen_language"].strip() !=
              shot["rejected_alternative"].strip(),
              "ARTISTIC_NO_MEANINGFUL_ALTERNATIVE")
        signature = (
            shot["visible_or_audible_change"].strip(),
            shot["chosen_screen_language"].strip(),
            shot["audience_after"].strip(),
        )
        _need(signature not in prior,
              "ARTISTIC_COPY_PASTED_SHOT_JUDGMENTS")
        prior.add(signature)
    if is_comic:
        _need(has_comic, "ARTISTIC_COMEDY_WITHOUT_ONSCREEN_FUNCTION")
    return {
        "kind": "director_artistic_methods_receipt",
        "plan_digest": agent_team.fingerprint(plan),
        **version,
        "shot_count": len(shots),
        "chosen_method_ids": sorted(picked),
        "comic_mode": plan["comic_mode"],
        "source_screenplay_preserved": True,
        "director_has_proposed_not_author_approved": True,
        "independent_art_quality_certified": False,
        "video_or_paid_model_generated": False,
    }


def departmental_context(base, state, director_command, plan, department):
    """Embed the director's selected ARTISTIC WHY in the existing role request."""
    receipt = validate(base, state, director_command, plan)
    _need(department in conference.DEPARTMENTS, "ARTISTIC_UNKNOWN_DEPARTMENT")
    by_dept = {
        "acting": "acting_direction",
        "camera_art": "camera_art_direction",
        "sound": "sound_direction",
        "editing_animation": "editing_direction",
        "ai_technical": "ai_production_fallback",
        "quality_review": "emotion_or_meaning_lost_if_generic",
        "director_final": "why_choice_works_better",
    }
    detail = by_dept[department]
    return {
        "kind": "versioned_director_artistic_method_for_specialist",
        "plan_digest": receipt["plan_digest"],
        "genre": plan["genre"],
        "comic_mode": plan["comic_mode"],
        "chosen_methods": deepcopy(plan["chosen_methods"]),
        "director_thesis": deepcopy(plan["director"]),
        "genre_comic_design_if_any": deepcopy(plan["comic_design"]),
        "this_department": department,
        "department_specific_direction_field": detail,
        "per_shot": [{
            "shot_id": shot["shot_id"],
            "applied_methods": list(shot["applied_methods"]),
            "audience_change": {
                "before": shot["audience_before"],
                "after": shot["audience_after"],
                "visible_trigger": shot["visible_or_audible_change"],
            },
            "detailed_department_direction": shot[detail],
            "selected_form": shot["chosen_screen_language"],
            "rejected_form_and_tradeoff": {
                "alternative": shot["rejected_alternative"],
                "why_rejected": shot["why_choice_works_better"],
                "cost_of_generic": shot["emotion_or_meaning_lost_if_generic"],
            },
            "comic_function": shot["gag_function"],
        } for shot in plan["shots"]],
        "specialist_may_propose_better_means_not_silently_rewrite_story": True,
        "independent_craft_or_media_not_verified": True,
    }

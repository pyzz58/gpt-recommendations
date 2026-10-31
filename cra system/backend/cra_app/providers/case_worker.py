"""Isolated local open-weight model used only for grounded explanations."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any


def _prompt(request: dict[str, Any]) -> str:
    evidence = "\n".join(
        f"- {item['evidence_id']}: {item['text']}"
        for item in request["evidence"]
    )
    dimensions = "\n".join(
        f"- {item['dimension']}: {item['status']}; {item['text']}"
        for item in request["dimensions"]
    )
    allowed = ", ".join(item["evidence_id"] for item in request["evidence"])
    allowed_codes = ", ".join(request["allowed_explanation_codes"])
    return f"""You are a cautious clinical-trial monitoring language assistant.
Return ONLY minified JSON with exactly two keys:
{{"explanation_code":"allowed code","evidence_ids":["allowed id"]}}

Hard rules:
- Do not include any digit or date.
- Do not make a diagnosis, causality, seriousness, expectedness or safety conclusion.
- Do not state that any fact or dimension is confirmed or met.
- Say that candidate dimensions and unknown information require CRA or medical review.
- Use only evidence IDs from the supplied list.
- Choose exactly one explanation_code from the supplied allowed list.
- Do not add any other key or prose outside the JSON object.

Evidence:
{evidence}

Deterministic server dimensions:
{dimensions}

Allowed evidence IDs: {allowed}

Allowed explanation codes: {allowed_codes}

Select the code describing whether candidates, unknown information, or both
were supplied by the deterministic server. Do not infer any new result.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    requests = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(requests, list):
        raise ValueError("input must be an array")
    if any(
        request.get("source") != "pure_synthetic"
        for request in requests
    ):
        raise ValueError("provider evaluation accepts only pure synthetic requests")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    revision = "7ae557604adf67be50417f59c2c2f167def9a775"
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        dtype=torch.float32,
    ).eval()
    torch.set_num_threads(min(4, torch.get_num_threads()))
    torch.manual_seed(0)
    results = []
    for request in requests:
        started = time.perf_counter()
        messages = [{"role": "user", "content": _prompt(request)}]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(
            generated[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
        )
        results.append(
            {
                "case_id": request["case_id"],
                "raw_output": raw,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
        )
    raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    max_rss_bytes = raw_rss if sys.platform == "darwin" else raw_rss * 1024
    for result in results:
        result["max_rss_bytes"] = max_rss_bytes
    print("CRA_CASE_RESULT=" + json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

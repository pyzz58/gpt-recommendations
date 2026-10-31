# CRA-W09 provider dependency record

Date: 2026-11-01. Scope: pure-synthetic engineering evaluation only.

| Component | Exact selection | License | Use and boundary |
| --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct | `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775` | Apache-2.0 | Chooses one server-allowed explanation code and supplied evidence IDs; no dimension calculation or medical decision |
| transformers | `4.57.1` | Apache-2.0 | Isolated tokenizer/model loading |
| torch | `2.7.1` | BSD-style PyTorch license | Isolated CPU inference |
| safetensors | `0.5.3` | Apache-2.0 | Isolated weight loading |

The main application remains on the locked Python 3.13 environment and does
not import torch, transformers or model weights. `LocalTransformersCaseAnalysisProvider`
starts an isolated Python 3.12 process through `uv` with the exact packages
above. The model revision is pinned in both provider and worker code.

The approximately 988 MB `model.safetensors` weight file is not committed.
CI downloads the pinned public model only after receiving the synthetic W09
request set. No project, IB, patient record, source file or real clinical
material is supplied to the model.

Grounding is intentionally stricter than the model prompt: the response must
be a JSON object with only `explanation_code` and `evidence_ids`; the code must
be allowed for the deterministic case, every evidence ID must have been
supplied, and legacy/free-text paths reject unsupported numbers, dates, fake
status claims and medical conclusions. A rejected model output leaves the
program candidates, unknowns and questions in place.

The one-synthetic-run evaluation measures provider behavior and resource use,
not clinical accuracy. License texts and transitive dependency notices must be
packaged and reviewed again for any approved production deployment in W15.

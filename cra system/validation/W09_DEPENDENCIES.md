# CRA-W09 provider dependency record

Date: 2026-11-01. Scope: pure-synthetic engineering evaluation only.

| Component | Exact selection | License | Use and boundary |
| --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct | `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775` | Apache-2.0 | Chooses one server-allowed explanation code and supplied evidence IDs; no dimension calculation or medical decision |
| transformers | `4.57.1` | Apache-2.0 | Isolated tokenizer/model loading |
| torch | `2.7.1` | BSD-style PyTorch license | Isolated CPU inference |
| safetensors | `0.5.3` | Apache-2.0 | Isolated weight loading |

The complete transitive environments are locked with distribution hashes in
`provider-locks/analysis-linux-py312.txt` and
`provider-locks/analysis-macos-arm64-py312.txt`. The Linux lock SHA-256 is
`0e94391c3ffb1d11612bc37bf0000ece9e1d96f1e3b3c3ebb6d0300dbf48b6d1`.
The macOS arm64 lock SHA-256 is
`2a72ed509bbd20ba5d92a98785f6a51d7fec57b7534126e966ee1b65a07cfaba`.
The pinned `model.safetensors` SHA-256 is
`fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`;
the worker verifies the downloaded bytes before loading the model.

The OCR isolated environment is likewise locked in
`provider-locks/ocr-linux-py312.txt` and
`provider-locks/ocr-macos-arm64-py312.txt`. The Linux lock SHA-256 is
`a935fb56356b2076fb134776d139e6f2fb98be868a5554b7a6aa8180cf5ce153`.
The macOS arm64 lock SHA-256 is
`fcd0ec5ac7da801c69e8e2c9f608343f1ad4fcab76c3926e3fab6e61169bfcbd`.
OCR evaluation emits the selected lock hash and a SHA-256 manifest over the
Docling model snapshot files. The local macOS evaluation observed model
manifest
`c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`;
CI logs its own authoritative value from the lock-created environment.

The main application remains on the locked Python 3.13 environment and does
not import torch, transformers or model weights. `LocalTransformersCaseAnalysisProvider`
starts an isolated Python 3.12 process through `uv` with the exact packages
above. The model revision is pinned in both provider and worker code.
The provider computes the hash of the actual platform-specific lock it passed
to `uv`, and `UV_TORCH_BACKEND=cpu` prevents implicit accelerator selection.

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

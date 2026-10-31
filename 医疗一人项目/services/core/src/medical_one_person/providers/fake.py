from __future__ import annotations

import hashlib
from decimal import Decimal

from medical_one_person.contracts import MockSmokeResponse
from medical_one_person.providers.base import (
    ModelUsage,
    ProviderCapabilities,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)


class FakeModelProvider:
    """Deterministic, network-free model substitute."""

    provider_id = "fake-deterministic-v1"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            mode="mock",
            structured_output=True,
            streaming=False,
            max_context_tokens=32_000,
        )

    def estimate_cost(self, request: StructuredGenerationRequest) -> Decimal | None:
        return Decimal("0")

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        if request.output_schema != "agent_delivery.v1":
            raise ValueError("Fake provider only supports agent_delivery.v1")
        input_fingerprint = hashlib.sha256(
            "\n".join(request.input_refs).encode("utf-8")
        ).hexdigest()[:12]
        evidence = [
            {
                "ref": ref,
                "source_kind": "fixture" if ref.startswith("fixture:") else "internal",
                "locator": None,
            }
            for ref in request.input_refs
        ]
        output = {
            "schema_version": "agent_delivery.v1",
            "mode": "mock",
            "role_id": request.role_id,
            "role_version": request.role_version,
            "project_id": str(request.project_id),
            "task_id": str(request.task_id),
            "delivery_type": request.delivery_type,
            "problem_statement": request.goal,
            "facts": [
                {
                    "statement": (
                        "Deterministic fake provider received the task and input references; "
                        "it did not verify a scientific fact."
                    ),
                    "status": "unknown",
                    "source_refs": request.input_refs,
                }
            ],
            "analysis": (
                f"Role {request.role_id} context was isolated and processed by the mock adapter "
                f"(input fingerprint {input_fingerprint})."
            ),
            "counterpoints": [
                "This deterministic mock output cannot support or refute a scientific claim."
            ],
            "unknowns": [
                "Source contents have not been read or scientifically reviewed.",
                "No real provider was called.",
            ],
            "recommendation": ("Use this output only as an interface and workflow test artifact."),
            "evidence_refs": evidence,
            "limitations": [
                "MOCK mode only.",
                "Not scientific evidence, professional advice, or external verification.",
            ],
            "independent_review": request.independent_context,
        }
        repair_tokens = len(request.repair_feedback or "")
        return StructuredGenerationResponse(
            provider_id=self.provider_id,
            model_id="fake-deterministic-v1",
            mode="mock",
            output=output,
            usage=ModelUsage(
                input_tokens=max(
                    1, sum(len(value) for value in request.context_sections.values()) // 4
                ),
                output_tokens=max(1, len(str(output)) // 4 + repair_tokens),
                estimated_cost=Decimal("0"),
                currency="USD",
            ),
            finish_reason="stop",
        )

    def smoke(self, value: str) -> MockSmokeResponse:
        fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        return MockSmokeResponse(
            provider_id=self.provider_id,
            output=f"已由模拟适配器接收输入（指纹 {fingerprint}）。",
            disclaimer="模拟响应，不代表真实模型、科学判断或外部执行。",
        )


class UnavailableLiveProvider:
    provider_id = "live-unconfigured"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            mode="live",
            structured_output=False,
            streaming=False,
            max_context_tokens=0,
        )

    def estimate_cost(self, request: StructuredGenerationRequest) -> Decimal | None:
        return None

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        raise RuntimeError("No reviewed live model provider is configured")

    def smoke(self, value: str) -> MockSmokeResponse:
        raise RuntimeError("Live provider is unavailable")

from __future__ import annotations

from pathlib import Path

import yaml

from medical_one_person.domain.exports import (
    ExportFormat,
    ExportTemplate,
    ExportTemplateCatalog,
)


class ExportTemplateRegistry:
    def __init__(self, templates: list[ExportTemplate]) -> None:
        self._by_format = {template.format: template for template in templates}

    @property
    def templates(self) -> list[ExportTemplate]:
        return [self._by_format[export_format] for export_format in ExportFormat]

    def default_for(self, export_format: ExportFormat) -> ExportTemplate:
        return self._by_format[export_format]

    def get(self, template_id: str, version: int) -> ExportTemplate:
        for template in self._by_format.values():
            if template.template_id == template_id and template.version == version:
                return template
        raise ValueError("Export template version is not registered")


def load_export_templates(path: Path) -> ExportTemplateRegistry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = ExportTemplateCatalog.model_validate(raw)
    return ExportTemplateRegistry(catalog.templates)

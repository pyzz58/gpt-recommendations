from __future__ import annotations

import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

from PIL import Image
from pypdf import PdfReader


class OfficeRendererError(Exception):
    pass


class OfficeRendererUnavailable(OfficeRendererError):
    pass


@dataclass(frozen=True)
class OfficeRuntimeStatus:
    status: str
    detail: str
    soffice_path: str | None
    pdftoppm_path: str | None
    versions: dict[str, str]


@dataclass(frozen=True)
class PdfPreview:
    pdf_bytes: bytes
    first_page_png: bytes
    page_count: int
    rendered_page_count: int
    blank_pages: list[int]
    minimum_content_ratio: float
    extracted_characters: int
    text_matches_expected: bool
    tool_version: str


class OfficeRenderer:
    def __init__(
        self,
        *,
        soffice_path: str | None = None,
        pdftoppm_path: str | None = None,
        timeout_seconds: int = 120,
        max_pages: int = 40,
    ) -> None:
        self._soffice = _resolve_executable(soffice_path or "soffice")
        self._pdftoppm = _resolve_executable(pdftoppm_path or "pdftoppm")
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages

    def status(self) -> OfficeRuntimeStatus:
        cjk_font = _find_cjk_font()
        versions = {
            package: _package_version(package)
            for package in (
                "python-docx",
                "python-pptx",
                "openpyxl",
                "reportlab",
                "pypdf",
                "Pillow",
            )
        }
        if cjk_font is not None:
            versions["cjk-font"] = str(cjk_font)
        if not self._soffice:
            return OfficeRuntimeStatus(
                status="unavailable",
                detail="LibreOffice headless command `soffice` is not installed or configured",
                soffice_path=None,
                pdftoppm_path=self._pdftoppm,
                versions=versions,
            )
        if not self._pdftoppm:
            return OfficeRuntimeStatus(
                status="unavailable",
                detail="Poppler `pdftoppm` is not installed or configured",
                soffice_path=self._soffice,
                pdftoppm_path=None,
                versions=versions,
            )
        if cjk_font is None:
            return OfficeRuntimeStatus(
                status="unavailable",
                detail=(
                    "No supported CJK TrueType font was found; Office previews would "
                    "omit Chinese text"
                ),
                soffice_path=self._soffice,
                pdftoppm_path=self._pdftoppm,
                versions=versions,
            )
        try:
            completed = subprocess.run(
                [self._soffice, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=_subprocess_environment(Path("/tmp"), configure_fonts=False),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return OfficeRuntimeStatus(
                status="unavailable",
                detail=f"Office runtime probe failed: {exc}",
                soffice_path=self._soffice,
                pdftoppm_path=self._pdftoppm,
                versions=versions,
            )
        soffice_version = " ".join(completed.stdout.strip().split())
        versions["libreoffice"] = soffice_version or "unknown"
        return OfficeRuntimeStatus(
            status="ready",
            detail=(
                "docx/pptx/xlsx can be converted to PDF and rendered; xlsx formulas "
                "can be recalculated by LibreOffice"
            ),
            soffice_path=self._soffice,
            pdftoppm_path=self._pdftoppm,
            versions=versions,
        )

    def recalculate_xlsx(self, source: Path, workdir: Path) -> Path:
        self._require_available(require_pdftoppm=False)
        return self._convert(
            source=source,
            workdir=workdir,
            target="xlsx",
            output_name="recalculated.xlsx",
            filter_name="Calc MS Excel 2007 XML",
        )

    def render_preview(
        self,
        source: Path,
        workdir: Path,
        *,
        expected_text: list[str],
    ) -> PdfPreview:
        self._require_available()
        workdir.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".pdf":
            preview_pdf = workdir / "preview.pdf"
            shutil.copy2(source, preview_pdf)
        else:
            preview_pdf = self._convert(
                source=source,
                workdir=workdir,
                target="pdf",
                output_name="preview.pdf",
                filter_name=None,
            )
        preview_bytes = preview_pdf.read_bytes()
        try:
            reader = PdfReader(preview_pdf)
            if reader.is_encrypted:
                raise OfficeRendererError("Rendered PDF is unexpectedly encrypted")
            page_count = len(reader.pages)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise OfficeRendererError("Rendered PDF cannot be opened") from exc
        if page_count < 1 or page_count > self._max_pages:
            raise OfficeRendererError(
                f"Rendered PDF page count {page_count} is outside 1-{self._max_pages}"
            )

        image_directory = workdir / "pages"
        image_directory.mkdir(parents=True, exist_ok=True)
        prefix = image_directory / "page"
        assert self._pdftoppm is not None
        try:
            subprocess.run(
                [
                    self._pdftoppm,
                    "-png",
                    "-r",
                    "72",
                    str(preview_pdf),
                    str(prefix),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                env=_subprocess_environment(workdir, configure_fonts=False),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise OfficeRendererError("PDF page rendering failed") from exc
        images = sorted(image_directory.glob("page-*.png"))
        if len(images) != page_count:
            raise OfficeRendererError(
                f"Rendered page count mismatch: PDF={page_count}, images={len(images)}"
            )

        ratios: list[float] = []
        blank_pages: list[int] = []
        for index, image_path in enumerate(images, start=1):
            with Image.open(image_path) as image:
                grayscale = image.convert("L")
                histogram = grayscale.histogram()
                pixel_count = max(1, grayscale.width * grayscale.height)
                non_white = sum(histogram[:250])
                ratio = non_white / pixel_count
            ratios.append(ratio)
            if ratio < 0.0005:
                blank_pages.append(index)
        if blank_pages:
            raise OfficeRendererError(f"Rendered blank pages: {blank_pages}")

        normalized_text = "".join(text.split())
        text_matches = all(
            "".join(expected.split()) in normalized_text
            for expected in expected_text
            if expected.strip()
        )
        if not text_matches:
            raise OfficeRendererError(
                "Rendered PDF text does not contain the report's required title or sections"
            )
        status = self.status()
        return PdfPreview(
            pdf_bytes=preview_bytes,
            first_page_png=images[0].read_bytes(),
            page_count=page_count,
            rendered_page_count=len(images),
            blank_pages=[],
            minimum_content_ratio=min(ratios),
            extracted_characters=len(text),
            text_matches_expected=text_matches,
            tool_version=status.versions.get("libreoffice", "unknown"),
        )

    def _convert(
        self,
        *,
        source: Path,
        workdir: Path,
        target: str,
        output_name: str,
        filter_name: str | None,
    ) -> Path:
        if not source.is_file():
            raise OfficeRendererError("Source document does not exist")
        conversion_dir = workdir / f"converted-{target}"
        profile_dir = workdir / "libreoffice-profile"
        conversion_dir.mkdir(parents=True, exist_ok=True)
        profile_dir.mkdir(parents=True, exist_ok=True)
        assert self._soffice is not None
        destination = (
            f"{target}:{filter_name}" if filter_name else target
        )
        command = [
            self._soffice,
            f"-env:UserInstallation=file://{quote(str(profile_dir.resolve()))}",
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            "--convert-to",
            destination,
            "--outdir",
            str(conversion_dir),
            str(source),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                env=_subprocess_environment(workdir, configure_fonts=True),
            )
        except subprocess.TimeoutExpired as exc:
            raise OfficeRendererError("LibreOffice conversion timed out") from exc
        except (OSError, subprocess.SubprocessError) as exc:
            raise OfficeRendererError("LibreOffice conversion failed") from exc

        candidates = sorted(
            conversion_dir.glob(f"*.{target}"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        if not candidates:
            raise OfficeRendererError("LibreOffice produced no output document")
        converted = candidates[0]
        if converted.stat().st_size == 0:
            raise OfficeRendererError("LibreOffice produced an empty output document")
        final_path = workdir / output_name
        shutil.copy2(converted, final_path)
        return final_path

    def _require_available(self, *, require_pdftoppm: bool = True) -> None:
        if not self._soffice:
            raise OfficeRendererUnavailable("LibreOffice headless is not configured")
        if require_pdftoppm and not self._pdftoppm:
            raise OfficeRendererUnavailable("Poppler pdftoppm is not configured")


def _subprocess_environment(
    workdir: Path,
    *,
    configure_fonts: bool,
) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
        if key in os.environ
    }
    environment["LANG"] = environment.get("LANG", "en_US.UTF-8")
    environment.update(
        {
            "HOME": str(workdir),
            "TMPDIR": str(workdir),
            "XDG_CACHE_HOME": str(workdir / "xdg-cache"),
            "XDG_CONFIG_HOME": str(workdir / "xdg-config"),
        }
    )
    if configure_fonts:
        environment["FONTCONFIG_FILE"] = str(_write_fontconfig(workdir))
    return environment


def _write_fontconfig(workdir: Path) -> Path:
    font_directories = [
        Path("/System/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
    ]
    available = [path for path in font_directories if path.is_dir()]
    cache_directory = workdir / "font-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    entries = "\n".join(
        f"  <dir>{xml_escape(str(path))}</dir>" for path in available
    )
    content = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
        "<fontconfig>\n"
        f"{entries}\n"
        f"  <cachedir>{xml_escape(str(cache_directory))}</cachedir>\n"
        "</fontconfig>\n"
    )
    target = workdir / "fonts.conf"
    target.write_text(content, encoding="utf-8")
    return target


def _find_cjk_font() -> Path | None:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "missing"


def _resolve_executable(command: str) -> str | None:
    candidate = Path(command)
    if candidate.is_absolute() or candidate.parent != Path("."):
        return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
    return shutil.which(command)


def almost_equal(first: float, second: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(first, second, rel_tol=tolerance, abs_tol=tolerance)

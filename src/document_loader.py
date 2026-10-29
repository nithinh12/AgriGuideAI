"""Document loading and text extraction for the AgriGuide knowledge base.

Responsibilities:
- discover source files under ``data/raw/`` (PDF and UTF-8 text),
- extract text with ``pypdf`` (page-level, with page numbers preserved),
- attach provenance metadata from ``data/raw/sources.jsonl`` (see
  ``data/README.md`` for the provenance schema).

Design notes:
- Extraction never fabricates content: pages that yield no extractable text
  (e.g. scanned images) are recorded with a warning and contribute no text.
- A document without a provenance entry is a hard error: the project spec
  requires every document to have recorded title/organization/URL details.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".txt"}


class ProvenanceError(ValueError):
    """Raised when a source file lacks a required provenance record."""


@dataclass(frozen=True)
class PageText:
    """Text extracted from one page of a document."""

    page_number: int  # 1-based
    text: str


@dataclass(frozen=True)
class Document:
    """A loaded source document with provenance attached."""

    doc_id: str
    title: str
    organization: str
    url: str
    language: str
    topics: tuple[str, ...]
    source_path: Path
    pages: tuple[PageText, ...] = field(default_factory=tuple)
    published_date: str | None = None
    retrieved_date: str | None = None
    license_notes: str | None = None
    warnings: tuple[str, ...] = ()

    @property
    def full_text(self) -> str:
        """All extracted page text joined with page separators."""
        return "\n\n".join(page.text for page in self.pages if page.text.strip())


def load_provenance(sources_file: Path) -> dict[str, dict]:
    """Load ``sources.jsonl`` into a ``doc_id -> metadata`` mapping.

    Each line must be a JSON object containing at least: doc_id, title,
    organization, url, language, topics, retrieved_date.
    """
    if not sources_file.exists():
        raise ProvenanceError(
            f"Provenance file not found: {sources_file}. "
            "Create it (see data/README.md) — every document must have provenance."
        )

    required = {"doc_id", "title", "organization", "url", "language", "retrieved_date"}
    registry: dict[str, dict] = {}
    with sources_file.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProvenanceError(
                    f"{sources_file}:{line_no}: invalid JSON — {exc}"
                ) from exc
            missing = required - record.keys()
            if missing:
                raise ProvenanceError(
                    f"{sources_file}:{line_no}: missing required fields {sorted(missing)}"
                )
            doc_id = str(record["doc_id"])
            if doc_id in registry:
                raise ProvenanceError(
                    f"{sources_file}:{line_no}: duplicate doc_id '{doc_id}'"
                )
            registry[doc_id] = record
    return registry


def _extract_pdf(
    source_path: Path, max_pages: int | None = None
) -> tuple[tuple[PageText, ...], tuple[str, ...]]:
    """Extract text page-by-page from a PDF.

    Returns ``(pages, warnings)``. Pages with no extractable text are dropped
    from ``pages`` and reported in ``warnings`` (typical for scanned PDFs).
    ``max_pages`` limits extraction to the first N pages (previews/tests).
    """
    warnings: list[str] = []
    pages: list[PageText] = []
    try:
        reader = PdfReader(str(source_path))
    except Exception as exc:  # pypdf raises various errors for corrupt files
        raise ValueError(f"Cannot open PDF {source_path}: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        # Some PDFs carry an empty user password; try that before giving up.
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError(f"PDF is encrypted and cannot be read: {source_path}") from exc

    for index, page in enumerate(reader.pages, start=1):
        if max_pages is not None and index > max_pages:
            break
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"page {index}: extraction failed ({exc})")
            continue
        text = text.strip()
        if not text:
            warnings.append(
                f"page {index}: no extractable text (likely a scanned image)"
            )
            continue
        pages.append(PageText(page_number=index, text=text))

    if not pages:
        warnings.append("no extractable text in the entire PDF")
    return tuple(pages), tuple(warnings)


def load_document(
    source_path: Path,
    provenance: dict[str, dict],
    max_pages: int | None = None,
) -> Document:
    """Load a single source file and attach its provenance record.

    ``provenance`` is the mapping returned by :func:`load_provenance`; the
    record is looked up by the file's stem (the file name without extension
    must equal the ``doc_id`` in ``sources.jsonl``).
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type '{source_path.suffix}' for {source_path} "
            f"(supported: {sorted(SUPPORTED_SUFFIXES)})"
        )

    doc_id = source_path.stem
    record = provenance.get(doc_id)
    if record is None:
        raise ProvenanceError(
            f"No provenance record for '{doc_id}' in sources.jsonl — "
            "every document must record title, organization, url, language, "
            "retrieved_date (see data/README.md)."
        )

    warnings: list[str] = []
    if source_path.suffix.lower() == ".pdf":
        pages, pdf_warnings = _extract_pdf(source_path, max_pages=max_pages)
        warnings.extend(pdf_warnings)
    else:  # .txt
        try:
            raw = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Text file is not valid UTF-8: {source_path}") from exc
        text = raw.strip()
        pages = (PageText(page_number=1, text=text),) if text else ()
        if not pages:
            warnings.append("text file is empty")

    if warnings:
        logger.warning("%s (%s): %s", doc_id, source_path.name, "; ".join(warnings))

    topics = record.get("topics") or []
    return Document(
        doc_id=doc_id,
        title=str(record["title"]),
        organization=str(record["organization"]),
        url=str(record["url"]),
        language=str(record["language"]).lower(),
        topics=tuple(str(t) for t in topics),
        source_path=source_path,
        pages=pages,
        published_date=record.get("published_date"),
        retrieved_date=str(record["retrieved_date"]),
        license_notes=record.get("license_notes"),
        warnings=tuple(warnings),
    )


def load_all_documents(raw_dir: Path) -> list[Document]:
    """Load every supported source file in ``raw_dir`` (provenance required).

    Files whose stem is not registered in ``sources.jsonl`` raise
    :class:`ProvenanceError` — silently skipping them would hide untracked
    sources, which the project spec forbids.
    """
    sources_file = raw_dir / "sources.jsonl"
    provenance = load_provenance(sources_file)

    source_paths = sorted(
        path
        for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    documents = [load_document(path, provenance) for path in source_paths]

    # Warn about provenance entries that point to missing files (typos etc.).
    known_stems = {path.stem for path in source_paths}
    for doc_id in sorted(set(provenance) - known_stems):
        logger.warning(
            "sources.jsonl entry '%s' has no matching file in %s", doc_id, raw_dir
        )
    return documents

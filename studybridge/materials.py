"""Bounded text extraction with page-level source identifiers."""
from __future__ import annotations

from io import BytesIO
from pypdf import PdfReader

MAX_BYTES = 8 * 1024 * 1024
MAX_CHARS = 40_000


def extract_file(name: str, content: bytes) -> list[dict]:
    if len(content) > MAX_BYTES:
        raise ValueError("Each file must be smaller than 8 MB.")
    pages = []
    if name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("Upload an unencrypted PDF.")
            if len(reader.pages) > 35:
                raise ValueError("Use a focused PDF of 35 pages or fewer.")
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"id": f"{name}::page-{i}", "name": name, "page": i, "text": text})
        except ValueError:
            raise
        except Exception:
            raise ValueError("This PDF could not be read. Try a text-based PDF or paste the text.") from None
    elif name.lower().endswith((".txt", ".md")):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Save text files using UTF-8 encoding.") from None
        pages = [{"id": f"{name}::page-1", "name": name, "page": 1, "text": text}]
    else:
        raise ValueError("Supported formats: PDF, TXT, and Markdown.")
    if not pages or not any(p["text"].strip() for p in pages):
        raise ValueError("No readable text was found. Scanned PDFs need OCR first; you can also paste the text.")
    if sum(len(p["text"]) for p in pages) > MAX_CHARS:
        raise ValueError("This file exceeds 40,000 characters. Upload a smaller section.")
    return pages


def pasted_pages(text: str, name="Pasted notes") -> list[dict]:
    if not 20 <= len(text.strip()) <= MAX_CHARS:
        raise ValueError("Paste between 20 and 40,000 characters.")
    return [{"id": f"{name}::page-1", "name": name, "page": 1, "text": text.strip()}]


def collect_materials(files, text: str, name="Pasted notes") -> list[dict]:
    pages = []
    for file in files or []:
        pages.extend(extract_file(file.name, file.getvalue()))
    if text.strip():
        pages.extend(pasted_pages(text, name))
    if not pages:
        raise ValueError("Upload a document or paste some course material first.")
    if len(pages) > 50 or sum(len(p["text"]) for p in pages) > MAX_CHARS:
        raise ValueError("Keep a course import under 50 readable pages and 40,000 characters.")
    ids = [p["id"] for p in pages]
    if len(ids) != len(set(ids)):
        raise ValueError("File names must be unique in an import.")
    return pages


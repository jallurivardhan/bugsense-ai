import os
from typing import Optional
from pathlib import Path

# PDF processing
try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency
    PdfReader = None

# DOCX processing
try:
    from docx import Document as DocxDocument
except ImportError:  # pragma: no cover - optional dependency
    DocxDocument = None


class DocumentProcessor:
    """Extract text content from various document formats."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

    def extract_text(self, file_path: str) -> Optional[str]:
        """Extract text from a document file."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        if extension in {".txt", ".md"}:
            return self._extract_text_file(file_path)
        if extension == ".pdf":
            return self._extract_pdf(file_path)
        if extension == ".docx":
            return self._extract_docx(file_path)

        return None

    def _extract_text_file(self, file_path: str) -> str:
        """Extract text from plain text files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF files."""
        if PdfReader is None:
            raise ImportError("pypdf is required for PDF processing")

        reader = PdfReader(file_path)
        text_parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX files."""
        if DocxDocument is None:
            raise ImportError("python-docx is required for DOCX processing")

        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)


document_processor = DocumentProcessor()


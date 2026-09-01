"""
Document Parser Service
Extracts text from PDF files using pdfplumber.
"""
import pdfplumber
from pathlib import Path


class DocumentParser:
    """Parses PDF documents and extracts text content."""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """
        Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text as a single string with page break markers
        """
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                if i < len(pdf.pages) - 1:
                    text_parts.append("\n---PAGE BREAK---\n")
        return "\n".join(text_parts)

    @staticmethod
    def parse_document(file_path: str) -> str:
        """
        Route to appropriate parser based on file extension.

        Args:
            file_path: Path to the document

        Returns:
            Extracted text

        Raises:
            ValueError: If file format is not supported
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return DocumentParser.parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Get basic statistics about extracted text."""
        words = text.split()
        return {
            "characters": len(text),
            "words": len(words),
            "lines": text.count("\n") + 1,
            "pages": text.count("---PAGE BREAK---") + 1,
        }

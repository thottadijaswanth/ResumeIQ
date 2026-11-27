import os
from typing import Tuple
from backend.app.config import settings
from backend.app.document_processing.pdf_parser import PDFParser
from backend.app.document_processing.docx_parser import DOCXParser


class DocumentParser:
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes

    @classmethod
    def validate_file(cls, filename: str, file_size: int, content_type: str = "") -> str:
        """
        Validate file extension, size, and return normalized file type ('pdf' or 'docx').
        """
        if file_size > cls.MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB (received {file_size / (1024 * 1024):.2f}MB)"
            )

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '.{ext}'. Allowed types are: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        return ext

    @classmethod
    def parse_document(cls, filename: str, file_bytes: bytes, content_type: str = "") -> Tuple[str, str]:
        """
        Parse uploaded document bytes into clean text.
        Returns (extracted_text, file_type).
        """
        file_type = cls.validate_file(filename, len(file_bytes), content_type)

        if file_type == "pdf":
            text = PDFParser.extract_text(file_bytes)
        elif file_type == "docx":
            text = DOCXParser.extract_text(file_bytes)
        else:
            raise ValueError(f"No parser available for type: {file_type}")

        return text, file_type


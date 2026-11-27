import io
from docx import Document
from backend.app.document_processing.normalizer import TextNormalizer


class DOCXParser:
    @staticmethod
    def extract_text(file_bytes: bytes) -> str:
        """
        Extract clean text from DOCX bytes using python-docx.
        Extracts both regular paragraphs and table cells.
        """
        if not file_bytes:
            raise ValueError("The uploaded DOCX file is empty (0 bytes).")

        try:
            file_stream = io.BytesIO(file_bytes)
            doc = Document(file_stream)
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX file. File may be corrupted. Details: {str(e)}")

        extracted_parts = []

        # Extract text from paragraphs
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                extracted_parts.append(text)

        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    extracted_parts.append(" | ".join(row_cells))

        combined_text = "\n".join(extracted_parts).strip()
        if not combined_text or len(combined_text) < 20:
            raise ValueError("The DOCX file does not contain sufficient readable text.")

        return TextNormalizer.normalize_whitespace(combined_text)


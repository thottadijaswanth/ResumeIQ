import fitz  # PyMuPDF
from backend.app.document_processing.normalizer import TextNormalizer


class PDFParser:
    @staticmethod
    def extract_text(file_bytes: bytes) -> str:
        """
        Extract clean text from PDF bytes using PyMuPDF.
        Raises ValueError for empty, corrupt, or scanned PDFs without text.
        """
        if not file_bytes:
            raise ValueError("The uploaded PDF file is empty (0 bytes).")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to parse PDF file. The file may be corrupt or encrypted. Details: {str(e)}")

        if doc.is_encrypted:
            raise ValueError("The PDF is encrypted or password-protected. Please upload an unlocked PDF.")

        if doc.page_count == 0:
            doc.close()
            raise ValueError("The PDF file contains 0 pages.")

        extracted_pages = []
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            page_text = page.get_text("text")
            if page_text:
                extracted_pages.append(page_text)

        doc.close()
        combined_text = "\n\n".join(extracted_pages).strip()

        if not combined_text or len(combined_text) < 20:
            raise ValueError(
                "Could not extract sufficient text from this PDF. "
                "The PDF might be a scanned image without selectable text (OCR required) or blank."
            )

        return TextNormalizer.normalize_whitespace(combined_text)


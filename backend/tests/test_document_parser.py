import pytest
import io
import fitz
from docx import Document
from backend.app.document_processing import DocumentParser, PDFParser, DOCXParser


def test_pdf_extraction_valid():
    # Create valid synthetic PDF bytes using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Alex Morgan\nSenior Python Backend Engineer\nSkills: Python, FastAPI, Docker, PostgreSQL")
    pdf_bytes = doc.tobytes()
    doc.close()

    text = PDFParser.extract_text(pdf_bytes)
    assert "Alex Morgan" in text
    assert "FastAPI" in text
    assert "PostgreSQL" in text


def test_pdf_extraction_empty_fails():
    with pytest.raises(ValueError, match="0 bytes"):
        PDFParser.extract_text(b"")


def test_docx_extraction_valid():
    # Create valid synthetic DOCX bytes
    doc = Document()
    doc.add_heading("Taylor Reed - Software Engineer", level=1)
    doc.add_paragraph("Proficient in React, TypeScript, and AWS cloud deployments.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Experience: 4 years"
    table.rows[0].cells[1].text = "Education: B.S. CS"

    stream = io.BytesIO()
    doc.save(stream)
    docx_bytes = stream.getvalue()

    text = DOCXParser.extract_text(docx_bytes)
    assert "Taylor Reed" in text
    assert "TypeScript" in text
    assert "AWS" in text


def test_document_parser_invalid_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentParser.validate_file("resume.txt", 100)


def test_document_parser_file_size_limit():
    with pytest.raises(ValueError, match="File size exceeds limit"):
        DocumentParser.validate_file("resume.pdf", 6 * 1024 * 1024)


from pathlib import Path

from app.models import FileType
from app.services.document_processor import document_processor
from app.services.text_utils import sanitize_document_text

SAMPLE_PDF = Path(__file__).resolve().parent.parent / "sample_docs" / "pipeline_test.pdf"


def test_pdf_extraction_uses_pdf_tooling():
    content, metadata = document_processor.extract_text_content(SAMPLE_PDF, FileType.PDF)

    assert metadata.get("success") is True, f"metadata indicates failure: {metadata}"
    assert metadata.get("extraction_method") in {"pymupdf", "pypdf"}, metadata
    assert "Hallo Welt" in content, "Expected German test text missing from extracted content"


def test_sanitized_pdf_text_available_for_llm_prompt():
    raw_content, metadata = document_processor.extract_text_content(SAMPLE_PDF, FileType.PDF)
    assert metadata.get("success") is True

    sanitized = sanitize_document_text(raw_content)
    assert "Hallo Welt" in sanitized

    user_prompt = "Bitte fassen Sie das Dokument zusammen."
    llm_prompt = f"{user_prompt}\n\nDokumentinhalt:\n{sanitized}"

    def fake_llm(prompt: str) -> str:
        assert "Hallo Welt" in prompt, "LLM prompt did not receive the PDF content"
        return "Zusammenfassung: Das Dokument beginnt mit 'Hallo Welt'."

    response = fake_llm(llm_prompt)
    assert "Zusammenfassung" in response and "Hallo Welt" in response

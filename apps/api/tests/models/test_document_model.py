"""Tests for Document model column definitions."""

from sqlalchemy import Text, inspect

from app.models.document import Document


def test_document_has_extracted_text_column():
    """Document model must have a nullable Text column for extracted text."""
    mapper = inspect(Document)
    assert "extracted_text" in mapper.columns
    col = mapper.columns["extracted_text"]
    assert col.nullable is True
    assert isinstance(col.type, Text)


def test_document_has_error_message_column():
    """Document model must have a nullable Text column for error messages."""
    mapper = inspect(Document)
    assert "error_message" in mapper.columns
    col = mapper.columns["error_message"]
    assert col.nullable is True
    assert isinstance(col.type, Text)

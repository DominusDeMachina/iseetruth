"""Test that document upload enqueues a Celery task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_investigation_service():
    with patch("app.services.document.InvestigationService") as mock_cls:
        mock_service = AsyncMock()
        mock_cls.return_value = mock_service
        mock_service.get_investigation = AsyncMock()
        yield mock_service


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    return session


@pytest.mark.asyncio
async def test_upload_enqueues_celery_task(
    mock_db, mock_investigation_service, tmp_path
):
    """After upload, process_document_task.delay should be called."""
    from app.services.document import DocumentService

    mock_file = MagicMock()
    mock_file.filename = "test.pdf"
    mock_file.read = AsyncMock(side_effect=[b"%PDF-1.4 content", b""])
    mock_file.seek = AsyncMock()

    inv_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    mock_task = MagicMock()

    with (
        patch("app.services.document.STORAGE_ROOT", tmp_path),
        patch("app.services.document.asyncio") as mock_asyncio,
        patch.dict(
            "sys.modules",
            {
                "app.worker.tasks.process_document": MagicMock(
                    process_document_task=mock_task
                )
            },
        ),
    ):
        mock_asyncio.to_thread = AsyncMock(return_value=5)

        service = DocumentService(mock_db)
        doc = await service.upload_document(inv_id, mock_file)

        # Verify task.delay was called with correct arguments
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0]
        assert call_args[1] == str(inv_id)

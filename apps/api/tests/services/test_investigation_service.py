"""Unit tests for InvestigationService business logic."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.investigation import Investigation
from app.schemas.investigation import InvestigationCreate
from app.services.investigation import InvestigationNotFoundError, InvestigationService


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    # session.add() is synchronous in SQLAlchemy — override to avoid coroutine warning
    db.add = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create InvestigationService with mocked DB."""
    return InvestigationService(mock_db)


@pytest.fixture
def sample_uuid():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def sample_investigation(sample_uuid):
    """Return a mock Investigation ORM object."""
    inv = MagicMock(spec=Investigation)
    inv.id = sample_uuid
    inv.name = "Test Investigation"
    inv.description = "A test description"
    inv.created_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    inv.updated_at = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
    return inv


# ---------------------------------------------------------------------------
# create_investigation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_investigation_persists_to_db(service, mock_db, tmp_path):
    """create_investigation should add to session, commit, and refresh."""
    data = InvestigationCreate(name="Test", description="Desc")
    sample_id = uuid.uuid4()

    async def fake_refresh(obj):
        obj.id = sample_id
        obj.name = data.name
        obj.description = data.description
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_db.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("app.services.investigation.STORAGE_ROOT", tmp_path):
        result = await service.create_investigation(data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
    assert isinstance(result, Investigation)


@pytest.mark.asyncio
async def test_create_investigation_creates_storage_dir(service, mock_db, tmp_path):
    """create_investigation should create storage/{id}/ directory on disk."""
    data = InvestigationCreate(name="Test")
    sample_id = uuid.uuid4()

    async def fake_refresh(obj):
        obj.id = sample_id
        obj.name = data.name
        obj.description = data.description
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_db.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("app.services.investigation.STORAGE_ROOT", tmp_path):
        await service.create_investigation(data)

    assert (tmp_path / str(sample_id)).is_dir()


# ---------------------------------------------------------------------------
# list_investigations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_investigations_returns_paginated_results(service, mock_db):
    """list_investigations should query count + paginated list."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 5

    inv1 = MagicMock(spec=Investigation)
    inv2 = MagicMock(spec=Investigation)
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [inv1, inv2]

    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

    investigations, total = await service.list_investigations(limit=10, offset=0)

    assert total == 5
    assert len(investigations) == 2
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_investigations_default_params(service, mock_db):
    """list_investigations should use default limit=50, offset=0."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[count_result, list_result])

    investigations, total = await service.list_investigations()

    assert total == 0
    assert investigations == []


# ---------------------------------------------------------------------------
# get_investigation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_investigation_returns_found(service, mock_db, sample_uuid):
    """get_investigation should return investigation when found."""
    inv = MagicMock(spec=Investigation)
    inv.id = sample_uuid
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inv

    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_investigation(sample_uuid)

    assert result.id == sample_uuid


@pytest.mark.asyncio
async def test_get_investigation_raises_not_found(service, mock_db, sample_uuid):
    """get_investigation should raise InvestigationNotFoundError when not found."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(InvestigationNotFoundError) as exc_info:
        await service.get_investigation(sample_uuid)

    assert str(sample_uuid) in str(exc_info.value)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_investigation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_investigation_removes_storage_and_db(
    service, mock_db, tmp_path, sample_uuid
):
    """delete_investigation should delete storage dir then DB record."""
    inv = MagicMock(spec=Investigation)
    inv.id = sample_uuid
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inv
    mock_db.execute = AsyncMock(return_value=result_mock)

    storage_dir = tmp_path / str(sample_uuid)
    storage_dir.mkdir()
    assert storage_dir.exists()

    with patch("app.services.investigation.STORAGE_ROOT", tmp_path):
        await service.delete_investigation(sample_uuid)

    assert not storage_dir.exists()
    mock_db.delete.assert_awaited_once_with(inv)
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_investigation_succeeds_without_storage_dir(
    service, mock_db, tmp_path, sample_uuid
):
    """delete_investigation should succeed even if storage dir doesn't exist."""
    inv = MagicMock(spec=Investigation)
    inv.id = sample_uuid
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inv
    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch("app.services.investigation.STORAGE_ROOT", tmp_path):
        await service.delete_investigation(sample_uuid)

    mock_db.delete.assert_awaited_once_with(inv)
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_investigation_not_found(service, mock_db, sample_uuid):
    """delete_investigation should raise NotFound if investigation doesn't exist."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(InvestigationNotFoundError):
        await service.delete_investigation(sample_uuid)

    mock_db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_investigation_continues_on_filesystem_error(
    service, mock_db, tmp_path, sample_uuid
):
    """delete_investigation should continue to DB delete even if filesystem cleanup fails."""
    inv = MagicMock(spec=Investigation)
    inv.id = sample_uuid
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inv
    mock_db.execute = AsyncMock(return_value=result_mock)

    (tmp_path / str(sample_uuid)).mkdir()

    with (
        patch("app.services.investigation.STORAGE_ROOT", tmp_path),
        patch("shutil.rmtree", side_effect=OSError("Permission denied")),
    ):
        await service.delete_investigation(sample_uuid)

    # DB delete should still happen despite filesystem error
    mock_db.delete.assert_awaited_once_with(inv)
    mock_db.commit.assert_awaited()

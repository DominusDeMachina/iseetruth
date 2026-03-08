"""Integration tests for /api/v1/investigations/ endpoints."""

import uuid

from app.services.investigation import InvestigationNotFoundError


def test_create_investigation_returns_201(
    investigation_client, mock_investigation_service
):
    response = investigation_client.post(
        "/api/v1/investigations/",
        json={"name": "Test Investigation", "description": "A test investigation"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Investigation"
    assert data["description"] == "A test investigation"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["document_count"] == 0
    assert data["entity_count"] == 0
    mock_investigation_service.create_investigation.assert_called_once()


def test_create_investigation_name_required(
    investigation_client, mock_investigation_service
):
    response = investigation_client.post(
        "/api/v1/investigations/",
        json={"description": "No name provided"},
    )
    assert response.status_code == 422


def test_create_investigation_empty_name_rejected(
    investigation_client, mock_investigation_service
):
    response = investigation_client.post(
        "/api/v1/investigations/",
        json={"name": "", "description": "Empty name"},
    )
    assert response.status_code == 422


def test_list_investigations_returns_200(
    investigation_client, mock_investigation_service
):
    response = investigation_client.get("/api/v1/investigations/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Test Investigation"


def test_list_investigations_with_pagination(
    investigation_client, mock_investigation_service
):
    response = investigation_client.get(
        "/api/v1/investigations/?limit=10&offset=5"
    )
    assert response.status_code == 200
    mock_investigation_service.list_investigations.assert_called_once_with(10, 5)


def test_get_investigation_returns_200(
    investigation_client, mock_investigation_service, sample_investigation_id
):
    response = investigation_client.get(
        f"/api/v1/investigations/{sample_investigation_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Investigation"
    assert data["id"] == str(sample_investigation_id)


def test_get_investigation_not_found_returns_404(
    investigation_client, mock_investigation_service
):
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_investigation_service.get_investigation.side_effect = (
        InvestigationNotFoundError(not_found_id)
    )
    response = investigation_client.get(
        f"/api/v1/investigations/{not_found_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:investigation_not_found"
    assert data["title"] == "Investigation Not Found"
    assert data["status"] == 404


def test_delete_investigation_returns_204(
    investigation_client, mock_investigation_service, sample_investigation_id
):
    response = investigation_client.delete(
        f"/api/v1/investigations/{sample_investigation_id}"
    )
    assert response.status_code == 204
    mock_investigation_service.delete_investigation.assert_called_once_with(
        sample_investigation_id
    )


def test_delete_investigation_not_found_returns_404(
    investigation_client, mock_investigation_service
):
    not_found_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    mock_investigation_service.delete_investigation.side_effect = (
        InvestigationNotFoundError(not_found_id)
    )
    response = investigation_client.delete(
        f"/api/v1/investigations/{not_found_id}"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "urn:osint:error:investigation_not_found"


def test_invalid_uuid_returns_422(investigation_client, mock_investigation_service):
    response = investigation_client.get("/api/v1/investigations/not-a-uuid")
    assert response.status_code == 422

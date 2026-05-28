"""Tests for /api/v1/contracts endpoints: list, upload, draft, review, export, delete."""

import pytest


@pytest.mark.asyncio
async def test_list_contracts_empty(client, auth_headers):
    """Listing contracts when none exist should return an empty list."""
    response = await client.get("/api/v1/contracts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "x-total-count" in response.headers


@pytest.mark.asyncio
async def test_get_nonexistent_contract(client, auth_headers):
    """Getting a non-existent contract should return 404."""
    response = await client.get("/api/v1/contracts/999999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_contract(client, auth_headers):
    """Deleting a non-existent contract should return 404."""
    response = await client.delete("/api/v1/contracts/999999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_contracts_unauthenticated(client):
    """Listing contracts without auth should return 401."""
    response = await client.get("/api/v1/contracts")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_contract_no_file(client, auth_headers):
    """Uploading a contract without a file should fail validation."""
    response = await client.post(
        "/api/v1/contracts/upload",
        headers=auth_headers,
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_review_nonexistent_contract(client, auth_headers):
    """Reviewing a non-existent contract should return 404."""
    response = await client.post(
        "/api/v1/contracts/999999/review",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_nonexistent_contract(client, auth_headers):
    """Exporting a non-existent contract should return 404."""
    response = await client.post(
        "/api/v1/contracts/999999/export",
        headers=auth_headers,
        json={"format": "markdown"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_contracts_with_case_filter(client, auth_headers):
    """Listing contracts with case_id filter should work."""
    response = await client.get(
        "/api/v1/contracts?case_id=1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "x-total-count" in response.headers

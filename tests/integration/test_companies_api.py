"""Integration tests for the Company API endpoints."""

from __future__ import annotations

import io
from typing import Any
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import FastAPI
from core.models.company import Company


@pytest.fixture(autouse=True)
def override_db_dependency(app: FastAPI, db_session: AsyncSession) -> None:
    from api.deps import get_session
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_company_api_flow(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """
    Test the full API flow:
    1. GET /api/v1/companies (empty)
    2. POST /api/v1/companies/discover (find & save companies)
    3. GET /api/v1/companies (populated)
    4. POST /api/v1/companies/discover/csv (upload and save CSV companies)
    """
    # 1. GET /api/v1/companies -> verify starts empty
    response = await async_client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

    # 2. POST /api/v1/companies/discover -> run discover
    discover_payload = {
        "industry": "AI",
        "location": "New York",
        "limit": 10
    }
    response = await async_client.post("/api/v1/companies/discover", json=discover_payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    assert len(res_data["data"]["companies"]) > 0
    assert res_data["data"]["new_count"] > 0

    # 3. GET /api/v1/companies -> verify returns the saved companies
    response = await async_client.get("/api/v1/companies")
    assert response.status_code == 200
    list_data = response.json()
    assert list_data["total"] > 0
    assert len(list_data["items"]) == list_data["total"]
    
    first_company = list_data["items"][0]
    assert "id" in first_company
    assert "name" in first_company
    assert "website" in first_company
    assert "source" in first_company

    # 4. POST /api/v1/companies/discover/csv -> upload a CSV file
    csv_file_content = (
        "Name,Website,LinkedIn,Industry,Location\n"
        "CSV Corp,https://csv-corp.com,https://linkedin.com/company/csv-corp,Tech,San Francisco\n"
    )
    
    files = {"file": ("companies.csv", io.BytesIO(csv_file_content.encode("utf-8")), "text/csv")}
    
    response = await async_client.post("/api/v1/companies/discover/csv", files=files)
    assert response.status_code == 201
    csv_res = response.json()
    assert csv_res["success"] is True
    assert len(csv_res["data"]["companies"]) == 1
    assert csv_res["data"]["companies"][0]["name"] == "CSV Corp"
    assert csv_res["data"]["companies"][0]["domain"] == "csv-corp.com"

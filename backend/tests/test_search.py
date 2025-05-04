import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app
from backend.models.search_models import CompanyInfo, CompanySearchByPersonResponse, CompanySearchByNameResponse

client = TestClient(app)

# Mock data for testing
mock_company_data = {
    "12345678": {
        "ico": "12345678",
        "name": "Test Company",
        "address": "Test Address 123",
        "established_date": "2020-01-01",
        "legal_form": "s.r.o.",
        "status": "active"
    }
}

mock_search_result = {
    "data": mock_company_data,
    "count": 1
}

# Helper function to get auth token
def get_auth_token():
    response = client.post(
        "/auth/token",
        data={"username": "honza@email.com", "password": "123456789"}
    )
    return response.json().get("access_token")


@pytest.fixture
def auth_headers():
    token = get_auth_token()
    return {"Authorization": f"Bearer {token}"}


# Test search by person endpoint
@patch("backend.routes.search.get_companies_from_name_person")
def test_search_by_person(mock_get_companies, auth_headers):
    # Setup mock
    mock_get_companies.return_value = mock_search_result
    
    # Make request
    response = client.get(
        "/search/person?first_name=Jan&last_name=Novak",
        headers=auth_headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert "count" in data
    assert data["count"] == 1
    assert "12345678" in data["companies"]
    
    # Verify mock was called with correct parameters
    mock_get_companies.assert_called_once_with("Jan", "Novak")


# Test search by company name endpoint
@patch("backend.routes.search.get_companies_from_name_company")
def test_search_by_company_name(mock_get_companies, auth_headers):
    # Setup mock
    mock_get_companies.return_value = mock_search_result
    
    # Make request
    response = client.get(
        "/search/company?company_name=Test%20Company",
        headers=auth_headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert "count" in data
    assert data["count"] == 1
    assert "12345678" in data["companies"]
    
    # Verify mock was called with correct parameters
    mock_get_companies.assert_called_once_with("Test Company")


# Test search by ICO endpoint
@patch("backend.routes.search.get_companies_from_ico")
def test_search_by_ico(mock_get_companies, auth_headers):
    # Setup mock
    mock_get_companies.return_value = mock_search_result
    
    # Make request
    response = client.get(
        "/search/ico?ico=12345678",
        headers=auth_headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["ico"] == "12345678"
    assert data["name"] == "Test Company"
    
    # Verify mock was called with correct parameters
    mock_get_companies.assert_called_once_with(12345678)


# Test unauthorized access
def test_unauthorized_access():
    # Try to access without auth token
    endpoints = [
        "/search/person?first_name=Jan&last_name=Novak",
        "/search/company?company_name=Test%20Company",
        "/search/ico?ico=12345678"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401
        assert "detail" in response.json()
        assert response.json()["detail"] == "Not authenticated"


# Test error handling
@patch("backend.routes.search.get_companies_from_ico")
def test_error_handling(mock_get_companies, auth_headers):
    # Setup mock to raise exception
    mock_get_companies.side_effect = Exception("Test error")
    
    # Make request
    response = client.get(
        "/search/ico?ico=12345678",
        headers=auth_headers
    )
    
    # Assertions
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "An error occurred" in response.json()["detail"]


# Test network failure
@patch("backend.routes.search.get_companies_from_name_person")
def test_network_failure(mock_get_companies, auth_headers):
    # Setup mock to simulate network failure
    mock_get_companies.side_effect = ConnectionError("Network unavailable")
    
    # Make request
    response = client.get("/search/person?first_name=Jan&last_name=Novak", headers=auth_headers)
    
    # Assertions
    assert response.status_code == 503  # Service Unavailable

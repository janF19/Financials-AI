import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Assuming your FastAPI app instance is in backend.main
from backend.main import app
from backend.config.settings import settings
from backend.database import supabase # Import the global client to mock it

# Override settings for testing if necessary
settings.DEBUG = True # Example override

@pytest.fixture(scope="module")
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True) # Automatically use this fixture for all tests
def mock_supabase():
    """Mocks the global supabase client."""
    mock_client = MagicMock()

    # --- Mock specific behaviors as needed ---
    # Example: Mock user lookup for authentication
    mock_user_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()

    # Chain the mocks: table('users').select('*').eq('id', ...).execute()
    mock_client.table.return_value = mock_user_table
    mock_user_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    # Configure execute() to return different results based on test needs
    mock_eq.execute.return_value = MagicMock(data=[{
        "id": "test-user-uuid",
        "email": "test@example.com",
        "password_hash": "$2b$12$...", # A valid bcrypt hash for testing
        "created_at": "2023-01-01T12:00:00Z"
    }]) # Example return value

    # Example: Mock storage upload
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = MagicMock(status_code=200) # Simulate success
    mock_bucket.get_public_url.return_value = "http://mock-storage.com/reports/test-user-uuid/report.docx"
    mock_bucket.remove.return_value = MagicMock(data=[]) # Simulate success

    # Example: Mock report insert
    mock_report_table = MagicMock()
    mock_client.table.side_effect = lambda table_name: mock_report_table if table_name == "reports" else mock_user_table
    mock_report_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "new-report-uuid"}])
    # --- End Mock specific behaviors ---

    # Patch the actual supabase client instance used by your application
    with patch('backend.database.supabase', mock_client), \
         patch('backend.routes.auth.supabase', mock_client), \
         patch('backend.routes.financials.supabase', mock_client), \
         patch('backend.routes.reports.supabase', mock_client), \
         patch('backend.routes.dashboard.supabase', mock_client), \
         patch('backend.routes.health.supabase', mock_client), \
         patch('backend.auth.dependencies.supabase', mock_client), \
         patch('backend.storage.report_archive.supabase', mock_client), \
         patch('backend.processors.workflow.supabase', mock_client): # Patch wherever it's imported
        yield mock_client # Provide the mock for potential direct assertions in tests

# Fixture for a test user's token
@pytest.fixture
def auth_token(client: TestClient, mock_supabase):
    # You might need to adjust the mock_supabase setup for login success
    # Or directly mock create_access_token if login logic is complex
    # Here, we assume get_current_user relies on the mocked supabase lookup
    # We just need a plausible token string for the header
    # In a real scenario, you might call the /auth/token endpoint
    # or directly call create_access_token
    from backend.auth.dependencies import create_access_token
    # Use the user ID mocked in mock_supabase
    user_id_from_mock = mock_supabase.table().select().eq().execute().data[0]["id"]
    token = create_access_token(user_id=user_id_from_mock)
    return {"Authorization": f"Bearer {token}"}
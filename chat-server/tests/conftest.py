import sys
from unittest.mock import Mock

import pytest

mock_session = Mock()
mock_session.get_aiohttp_client.return_value = Mock()
mock_session.SingletonAiohttp = Mock()
mock_session.SingletonAiohttp.get_aiohttp_client.return_value = Mock()

sys.modules["app.core.session"] = mock_session

def pytest_addoption(parser):
    parser.addoption(
        "--disable-formatter",
        action="store_true",
        default=False,
        help="Disable terminal formatter output for cleaner pytest output"
    )

@pytest.fixture
def sample_metadata():
    return {
        "user": "test_user",
        "trace_id": "test_trace_123",
        "chat_id": "test_chat_456",
    }


@pytest.fixture
def mock_settings():
    return Mock(
        QDRANT_COLLECTION="test_collection",
        QDRANT_TOP_K=5,
        DEFAULT_VENDOR="openai",
        DEFAULT_OPENAI_MODEL="gpt-4",
        DEFAULT_GEMINI_MODEL="gemini-pro",
        DEFAULT_EMBEDDING_MODEL="text-embedding-ada-002",
        GATEWAY_PROVIDER="portkey_hosted",
        PORTKEY_API_KEY="test_key",
        OPENAI_VIRTUAL_KEY="test_virtual_key",
        GEMINI_VIRTUAL_KEY="test_gemini_key",
        LITELLM_MASTER_KEY="test_master_key",
        LITELLM_BASE_URL="http://localhost:4000",
        LANGSMITH_PROMPT=False,
    )


@pytest.fixture
def mock_vector_store():
    return Mock(
        add_documents=Mock(),
        similarity_search=Mock(return_value=[]),
    )


@pytest.fixture
def mock_qdrant_client():
    return Mock(
        scroll=Mock(return_value=([],)),
        search=Mock(return_value=[]),
    )


@pytest.fixture
def mock_embeddings():
    return Mock(
        embed_query=Mock(return_value=[0.1, 0.2, 0.3]),
        embed_documents=Mock(return_value=[[0.1, 0.2, 0.3]]),
    )


@pytest.fixture
def sample_dataset_schema():
    return {
        "dataset_name": "test_dataset",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "string"},
            {"name": "value", "type": "float"},
        ],
        "sample_data": [
            {"id": 1, "name": "test1", "value": 10.5},
            {"id": 2, "name": "test2", "value": 20.3},
        ],
    }


@pytest.fixture
def sample_query_request():
    return {
        "messages": [{"role": "user", "content": "Show me the sales data"}],
        "model": "gpt-4",
        "user": "test_user",
        "metadata": {"project_id_1": "proj1,proj2", "dataset_id_1": "ds1,ds2"},
    }

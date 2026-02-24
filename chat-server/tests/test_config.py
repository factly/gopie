"""
Test Configuration Module

This module provides configuration settings for all test suites.
Values can be overridden via environment variables.

Environment Variables:
    GOPIE_API_URL          - Gopie API server URL (default: http://localhost:8000)
    CHAT_SERVER_URL        - Chat server endpoint (default: http://localhost:8001/api/v1/chat/completions)
    GOPIE_USER_ID          - Gopie user ID for API requests (default: system)
    GOPIE_ORG_ID           - Gopie organization ID (default: 123)
    S3_ENDPOINT_URL        - MinIO/S3 endpoint (default: http://localhost:9000)
    S3_ACCESS_KEY_ID       - S3 access key (default: minioadmin)
    S3_SECRET_ACCESS_KEY   - S3 secret key (default: minioadmin)
    S3_BUCKET_NAME         - S3 bucket name (default: gopie)
    OPENAI_API_KEY         - OpenAI API key (required for DSPy evaluation)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


class TestConfig:
    # ============================================================================
    # API Endpoints (can be overridden via environment variables)
    # ============================================================================
    GOPIE_API_URL = os.getenv("GOPIE_API_URL", "http://localhost:8000")
    CHAT_SERVER_URL = os.getenv("CHAT_SERVER_URL", "http://localhost:8001/api/v1/chat/completions")

    # Gopie Authentication
    GOPIE_USER_ID = os.getenv("GOPIE_USER_ID", "system")
    GOPIE_ORG_ID = os.getenv("GOPIE_ORG_ID", "123")

    # ============================================================================
    # S3/MinIO Configuration (can be overridden via environment variables)
    # ============================================================================
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "gopie")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")

    # ============================================================================
    # Test Data Paths (generally don't need to be changed)
    # ============================================================================
    TEST_ROOT = Path(__file__).parent
    E2E_DATASET_FOLDER = str(TEST_ROOT / "e2e" / "datasets")
    E2E_OUTPUT_DIR = TEST_ROOT / "e2e" / "output"
    VIZ_OUTPUT_DIR = str(E2E_OUTPUT_DIR / "visualization")
    VIZ_EXAMPLES_DIR = TEST_ROOT / "e2e" / "viz_utils" / "examples_arguments_syntax"

    # ============================================================================
    # DSPy Configuration
    # ============================================================================

    # LLM Configuration (for DSPy optimizations)
    # NOTE: OPENAI_API_KEY is REQUIRED for DSPy evaluation
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "openai/gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # DSPy Optimization Settings
    DSPY_CACHE_DIR = str(TEST_ROOT / "dspy" / ".cache")
    DSPY_LOG_LEVEL = os.getenv("DSPY_LOG_LEVEL", "INFO")
    DSPY_OPTIMIZER_MODEL = os.getenv("DSPY_OPTIMIZER_MODEL", "gpt-4o")
    DSPY_MAX_BOOTSTRAPPED_DEMOS = int(os.getenv("DSPY_MAX_BOOTSTRAPPED_DEMOS", "8"))
    DSPY_MAX_LABELED_DEMOS = int(os.getenv("DSPY_MAX_LABELED_DEMOS", "4"))

    @classmethod
    def validate(cls):
        required_vars = {
            "GOPIE_API_URL": cls.GOPIE_API_URL,
            "CHAT_SERVER_URL": cls.CHAT_SERVER_URL,
            "S3_ENDPOINT_URL": cls.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY_ID": cls.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": cls.S3_SECRET_ACCESS_KEY,
        }

        missing_vars = [key for key, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing_vars)}\n"
                f"Please update test_config.py with the correct values."
            )

    @classmethod
    def print_config(cls):
        print("=" * 60)
        print("Test Configuration")
        print("=" * 60)
        print(f"GOPIE_API_URL: {cls.GOPIE_API_URL}")
        print(f"CHAT_SERVER_URL: {cls.CHAT_SERVER_URL}")
        print(f"S3_ENDPOINT_URL: {cls.S3_ENDPOINT_URL}")
        print(f"S3_BUCKET_NAME: {cls.S3_BUCKET_NAME}")
        print("-" * 60)
        print("DSPy Configuration")
        print("-" * 60)
        print(f"DEFAULT_LLM_MODEL: {cls.DEFAULT_LLM_MODEL}")
        print(f"DSPY_OPTIMIZER_MODEL: {cls.DSPY_OPTIMIZER_MODEL}")
        print(f"DSPY_MAX_BOOTSTRAPPED_DEMOS: {cls.DSPY_MAX_BOOTSTRAPPED_DEMOS}")
        print(f"DSPY_MAX_LABELED_DEMOS: {cls.DSPY_MAX_LABELED_DEMOS}")
        print("=" * 60)

import os
import pytest
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from core.config import Settings

@pytest.mark.integration
def test_alembic_migrations_upgrade_downgrade():
    """
    Test that the Alembic migrations can upgrade to head and downgrade to base.
    Uses a temporary SQLite database to avoid touching the real database.
    """
    # Create test settings with an isolated SQLite database for migrations
    test_db_url = "sqlite+aiosqlite:///test_alembic.db"
    
    test_settings = Settings(
        app_env="testing",
        app_debug=True,
        app_secret_key="test-secret-key-must-be-at-least-32-chars",
        jwt_secret_key="test-jwt-key-must-be-at-least-32-chars!!",
        database_url=test_db_url,
        log_level="DEBUG",
        log_format="console",
        gemini_api_key="test-key",
    )

    alembic_cfg = Config("alembic.ini")
    
    # Run migrations in-process and mock get_settings to use our test_settings
    # The patch needs to target where get_settings is imported or called in alembic/env.py
    # The patch needs to target core.config.get_settings which is called in alembic/env.py
    with patch("core.config.get_settings", return_value=test_settings):
        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")
        
        # 2. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        
        # 3. Upgrade to head again
        command.upgrade(alembic_cfg, "head")

    # Cleanup the test database
    if os.path.exists("test_alembic.db"):
        os.remove("test_alembic.db")

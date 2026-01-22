# -*- coding: utf-8 -*-
"""
Reset and reinitialize provider configuration
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.engine import get_engine, Base, get_db
from app.db.models.providers import Provider
from app.db.provider_dao import seed_default_providers
from app.utils.logger import get_logger

logger = get_logger(__name__)

def reset_providers():
    """Delete all providers and reload from builtin_providers.json"""
    db = next(get_db())

    try:
        # Initialize database tables first
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")

        # Check if providers table has data
        count = db.query(Provider).count()
        if count > 0:
            # Delete all existing providers
            count = db.query(Provider).delete()
            db.commit()
            logger.info(f"Deleted {count} old provider configurations")

        # Reload from builtin_providers.json
        seed_default_providers()

        # Verify loading result
        providers = db.query(Provider).all()
        logger.info(f"Successfully loaded {len(providers)} providers:")
        for p in providers:
            has_key = "Yes" if (p.api_key and p.api_key.strip()) else "No"
            logger.info(f"  - {p.name}: API Key={has_key}, Enabled={p.enabled}")

        return True

    except Exception as e:
        logger.error(f"Failed to reset providers: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Resetting provider configuration...")
    if reset_providers():
        print("SUCCESS! Provider configuration reset.")
        print("\nPlease restart the backend service.")
    else:
        print("FAILED! Please check the logs.")

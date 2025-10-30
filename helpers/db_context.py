# helpers/db_context.py
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from app import create_app
from helpers.db import db
from helpers.logger import app_logger


@asynccontextmanager
async def managed_db_context():
    """
    Context manager for database session management in async tasks.
    Handles:
    - Creating app context
    - Committing/rolling back transactions
    - Closing sessions
    - Disposing connections to prevent pool exhaustion
    """
    app = create_app()
    with app.app_context():
        try:
            yield db
        except Exception as e:
            app_logger.error(f"Error in managed_db_context: {e}")
            db.session.rollback()
            raise
        finally:
            # Cleanup in order
            db.session.close()
            db.session.remove()
            db.engine.dispose()


@contextmanager
def managed_db_context_sync():
    """Context manager for SYNC database session management (for callbacks)"""
    app = create_app()
    with app.app_context():
        try:
            yield db
        except Exception as e:
            app_logger.error(f"Error in managed_db_context_sync: {e}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            db.session.remove()
            db.engine.dispose()


def async_with_db_context(func):
    """
    Decorator for async functions that need database session management.
    Usage:
        @async_with_db_context
        async def my_async_task(**request):
            # db is automatically available
    """
    @wraps(func)
    async def wrapper(**request):
        async with managed_db_context():
            return await func(**request)
    return wrapper


def sync_with_db_context(func):
    """Decorator for sync functions - for RQ callbacks with variable arguments"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # args will be: (job, connection) for success or (job, connection, *exc_info) for failure
        with managed_db_context_sync():
            return func(*args, **kwargs)
    return wrapper

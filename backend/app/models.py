"""Import every module's models so SQLAlchemy and Alembic see all tables."""

import app.modules.audit.models  # noqa: F401
import app.modules.auth.models  # noqa: F401

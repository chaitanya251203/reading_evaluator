# Import all models so SQLAlchemy relationships can resolve string references.
from app.models.teacher import Teacher  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.material import Material  # noqa: F401
from app.models.session import ReadingSession  # noqa: F401

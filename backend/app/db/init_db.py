from app.db.database import Base, engine
from app.models.material import Material
from app.models.session import ReadingSession
from app.models.student import Student
from app.models.teacher import Teacher


def init_db():
    # Ensure models are imported so tables are registered.
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized")

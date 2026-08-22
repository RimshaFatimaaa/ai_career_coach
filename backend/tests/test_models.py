from app.database import Base, engine
from app import models  # noqa: F401 — register tables


def test_models_create():
    Base.metadata.create_all(bind=engine)
    assert "users" in Base.metadata.tables
    assert "profiles" in Base.metadata.tables

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth as auth_module
from app.core.config import Settings
from app.core.database import Base
from app.models import Assessment, User


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase1.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_demo_credentials_disabled_in_production_flag(monkeypatch, db_session):
    monkeypatch.setattr(auth_module.settings, "ENABLE_DEMO_AUTH", False)
    form = SimpleNamespace(username="demo@studio.com", password="password123")
    with pytest.raises(HTTPException) as exc:
        auth_module.login(form, db_session)
    assert exc.value.status_code == 401
    assert "disabled" in str(exc.value.detail).lower()


def test_cross_tenant_assessment_isolation(db_session):
    user_a = User(
        email="a@example.com", hashed_password=auth_module.get_password_hash("x")
    )
    user_b = User(
        email="b@example.com", hashed_password=auth_module.get_password_hash("y")
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    owned = Assessment(user_id=user_a.id, company_name="A Co", status="completed")
    db_session.add(owned)
    db_session.commit()
    db_session.refresh(owned)

    visible_to_a = (
        db_session.query(Assessment)
        .filter(Assessment.id == owned.id, Assessment.user_id == user_a.id)
        .first()
    )
    visible_to_b = (
        db_session.query(Assessment)
        .filter(Assessment.id == owned.id, Assessment.user_id == user_b.id)
        .first()
    )
    assert visible_to_a is not None
    assert visible_to_b is None


def test_production_safety_rejects_insecure_defaults():
    unsafe = Settings.model_construct(
        ENVIRONMENT="production",
        SECRET_KEY=Settings.INSECURE_DEFAULT_SECRET,
        ENABLE_DEMO_AUTH=True,
        DEMO_MODE=False,
        ALLOW_HEURISTIC_FALLBACK=False,
    )
    with pytest.raises(RuntimeError):
        unsafe.validate_production_safety()


def test_production_safety_passes_with_hardened_settings():
    safe = Settings.model_construct(
        ENVIRONMENT="production",
        SECRET_KEY="a-long-random-production-secret",
        ENABLE_DEMO_AUTH=False,
        DEMO_MODE=False,
        ALLOW_HEURISTIC_FALLBACK=False,
    )
    safe.validate_production_safety()

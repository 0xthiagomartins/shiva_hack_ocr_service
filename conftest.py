"""pytest: banco em memória para testes."""
import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"


# User id usado nos testes; Receipt exige User existente (FK)
TEST_USER_ID = "fMicQESWZY7BMy6cTrqe09odj6uanNjC"


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Cria tabelas e um User para os testes (Receipt tem FK para User.id)."""
    from sqlalchemy.orm import Session
    from app.db import engine, init_db
    from app.models import User
    init_db()
    with Session(engine) as session:
        session.add(User(id=TEST_USER_ID, name="Test User", email="test@example.com"))
        session.commit()

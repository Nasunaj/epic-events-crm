"""Shared pytest fixtures for model integration tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from epicevents.database import Base
from epicevents.models import Role, Employee, Client, Event, Contract
from datetime import datetime
from decimal import Decimal


# Une base neuve par test (fixture = base remise à zéro) : chaque test est
# indépendant et rejouable dans n'importe quel ordre. Un test qui dépend des
# déchets d'un autre test est un test fragile.
# StaticPool garde la même connexion en mémoire pour que tous les tests
# parlent bien de la même base "fantôme".
# yield : code d'avant = setup, code d'après = teardown.
# On teste les modèles sur SQLite mémoire (rapide), la vraie base PostgreSQL
# étant vérifiée par le script d'init. C'est une pratique standard ; si un
# jour un test passe sur SQLite mais pas sur PostgreSQL, on adaptera.
@pytest.fixture()
def session():
    """Fresh in-memory database for each test (isolation)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture()
def role_com(session):
    role = Role(name="commercial")
    session.add(role)
    session.commit()
    return role

@pytest.fixture()
def role_sup(session):
    role = Role(name="support")
    session.add(role)
    session.commit()
    return role

@pytest.fixture()
def commercial(session, role_com):
    emp = Employee(employee_number="E001", name="Josh C",
                   email="c.josh@epicevents.com",
                   password_hash="hash1", role=role_com)
    session.add(emp)
    session.commit()
    return emp

@pytest.fixture()
def support(session, role_sup):
    emp = Employee(employee_number="E002", name="Kate A",
                   email="a.kate@epicevents.com",
                   password_hash="hash2", role=role_sup)
    session.add(emp)
    session.commit()
    return emp

@pytest.fixture()
def client(session, commercial):
    c = Client(name="Kevin Casey", email="kevin@startup.io",
               phone="+06 08 09 10 45", company_name="Cool Startup LLC",
               creation_date=datetime(2026, 9, 30),
               last_update=datetime(2026, 9, 30),
               commercial=commercial)
    session.add(c)
    session.commit()
    return c

@pytest.fixture()
def contract(session, client, commercial):
    ct = Contract(client=client, commercial=commercial,
                 total_amount=Decimal("10000.00"),
                 remaining_amount=Decimal("5000.00"),
                 is_signed=True, creation_date=datetime(2023, 5, 1))
    session.add(ct)
    session.commit()
    return ct

@pytest.fixture()
def event(session, contract, support):
    ev = Event(contract=contract, name="xxxx Party",
               event_date_start=datetime(2026, 10, 1, 13),
               event_date_end=datetime(2026, 10, 2, 2),
               location="1 ..., Paris",
               attendees=75, note="DJ", support=support)
    session.add(ev)
    session.commit()
    return ev

@pytest.fixture()
def contract2(session, client, commercial):
    ct = Contract(client=client, commercial=commercial,
                 total_amount=Decimal("2000.00"),
                 remaining_amount=Decimal("0.00"),
                 is_signed=False, creation_date=datetime(2026, 1, 15))
    session.add(ct)
    session.commit()
    return ct

@pytest.fixture()
def event2(session, contract2, support):
    ev = Event(contract=contract2, name="xxxx Party",
               event_date_start=datetime(2026, 10, 1, 13),
               event_date_end=datetime(2026, 10, 2, 2),
               location="1 ..., Paris",
               attendees=75, note="DJ", support=None)
    session.add(ev)
    session.commit()
    return ev
"""Shared pytest fixtures for model integration tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from epicevents import token_store
from epicevents.database import Base
from epicevents.models import Role, Employee, Client, Event, Contract
from datetime import datetime
from decimal import Decimal

from epicevents.services.employee_service import create_employee


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
def role_ges(session):
    """Crée le rôle 'gestion' dans la base de test."""
    role = Role(name="gestion")
    session.add(role)
    session.commit()
    return role


@pytest.fixture()
def commercial(session, role_com):
    emp = Employee(
        employee_number="E001",
        name="Josh C",
        email="c.josh@epicevents.com",
        password_hash="hash1",
        role=role_com,
    )
    session.add(emp)
    session.commit()
    return emp


@pytest.fixture()
def support(session, role_sup):
    emp = Employee(
        employee_number="E002",
        name="Kate A",
        email="a.kate@epicevents.com",
        password_hash="hash2",
        role=role_sup,
    )
    session.add(emp)
    session.commit()
    return emp


@pytest.fixture()
def client(session, commercial):
    c = Client(
        name="Kevin Casey",
        email="kevin@startup.io",
        phone="+06 08 09 10 45",
        company_name="Cool Startup LLC",
        creation_date=datetime(2026, 9, 30),
        last_update=datetime(2026, 9, 30),
        commercial=commercial,
    )
    session.add(c)
    session.commit()
    return c


@pytest.fixture()
def contract(session, client, commercial):
    ct = Contract(
        client=client,
        commercial=commercial,
        total_amount=Decimal("10000.00"),
        remaining_amount=Decimal("5000.00"),
        is_signed=True,
        creation_date=datetime(2023, 5, 1),
    )
    session.add(ct)
    session.commit()
    return ct


# @pytest.fixture()
# def contract2(session, client, commercial):
#     ct = Contract(
#         client=client,
#         total_amount=Decimal("2000.00"),
#         remaining_amount=Decimal("0.00"),
#         is_signed=False,
#         creation_date=datetime(2026, 1, 15),
#     )
#     session.add(ct)
#     session.commit()
#     return ct


@pytest.fixture()
def event(session, contract, support):
    ev = Event(
        contract=contract,
        name="xxxx Party",
        event_date_start=datetime(2026, 10, 1, 13),
        event_date_end=datetime(2026, 10, 2, 2),
        location="1 ..., Paris",
        attendees=75,
        note="DJ",
        support=support,
    )
    session.add(ev)
    session.commit()
    return ev


@pytest.fixture()
def contract2(session, client, commercial):
    ct = Contract(
        client=client,
        commercial=commercial,
        total_amount=Decimal("2000.00"),
        remaining_amount=Decimal("0.00"),
        is_signed=False,
        creation_date=datetime(2026, 1, 15),
    )
    session.add(ct)
    session.commit()
    return ct


@pytest.fixture()
def event2(session, contract2, support):
    ev = Event(
        contract=contract2,
        name="xxxx Party",
        event_date_start=datetime(2026, 10, 1, 13),
        event_date_end=datetime(2026, 10, 2, 2),
        location="1 ..., Paris",
        attendees=75,
        note="DJ",
        support=None,
    )
    session.add(ev)
    session.commit()
    return ev


@pytest.fixture()
def make_employee(session, role_ges):
    """Factory: returns a callable creating employees with defaults."""

    def _make(**overrides):
        defaults = dict(
            session=session,
            email="c.josh@epicevents.com",
            employee_number="E001",
            name="Josh C",
            role_name="gestion",
            password="AZERTYUI",
        )
        defaults.update(overrides)
        return create_employee(**defaults)

    return _make


# Test for epicevents/token_store.py
@pytest.fixture()
def isolated_store(tmp_path):
    """Redirect TOKEN_PATH to a throwaway directory for this test"""
    # Mémorisation du vrai chemin
    original = token_store.TOKEN_PATH

    # token_store.TOKEN_PATH = ... : on remplace la constante du module à la
    # volée. Python lit les variables de module au moment de l'appel
    # (TOKEN_PATH est regardé dans le module à chaque exécution de
    # save_token, etc.). C'est pour ça que le remplacement fonctionne.
    token_store.TOKEN_PATH = tmp_path / "token"
    yield
    # Restauration du vrai chemin
    token_store.TOKEN_PATH = original


@pytest.fixture()
def make_client(session, commercial):
    """Factory: returns a callable creating clients with defaults."""

    def _make(**overrides):
        defaults = dict(
            name="Client 1",
            email="client@startup.com",
            phone="06 01 09 10 45",
            company_name="Startup SAS",
            creation_date=datetime(2026, 10, 1),
            last_update=datetime(2026, 10, 1),
            commercial=commercial,
        )
        defaults.update(overrides)
        client = Client(**defaults)
        session.add(client)
        session.commit()
        return client

    return _make


@pytest.fixture()
def gestion(session, role_ges):
    emp = Employee(
        employee_number="E003",
        name="M Gestion",
        email="m.gestion@epicevents.com",
        password_hash="hash3",
        role=role_ges,
    )
    session.add(emp)
    session.commit()
    return emp

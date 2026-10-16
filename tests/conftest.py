"""Shared pytest fixtures for model integration tests."""

from click.testing import CliRunner
from epicevents import cli as cli_module

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
    """Factory: create employees with defaults that collide with nothing."""

    def _make(**overrides):
        defaults = dict(
            session=session,
            employee=None,
            bootstrap=True,
            email="factory.employee@epicevents.com",
            employee_number="E900",
            name="Factory Employee",
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


# --------------- fixtures for the CLI tests ----------------------
# ---------------------------------------------------------------
# Prérequis : en haut du conftest.py, il faut ces deux imports :
#     from click.testing import CliRunner
#     from epicevents import cli as cli_module
#
# Pourquoi from epicevents import cli as cli_module et pas
# from epicevents.cli import cli seul? Parce que monkeypatch a besoin du MODULE
# (la boîte qui contient les noms) pour remplacer un nom DEDANS. On patche
# cli_module.get_session, donc on doit importer le module lui-même, pas
# seulement ses habitants.


@pytest.fixture()
def runner():
    """The terminal simulator: a fresh instance for each test."""
    # CliRunner est l'outil de Click pour tester un CLI sans vrai terminal :
    # invoke() simule les frappes clavier (paramètre input), capture stdout/stderr
    # et attrape les exceptions. Une instance neuve par test = aucune pollution
    # entre les tests (isolation).
    return CliRunner()


# --- The identity fixtures: who is running the command? -------
# Rappel du mécanisme (le cœur de ces fixtures) :
#   require_login fait DEUX appels :
#     session = get_session()                  # la dépendance base
#     employee = get_current_employee(session) # la dépendance identité
#   Ces noms sont résolus DANS le module cli au moment de l'appel.
#   monkeypatch.setattr(cli_module, "get_session", ...) remplace le nom dans
#   ce module : require_login appelle donc notre faux, pas le vrai. Après le
#   test, monkeypatch restaure tout seul (c'est sa garantie : aucun effet de
#   bord qui fuirait vers les autres tests).
#
# Résultat : pas besoin de fichier token sur disque, pas besoin de JWT valide.
# On injecte directement l'employé voulu, comme si la personne était déjà connectée.


@pytest.fixture()
def as_gestion(monkeypatch, session, gestion):
    """Simulates a user logged in as management (gestion).

    Both injection points used by `require_login` are patched.
    No token file is read: `get_current_employee` is short-circuited.
    """
    # 1er point d'injection : la session. Le module cli croit ouvrir
    # la vraie base ; il reçoit la session SQLite de test du conftest.
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    # 2e point d'injection : l'identité. Le vrai get_current_employee
    # relit le token du disque, le décode, recharge l'employé ;
    # le nôtre renvoie directement l'employé "gestion" du jeu de test.
    # (lambda s: ... : le paramètre s est la session, ignorée ici.)
    monkeypatch.setattr(cli_module, "get_current_employee", lambda s: gestion)
    # On retourne l'employé : le test peut utiliser son id, son nom…
    return gestion


@pytest.fixture()
def as_commercial(monkeypatch, session, commercial):
    """Simulates a user logged in as a sales representative (commercial)."""
    # Même mécanique, autre rôle : le test des refus de périmètre
    # (clients/contrats des autres) partira de cette identité.
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    monkeypatch.setattr(cli_module, "get_current_employee", lambda s: commercial)
    return commercial


@pytest.fixture()
def as_support(monkeypatch, session, support):
    """Simulates a user logged in as support."""
    # Idem pour le support : tests de --mine, update de SON événement…
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    monkeypatch.setattr(cli_module, "get_current_employee", lambda s: support)
    return support


@pytest.fixture()
def not_logged_in(monkeypatch, session):
    """Simulates no user being logged in (token absent/expired -> None)."""
    # Le cas US-04 : get_current_employee renvoie None, exactement
    # comme en production quand il n'y a pas de token (ou token
    # expiré, ou employé disparu de la base). require_login doit
    # alors refuser la commande : exit 1 + message "Non connecté".
    # C'est le test de sécurité du garde — le seul où None est le
    # résultat attendu, pas un bug.
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    monkeypatch.setattr(cli_module, "get_current_employee", lambda s: None)

"""CLI tests: we are testing the presentation layer, not the business logic.

General principle (to keep in mind):
- The business logic (services) is already tested elsewhere. Here, we verify
  that the commands are wired up correctly: Click parsing, messages, exit
  codes, and the rejection of requests (US-04) when no token is present.
- Core technique: monkeypatch replaces, WITHIN the cli module, the two
  dependencies injected by `require_login`:
    * cli.get_session -> the test SQLite session (from `conftest`)
    * cli.get_current_employee -> a test employee (no token file needed)
  Since `require_login` calls these names via the module, the replacement
  applies everywhere, without modifying the production code.
- Click's `CliRunner` simulates a terminal: invoke() returns the stdout
  (via result.output), the exit code (via result.exit_code), and captures
  any exception (via result.exception).
"""

import pytest
from epicevents import cli as cli_module
from epicevents.cli import cli
from epicevents.exceptions import AuthenticationError

# ---------- US-01: login ----------


def test_login_success(runner, monkeypatch, session, commercial):
    """Successful login: the service returns the employee, the command
    prints a welcome message."""
    # On patche get_session : la commande croit parler à la vraie base,
    # elle parle à la SQLite de test (aucun PostgreSQL requis).
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    # On remplace le service par un faux (le vrai est déjà testé) :
    # on teste la COMMANDE, pas Argon2.
    monkeypatch.setattr(cli_module, "auth_login", lambda s, e, p: commercial)
    # save_token écrit sur le disque : on le neutralise (pas d'effet de bord,
    # le test reste isolé et ne pollue pas la machine).
    monkeypatch.setattr(cli_module, "save_token", lambda token: None)

    result = runner.invoke(cli, ["login", "--email", "x@y.z", "--password", "pw"])
    assert result.exit_code == 0
    assert "Connecté" in result.output
    assert "commercial" in result.output


def test_login_failure_message_is_generic(runner, monkeypatch, session):
    """US-01: the failure message is generic (anti-enumeration), exit code 1."""

    # Un faux service qui lève l'erreur métier d'authentification :
    # simule un mot de passe incorrect sans passer par Argon2.
    def raise_auth(s, email, password):
        raise AuthenticationError("Identifiants incorrects.")

    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    monkeypatch.setattr(cli_module, "auth_login", raise_auth)

    result = runner.invoke(cli, ["login", "--email", "a@b.c", "--password", "bad"])
    assert result.exit_code == 1
    assert "Identifiants incorrects." in result.output


# ---------- US-02 / US-03: whoami, logout ----------


def test_whoami_when_logged_in(runner, monkeypatch, session, commercial):
    """whoami prints the name of the currently logged-in employee."""
    # Même technique que require_login : on injecte session + identité.
    # Pas de fichier token : get_current_employee est court-circuité.
    monkeypatch.setattr(cli_module, "get_session", lambda: session)
    monkeypatch.setattr(cli_module, "get_current_employee", lambda s: commercial)
    result = runner.invoke(cli, ["whoami"])
    assert result.exit_code == 0
    assert commercial.name in result.output


def test_whoami_when_not_logged_in(runner, not_logged_in):
    """Without a token: a clear message, not a crash."""
    result = runner.invoke(cli, ["whoami"])
    assert result.exit_code == 0
    assert "Non connecté" in result.output


def test_logout_is_idempotent(runner):
    """US-03: logout depends on nothing — always OK, always the message."""
    result = runner.invoke(cli, ["logout"])
    assert result.exit_code == 0
    assert "Déconnecté" in result.output


# ---------- US-04: the universal auth guard ----------


# Un même test joué sur les 4 groupes : le garde refuse SANS token,
# quel que soit le groupe visé. Chaque jeu de données = un test.
@pytest.mark.parametrize(
    "command",
    [
        ["employees", "list"],
        ["clients", "list"],
        ["contracts", "list"],
        ["events", "list"],
    ],
)
def test_guard_refuses_without_token(runner, not_logged_in, command):
    """Every protected group requires a token: exit 1 + actionable message."""
    result = runner.invoke(cli, command)
    assert result.exit_code == 1
    assert "Non connecté" in result.output


# ---------- US-10 to US-12: employees ----------


def test_employees_create(runner, as_gestion, role_com):
    """Creation by gestion: success message contains name and role."""
    result = runner.invoke(
        cli,
        [
            "employees",
            "create",
            "--email",
            "new@epicevents.com",
            "--employee-number",
            "E100",
            "--name",
            "New Employee",
            "--role-name",
            "commercial",
            "--password",
            "secret123",
        ],
    )
    assert result.exit_code == 0
    assert "Créé : New Employee" in result.output
    assert "commercial" in result.output


def test_employees_update(runner, as_gestion, commercial):
    """Update --name: the 'Changer le mot de passe ?' confirm receives 'n'."""
    # input="n\n" répond À L'AVANCE au click.confirm : le runner simule
    # les frappes clavier dans l'ordre des questions posées.
    result = runner.invoke(
        cli,
        ["employees", "update", str(commercial.id), "--name", "Renamed"],
        input="n\n",
    )
    assert result.exit_code == 0
    assert "Modifié : Renamed" in result.output


def test_employees_list(runner, as_gestion, commercial):
    """The employees table lists the seeded employee."""
    result = runner.invoke(cli, ["employees", "list"])
    assert result.exit_code == 0
    assert commercial.name in result.output


# ---------- US-20 to US-22: clients ----------


def test_clients_create_auto_assigns_commercial(runner, as_commercial):
    """The success message makes the auto-assignment visible (US-20)."""
    result = runner.invoke(
        cli,
        [
            "clients",
            "create",
            "--name",
            "ACME",
            "--email",
            "info@acme.io",
            "--phone",
            "0601020304",
            "--company-name",
            "ACME SAS",
        ],
    )
    assert result.exit_code == 0
    assert "Client créé : ACME" in result.output


def test_clients_update_own_client(runner, as_commercial, client):
    """A commercial updates their own client (US-21)."""
    result = runner.invoke(
        cli, ["clients", "update", str(client.id), "--phone", "0699999999"]
    )
    assert result.exit_code == 0
    assert "Client modifié" in result.output


# ---------- US-30 to US-32: contracts ----------


def test_contracts_create_signed(runner, as_gestion, client):
    """Signed contract: Click asks for the remaining amount (prompt with
    default=total). input='500\\n' answers that prompt; other options are
    provided on the command line."""
    result = runner.invoke(
        cli,
        [
            "contracts",
            "create",
            "--client-id",
            str(client.id),
            "--total-amount",
            "1000",
            "--signed",
        ],
        input="500\n",
    )
    assert result.exit_code == 0
    assert "créé" in result.output


def test_contracts_update_signature(runner, as_gestion, contract):
    """The paired flag --signed sets is_signed to True (US-31)."""
    result = runner.invoke(cli, ["contracts", "update", str(contract.id), "--signed"])
    assert result.exit_code == 0
    assert "signé : oui" in result.output


def test_contracts_list_empty_message(runner, as_gestion):
    """Empty table: a clean message, not a crash ('if not contracts' branch)."""
    result = runner.invoke(cli, ["contracts", "list"])
    assert result.exit_code == 0
    assert "Aucun contrat" in result.output


# ---------- US-40 to US-43: events ----------


def test_events_create_on_signed_contract(runner, as_commercial, contract):
    """Dates given as DD/MM/YYYY HH:MM: Click converts them to datetime."""
    result = runner.invoke(
        cli,
        [
            "events",
            "create",
            "--contract-id",
            str(contract.id),
            "--name",
            "Gala",
            "--event-date-start",
            "01/12/2026 10:00",
            "--event-date-end",
            "01/12/2026 18:00",
            "--location",
            "Paris",
            "--attendees",
            "50",
        ],
    )
    assert result.exit_code == 0
    assert "Événement créé : Gala" in result.output


def test_events_update_by_assigned_support(runner, as_support, event):
    """The assigned support updates THEIR event (US-41)."""
    result = runner.invoke(
        cli, ["events", "update", str(event.id), "--location", "Lyon"]
    )
    assert result.exit_code == 0
    assert "Événement modifié" in result.output


def test_events_assign_support(runner, as_gestion, event2, support):
    """US-42: gestion assigns a support to the orphan event."""
    result = runner.invoke(
        cli,
        [
            "events",
            "assign-support",
            "--event-id",
            str(event2.id),
            "--support-id",
            str(support.id),
        ],
    )
    assert result.exit_code == 0
    assert "Support assigné" in result.output


def test_events_list_mine_guides_gestion(runner, as_gestion):
    """--mine as gestion: refusal with guidance (a CDC decision, not a crash)."""
    result = runner.invoke(cli, ["events", "list", "--mine"])
    assert result.exit_code == 0
    assert "--no-support" in result.output

"""Epic Events CRM command-line interface.

Thin presentation layer: it parses input, calls the (already secured)
services, and turns business exceptions into user-friendly messages.
No business rule lives here — the services own every rule.

Covers user stories: US-01 (login), US-02 (whoami), US-03 (logout),
US-04 (authentication guard on every command).
"""

# sys : pour sys.argv (récupéré par Click) et sys.exit (codes de sortie)
import sys

# functools.wraps : indispensable pour nos propres décorateurs
# sans lui, Click afficherait "wrapper" au lieu du nom de la commande
import functools

# click : le framework CLI. Toute la mécanique de parsing (options,
# prompts, aide, conversion de types) vient de lui.
import click

from rich.console import Console
from rich.table import Table

# Les briques (aucune règle métier écrit ici)
from epicevents.database import get_session
from epicevents.exceptions import (
    AuthenticationError,
    # EpicEventsError classe de base : attrape TOUTES les erreurs métier
    EpicEventsError,
)
from epicevents.security import create_token
from epicevents.services.auth_service import (
    get_current_employee,
    # alias : évite la collision avec la commande "login"
    login as auth_login,
)
from epicevents.services.client_service import (
    create_client,
    update_client,
    list_clients,
)
from epicevents.services.contract_service import (
    create_contract,
    update_contract,
    list_unsigned_contracts,
    list_unpaid_contracts,
    list_contracts,
)
from epicevents.services.employee_service import (
    create_employee,
    update_employee,
    list_employees,
)
from epicevents.services.event_service import (
    create_event,
    update_event,
    assign_support,
    list_events_without_support,
    list_events_for_support,
    list_events_for_commercial,
    list_events,
)
from epicevents.token_store import clear_token, save_token

from epicevents.logging_conf import init_sentry

console = Console()

# La commande CLI s'appelle login (le nom tapé par l'utilisateur). Le service
# s'appelle aussi login. L'import via l'alias distingue les deux couches :
# la commande (présentation) appelle le service (métier). Sans alias,
# l'un écraserait l'autre dans l'espace de noms du module.


#  --- US-04  Le garde d'authentification universel ----
def require_login(func):
    """Inject session and the authenticated employee into the command.

    Refuses the command (clean message, exit 1) if no valid token.
    """

    # functools.wraps copie nom + docstring de func sur wrapper.
    # Crucial pour Click : c'est ainsi que --help affiche le vrai nom
    # et la vraie description de la commande, pas wrapper.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Le décorateur résout les 2 dépendances de toute commande :
        # 1. la session (l'accès à la base)
        session = get_session()
        # 2. l'identité (qui est connecté ?) relit le token stocké
        #   sur disque, le décode, et recharge l'employé depuis la base.
        #   Retourne None si pas de token / token expiré / employé disparu.
        employee = get_current_employee(session)
        if employee is None:
            # US-04 : aucun accès sans authentification. On refuse avec un
            # message actionnable (comment se connecter) sur stderr.
            click.echo("Non connecté. Lancez 'epicevents login'.", err=True)
            sys.exit(1)  # code de sortie 1 = échec (convention Unix)
            # Injection : la commande reçoit session et employee comme
            # premiers paramètres. Elle ne les demande jamais à l'utilisateur.
            # C'est le pattern dependency injection : la couche au-dessus
            # fournit le contexte, la commande se concentre sur son action.
        return func(session, employee, *args, **kwargs)

    return wrapper


# --- Le groupe racine : le point d'entrée "epicevents" -------
@click.group()
def cli():
    """Epic Events CRM : management of clients, contracts, and events."""
    # Un groupe Click est un conteneur de commandes. Sa docstring devient
    # le texte affiché par epicevents --help. Chaque commande accrochée
    # via @cli.command() devient un sous-argument : epicevents login, etc.
    # Le corps peut rester vide : le groupe ne fait que router.


# --- US-01 — Connexion ----------
@cli.command()
@click.option("--email", prompt=True, help="Votre email")
# prompt=True : si l'utilisateur ne tape pas --email, Click POSE la
# question dans le terminal. Le CLI reste utilisable sans documentation.
@click.option("--password", prompt=True, hide_input=True, help="Votre mot de passe")
# saisie masquée : rien ne s'affiche (sécurité)
def login(email: str, password: str):
    """Log in and store the session token."""
    # Click a déjà fait le travail : email et password sont des chaînes
    # non vides (les prompts obligent à répondre). La commande n'a plus
    # qu'à déléguer au service qui vérifie le mot de passe (Argon2id)
    # et lève AuthenticationError en cas d'échec.
    session = get_session()
    try:
        employee = auth_login(session, email.strip(), password)
    except AuthenticationError:
        # US-01 (critère d'acceptation) : message générique, identique que
        # l'email soit inconnu ou le mot de passe faux => anti-enumeration.
        click.echo("Identifiants incorrects.", err=True)
        sys.exit(1)

    # Succès : on génère le JWT (étape 4 : HS256, expiration, algorithme
    # fixé) et on le stocke sur disque (token_store : permissions 0o600).
    # Deux briques existantes assemblées. Zéro logique réécrite.
    save_token(create_token(employee.id, employee.role.name))
    # Message de bienvenue (nom + rôle)
    click.echo(f"Connecté : {employee.name} ({employee.role.name})")


# --- US-02  Identité courante ----------
@cli.command()
def whoami():
    """Show the currently logged-in employee."""
    # Prototype de toute commande protégée : session => identité =>
    # refus si None, action sinon. Les commandes métier utiliseront @require_login.
    session = get_session()
    employee = get_current_employee(session)
    if employee is None:
        # US-02 : sans token, on l'affiche clairement => pas un crash.
        click.echo("Non connecté.")
    else:
        click.echo(f"{employee.name} — {employee.email} ({employee.role.name})")


# --- US-03 Déconnexion --------
@cli.command()
def logout():
    """Clear the stored session token."""
    # US-03 (critère d'acceptation) : idempotent => se déconnecter sans
    # être connecté n'est pas une erreur (clear_token gère le cas
    # fichier absent silencieusement). Un seul appel, zéro condition.
    clear_token()
    click.echo("Déconnecté.")


# ------- Collaborateur ------------------
@click.group()
def employees():
    """Employee management."""


# branche le groupe au groupe racine
cli.add_command(employees)


# --- US-10 Créer un collaborateur --------
@employees.command()
@require_login
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--employee-number", prompt=True)
@click.option("--role-name", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create(session, employee, email, employee_number, name, role_name, password):
    """Create a new employee (gestion allow)."""
    created = create_employee(
        session,
        employee=employee,  # le service vérifie son rôle
        email=email.strip(),
        employee_number=employee_number,
        name=name,
        role_name=role_name,
        password=password,
    )
    click.echo(f"Créé : {created.name} ({created.role.name})")


# --- US-11 Modifier un collaborateur --------
@employees.command()
@click.argument("target_id", type=int)
# Un argument Click (contrairement à une option --name) est un paramètre que
# l'utilisateur tape en position, sans nom, obligatoire par défaut.
@click.option("--name", default=None)
@click.option("--email", default=None)
@click.option("--employee-number", default=None)
# convention cli pas de _ mettre plutôt à la place - cli déduira pour trouver
# ex : --employee-number => employee_number def update.
@click.option("--role-name", default=None)
@require_login
def update(session, employee, target_id, name, email, employee_number, role_name):
    """Update an existing employee (gestion allow)"""
    dict_param = {
        "name": name,
        "email": email,
        "employee_number": employee_number,
        "role_name": role_name,
    }  # k: v = la clé k pointe vers la valeur v
    fields = {
        k: (v.strip() if k == "email" else v)
        for k, v in dict_param.items()
        if v is not None
    }
    # Le mot de passe : jamais en option (il resterait dans
    # l'historique du shell). On le demande ici, masqué, seulement
    # si l'utilisateur en veut un nouveau.
    if click.confirm("Changer le mot de passe ?"):
        fields["password"] = click.prompt(
            "Nouveau mot de passe", hide_input=True, confirmation_prompt=True
        )
    updated = update_employee(session, employee, target_id, **fields)
    click.echo(f"Modifié : {updated.name}")


# --- US-12 Lister les collaborateurs --------
@employees.command(name="list")
@require_login
# underscore final est la convention pour éviter d'écraser le builtin list
def list_employees_cmd(session, employee):
    """Lister les collaborateurs (US-12)."""
    table = Table(title="Collaborateurs")
    table.add_column("ID", justify="right")
    table.add_column("N°", style="cyan")
    table.add_column("Nom")
    table.add_column("Email")
    table.add_column("Rôle", style="green")
    for e in list_employees(session):
        table.add_row(str(e.id), e.employee_number, e.name, e.email, e.role.name)
    console.print(table)


# ------- Client ------------------
@click.group()
def clients():
    """Client management."""


# branche le groupe au groupe racine
cli.add_command(clients)


# --- US-20 Créer un client (commercial) --------
@clients.command(name="create")
@require_login
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--phone", prompt=True)
@click.option("--company-name", prompt=True)
def create_client_cmd(session, employee, name, email, phone, company_name):
    """Créer un client (association automatique au commercial connecté)."""
    client = create_client(
        session,
        employee,
        name=name.strip(),
        email=email.strip(),
        phone=phone,
        company_name=company_name,
    )
    # L'auto-association rendue visible : l'utilisateur comprend
    # que le client est à lui, sans qu'il ait eu à le demander.
    click.echo(f"Client créé : {client.name} — commercial : {employee.name}")


# --- US-21 — Modifier un client (commercial, le sien) --------
@clients.command(name="update")
@require_login
@click.argument("client_id", type=int)
@click.option("--name", default=None)
@click.option("--email", default=None)
@click.option("--phone", default=None)
@click.option("--company-name", default=None)
def update_client_cmd(session, employee, client_id, name, email, phone, company_name):
    """Modifier un client dont vous êtes le commercial."""
    fields = {
        k: v
        for k, v in {
            "name": name,
            "email": email,
            "phone": phone,
            "company_name": company_name,
        }.items()
        if v is not None
    }
    if "name" in fields:
        fields["name"] = fields["name"].strip()
    if "email" in fields:
        fields["email"] = fields["email"].strip()
    updated = update_client(session, employee, client_id, **fields)
    click.echo(f"Client modifié : {updated.name}")


# --- US-22 — Lister les clients (tous) --------
@clients.command(name="list")
@require_login
def list_clients_cmd(session, employee):
    """Lister tous les clients (lecture universelle)."""
    table = Table(title="Clients")
    for col in (
        "ID",
        "Nom",
        "Entreprise",
        "Email",
        "Téléphone",
        "Commercial",
        "Dernière MAJ",
    ):
        table.add_column(col)
    for c in list_clients(session):
        table.add_row(
            str(c.id),
            c.name,
            c.company_name,
            c.email,
            c.phone,
            c.commercial.name,
            c.last_update.strftime("%d/%m/%Y"),
        )
    console.print(table)


# ------- Contrat ------------------
@click.group()
def contracts():
    """contract management."""


# branche le groupe au groupe racine
cli.add_command(contracts)


# --- US-30 Créer un contrat (gestion) --------
@contracts.command(name="create")
@require_login
@click.option("--client-id", type=int, prompt=True)
@click.option("--total-amount", prompt=True)
@click.option(
    "--signed",
    is_flag=True,
    default=None,
    help="Contrat déjà signé (sinon, la question est posée)",
)
def create_contract_cmd(session, employee, client_id, total_amount, signed):
    """Creating a contract (administration). At the creation stage, no
    payments are made until the contract has been signed."""
    if signed is None:
        signed = click.confirm("Le contrat est-il déjà signé?", default=False)
    total = total_amount.strip()
    if signed:
        remaining = click.prompt("Montant restant à payer", default=total)
    else:
        remaining = total
    contract = create_contract(
        session,
        employee,
        client_id,
        total_amount=total,
        remaining_amount=remaining.strip(),
        is_signed=signed,
    )
    click.echo(f"Contrat {contract.id} créé — client : {contract.client.name}")


# --- US-31 — Modifier un contrat (gestion tous ; commercial ses clients) --------
@contracts.command(name="update")
@require_login
@click.argument("contract_id", type=int)
@click.option("--total-amount", default=None, help="Nouveau montant total")
@click.option("--remaining-amount", default=None, help="Nouveau restant à payer")
@click.option(
    "--signed/--unsigned",
    "new_signed",
    default=None,
    help="Changer le statut de signature",
)
@click.option(
    "--client-id", type=int, default=None, help="Rattacher à un autre client (gestion)"
)
def update_contract_cmd(
    session,
    employee,
    contract_id,
    total_amount,
    remaining_amount,
    new_signed,
    client_id,
):
    """Update a contract."""
    fields = {
        k: v
        for k, v in {
            "total_amount": total_amount,
            "remaining_amount": remaining_amount,
            "client_id": client_id,
        }.items()
        if v is not None
    }
    if new_signed is not None:
        fields["is_signed"] = new_signed
    updated = update_contract(session, employee, contract_id, **fields)
    click.echo(
        f"Contrat {updated.id} modifié — client : {updated.client.name}, "
        f"signé : {'oui' if updated.is_signed else 'non'}"
    )


# --- US-32 — Lister les contrats (tous, avec filtres) --------
@contracts.command(name="list")
@require_login
@click.option(
    "--unsigned",
    "unsigned_only",
    is_flag=True,
    help="Uniquement les contrats non signés",
)
@click.option(
    "--unpaid", "unpaid_only", is_flag=True, help="Uniquement les contrats non soldés"
)
def list_contract_cmd(session, employee, unsigned_only, unpaid_only):
    """Lister les contrats (lecture universelle, filtres optionnels)."""
    if unsigned_only:
        contracts = list_unsigned_contracts(session)
    elif unpaid_only:
        contracts = list_unpaid_contracts(session)
    else:
        contracts = list_contracts(session)
    if not contracts:
        click.echo("Aucun contrat trouvé.")
        return
    table = Table(title="Contrats")
    for col in ("ID", "Client", "Commercial", "Total", "Restant", "Signé", "Créé le"):
        table.add_column(col)
    for c in contracts:
        table.add_row(
            str(c.id),
            c.client.name,
            c.commercial.name if c.commercial else "-",
            f"{c.total_amount:,.2f} €".replace(",", " "),
            f"{c.remaining_amount:,.2f} €".replace(",", " "),
            "✓" if c.is_signed else "✗",
            c.creation_date.strftime("%d/%m/%Y"),
        )
    console.print(table)


# ------- Event ------------------
@click.group()
def events():
    """Event management."""


# branche le groupe au groupe racine
cli.add_command(events)


# --- US-40 Créer un événement --------
@events.command(name="create")
@require_login
@click.option("--contract-id", type=int, prompt=True)
@click.option("--name", prompt=True)
@click.option(
    "--event-date-start", type=click.DateTime(formats=["%d/%m/%Y %H:%M"]), prompt=True
)
@click.option(
    "--event-date-end", type=click.DateTime(formats=["%d/%m/%Y %H:%M"]), prompt=True
)
@click.option("--location", prompt=True)
@click.option("--attendees", type=int, prompt=True)
@click.option("--note", default=None)
def create_event_cmd(
    session,
    employee,
    contract_id,
    name,
    event_date_start,
    event_date_end,
    location,
    attendees,
    note,
):
    """Create a event (signed contract required)."""
    event = create_event(
        session=session,
        employee=employee,
        contract_id=contract_id,
        name=name.strip(),
        event_date_start=event_date_start,
        event_date_end=event_date_end,
        location=location.strip(),
        attendees=attendees,
        note=note,
    )
    click.echo(f"Événement créé : {event.name} (contrat {event.contract.id})")


# --- US-41 Modifier un événement (support, le sien) --------
@events.command(name="update")
@require_login
@click.argument("event_id", type=int)
@click.option("--name", default=None)
@click.option(
    "--event-date-start",
    "new_start",
    type=click.DateTime(formats=["%d/%m/%Y %H:%M"]),
    default=None,
)
@click.option(
    "--event-date-end",
    "new_end",
    type=click.DateTime(formats=["%d/%m/%Y %H:%M"]),
    default=None,
)
@click.option("--location", default=None)
@click.option("--attendees", type=int, default=None)
@click.option("--notes", default=None)
def update_event_cmd(
    session, employee, event_id, name, new_start, new_end, location, attendees, notes
):
    """Modifier un événement dont vous êtes le support."""
    fields = {
        k: v
        for k, v in {
            "name": name,
            "event_date_start": new_start,
            "event_date_end": new_end,
            "location": location,
            "attendees": attendees,
            "notes": notes,
        }.items()
        if v is not None
    }
    if "name" in fields:
        fields["name"] = fields["name"].strip()
    if "location" in fields:
        fields["location"] = fields["location"].strip()
    updated = update_event(session, employee, event_id, **fields)
    click.echo(f"Événement modifié : {updated.name}")


# --- US-42 Assigner un support --------
@events.command("assign-support")
@require_login
@click.option("--event-id", type=int, prompt=True)
@click.option("--support-id", type=int, prompt=True)
def assign(session, employee, event_id, support_id):
    """Assign a support at an event (gestion)."""
    event = assign_support(session, employee, event_id, support_id)
    click.echo(f"Support assigné : {event.support.name} => {event.name}")


# --- US-43 Lister les événements (avec filtres) --------
@events.command(name="list")
@require_login
@click.option(
    "--no-support",
    "without_support",
    is_flag=True,
    help="Événements sans support assigné (vue gestion)",
)
@click.option(
    "--mine",
    "mine_only",
    is_flag=True,
    help="Mes événements (support) ou ceux de mes clients (commercial)",
)
def list_events_cmd(session, employee, without_support, mine_only):
    """Lister les événements (lecture universelle)."""
    if without_support:
        events = list_events_without_support(session)
        title = "Événements sans support"
    elif mine_only:
        # Adaptation au rôle : "mes événements" ne veut pas dire la même
        # chose pour un support (assignés) et un commercial (ses clients).
        if employee.role.name == "support":
            events = list_events_for_support(session, employee)
            title = f"Événements de {employee.name}"
        elif employee.role.name == "commercial":
            events = list_events_for_commercial(session, employee)
            title = f"Événements des clients de {employee.name}"
        else:
            # Le filtre --mine n'existe pas pour la gestion (CDC) ;
            # son filtre naturel est --no-support.
            click.echo(
                "Le filtre --mine concerne les rôles support et commercial.\n"
                "Pour votre rôle, essayez : epicevents events list --no-support"
            )
            return
    else:
        events = list_events(session)
        title = "Événements"

    table = Table(title=title)
    for col in (
        "ID",
        "Nom",
        "Client",
        "Contrat",
        "Support",
        "Début",
        "Fin",
        "Lieu",
        "Participants",
    ):
        table.add_column(col)
    for e in events:
        table.add_row(
            str(e.id),
            e.name,
            e.contract.client.name,
            str(e.contract.id),
            e.support.name if e.support else "—",
            e.event_date_start.strftime("%d/%m/%Y %H:%M"),
            e.event_date_end.strftime("%d/%m/%Y %H:%M"),
            e.location,
            str(e.attendees),
        )
    console.print(table)


# --- Le harnais d'erreurs global (US-04) -----
def main():
    """Console entry point: catch business errors, let bugs crash."""
    init_sentry()  # Avant cli(), pour couvrir toute l'exécution
    try:
        # cli() déclenche Click : parsing de sys.argv, choix de la
        # commande, exécution. C'est ici que tout commence.
        cli()
    except EpicEventsError as exc:
        # Une seule attrape pour toutes les erreurs métier. Message sur stderr
        # (le canal des diagnostics — stdout reste réservé aux données),
        # code de sortie 1 pour les scripts automatisés.
        click.echo(f"Erreur : {exc}", err=True)
        sys.exit(1)
        # Pas de except Exception ici, volontairement. Un bug doit
        # remonter avec son traceback complet. L'attraper casserait la
        # journalisation des erreurs imprévues.


if __name__ == "__main__":
    main()

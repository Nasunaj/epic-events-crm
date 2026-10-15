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
from epicevents.token_store import clear_token, save_token

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


# --- US-03 — Déconnexion --------
@cli.command()
def logout():
    """Clear the stored session token."""
    # US-03 (critère d'acceptation) : idempotent => se déconnecter sans
    # être connecté n'est pas une erreur (clear_token gère le cas
    # fichier absent silencieusement). Un seul appel, zéro condition.
    clear_token()
    click.echo("Déconnecté.")


# --- Le harnais d'erreurs global (US-04) -----
def main():
    """Console entry point: catch business errors, let bugs crash."""
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

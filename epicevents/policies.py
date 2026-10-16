"""Role-based access policies (single source of truth).

This module ONLY defines who can do what. Services import and enforce
these rules; nothing here contains business logic.

Why a dedicated module: the whole permission matrix can be audited
in one glance, and a role change happens in exactly one place.
"""

# --- Reading: every authenticated employee reads everything (CDC) ---
READERS = ("gestion", "commercial", "support")  # = all roles

# --- Writing scopes (step 6) ---
CLIENT_CREATORS = ("commercial",)
CLIENT_UPDATERS = ("commercial",)  # son client uniquement
CONTRACT_CREATORS = ("gestion",)
CONTRACT_UPDATERS = ("gestion", "commercial")  # commercial: ses clients
EVENT_CREATORS = ("commercial",)  # client avec contrat signé
EVENT_UPDATERS = ("support",)  # son événement
SUPPORT_ASSIGNERS = ("gestion",)
EMPLOYEE_MANAGERS = ("gestion",)

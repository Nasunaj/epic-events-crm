"""Connecting to the database via SQLAlchemy."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load the .env file into environment variables
load_dotenv()

# This is the connection string (connection URL).
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Crée le moteur : l'objet central qui gère le pool de connexions vers
# PostgreSQL. Le moteur est paresseux (lazy). create_engine ne se connecte
# pas tout de suite — il attend la première vraie requête. C'est pourquoi
# cette ligne ne provoque aucune erreur même si le serveur est éteint
# l'erreur n'apparaîtra qu'au premier accès.
# Un seul moteur pour toute l'application (ne pas le recréer à chaque fonction)
engine = create_engine(DB_URL)

# sessionmaker est une fabrique de sessions : un objet qui, quand elle est
# appelée, produit une session branchée sur engine.
# La session est le "carnet de bord" : elle suit les objets que nous
# chargeons/créons et décide à quel moment envoyer INSERT/UPDATE/DELETE à la
# base.
# Pourquoi une fabrique plutôt qu'une session directe? :
# une session n'est pas réutilisables entre plusieurs opérations/utilisateurs:
# nous en ouvrons une par tâche et nous la refermons. La fabrique garantit que
# toutes les sessions sont configurées pareil (même moteur).
SessionLocal = sessionmaker(bind=engine)

# C'est ce qui marque la classe comme « table » aux yeux de SQLAlchemy, qui
# l'enregistre dans son registre de métadonnées.
# Un seul 'Base' pour tout le projet : toutes les entités doivent hériter du
# même, sinon les relations entre tables (Client <-> Contract) ne pourront pas
# se résoudre.
# C'est aussi depuis lui que nous créons les tables :
# Base.metadata.create_all(engine).
Base = declarative_base()

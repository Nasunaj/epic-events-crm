"""Password hashing utilities (Argon2id)."""

from dotenv import load_dotenv
from passlib.context import CryptContext

import jwt
from datetime import datetime, timedelta, timezone
import os

# CryptContext plutôt que argon2 directement : c'est une façade qui gère la
# migration d'algorithmes. deprecated="auto" signifie que si un jour nous
# passons à un schéma plus récent, les anciens hashs restent vérifiables et
# sont de nouveau hachés à la volée à la prochaine connexion réussie.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id (salted automatically)."""
    # Le sel est intégré : pwd_context.hash() génère un sel aléatoire unique
    # et l'incorpore dans la chaîne retournée. Rien à faire, rien à stocker
    # séparément.
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against stored hash."""
    # Renvoie un booléen, jamais une exception : un mauvais mot de passe est un
    # résultat normal (l'utilisateur s'est trompé), pas une erreur système.
    return pwd_context.verify(plain_password, password_hash)


# Load the .env file into environment variables
load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))


def create_token(employee_id: int, role: str) -> str:
    """Create a signed JWT for an authenticated employee.

    The token carries the employee id ('sub' claim) and role, and expires
    after JWT_EXPIRATION_HOURS hours.
    """
    payload = {
        "sub": str(employee_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Verify and decode a JWT. Raises jwt.ExpiredSignatureError or
    jwt.InvalidTokenError on failure."""
    return jwt.decode(
        token,
        JWT_SECRET,  # même secret signature vérifiée
        algorithms=[JWT_ALGORITHM],
    )

"""Password hashing utilities (Argon2id)."""

from passlib.context import CryptContext

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

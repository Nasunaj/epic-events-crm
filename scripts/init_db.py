"""Create all application tables in the PostgreSQL database."""
from epicevents.database import Base, engine
import epicevents.models  # noqa: F401 (enregistre les modèles sur Base)

Base.metadata.create_all(engine)
print("Tables created.")
"""Sanity-check script: builds a full, consistent data graph on a
throwaway in-memory database, then prints every object and relation.

Run from the project root: python scripts/check_models.py
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from epicevents.database import Base
from epicevents.models import Role, Employee, Client, Contract, Event

# Schema SQL
from sqlalchemy.schema import CreateTable

# Database "jettable" en mémoire
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Graph de données
role_com = Role(name="commercial")
role_sup = Role(name="support")
role_ges = Role(name="gestion")

josh = Employee(
    employee_number="E001",
    name="Josh C",
    email="c.josh@epicevents.com",
    password_hash="hash1",
    role=role_com,
)

kate = Employee(
    employee_number="E002",
    name="Kate A",
    email="a.kate@epicevents.com",
    password_hash="hash2",
    role=role_sup,
)

client = Client(
    name="Kevin Casey",
    email="kevin@startup.com",
    phone="+06 08 09 10 45",
    company_name="xxx",
    creation_date=datetime(2026, 9, 30),
    last_update=datetime(2026, 9, 30),
    commercial=josh,
)

contract = Contract(
    client=client,
    commercial=josh,
    total_amount=Decimal("10000.00"),
    remaining_amount=Decimal("5000.00"),
    is_signed=True,
    creation_date=datetime(2023, 5, 1),
)

event = Event(
    contract=contract,
    name="xxxx Party",
    event_date_start=datetime(2026, 10, 1, 13),
    event_date_end=datetime(2026, 10, 2, 2),
    location="1 ..., Paris",
    attendees=75,
    note="DJ",
    support=kate,
)

session.add_all([role_com, role_sup, role_ges, josh, kate, client, contract, event])
session.commit()  # Ici que les FK sont vérifiées et générées

# Visualisation : les objets (__repr__)
print("\n----------REPR----------------")
for obj in (role_com, josh, kate, client, contract, event):
    print(obj)

print("------foreign keys----------")
print(f"client.commercial_id: {client.commercial_id}")
print(f"contract.client_id: {contract.client_id}")
print(f"contract.commercial_id: {contract.commercial_id}")
print(f"event.contract_id: {event.contract_id}")
print(f"event.support_id: {event.support_id}")

# Visualisation : les relations objets
print("\n---------Relation objets----------")
print(f"josh.clients : {[c.name for c in josh.clients]}")
print(f"client.commercial: {client.commercial.name}(id : {client.commercial_id})")
print(f"client.contracts : {[ct.id for ct in client.contracts]}")
print(f"event.contract_id: {event.contract.client.company_name}")
print(f"event.support: {event.support.name}(id:{event.support_id})")
print(f"kate.events : {[ev.id for ev in kate.events]}")
print(f"josh.role : {josh.role.name}(id : {josh.role_id})")
print(contract.event)

for table in Base.metadata.sorted_tables:
    print(f"\n-- {table.name}")
    print(CreateTable(table).compile(engine))

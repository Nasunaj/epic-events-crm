"""Epic events CRM business models.

This module defines the SQLAlchemy ORM models mapping the database tables :
roles, employees, clients, contracts and events
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from epicevents.database import Base


class Role(Base):
    """Role of employee (department)

    Each employee belongs to exactly one role.
    """

    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    employees: Mapped[list["Employee"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"role (id={self.id}, name={self.name})"


class Employee(Base):
    """Collaborator who uses the CRM.

    An employee is authenticated with their email and password and is
    granted permissions depending on their role (department)
    """

    __tablename__ = "employee"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[int] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    # Ne doit pas stocker le mot de passe en clair
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"))
    role: Mapped["Role"] = relationship(back_populates="employees")

    clients: Mapped[list["Client"]] = relationship(
        back_populates="commercial", foreign_keys="Client.commercial_id"
    )
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="commercial", foreign_keys="Contract.commercial_id"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="support", foreign_keys="Event.support_id"
    )

    def __repr__(self) -> str:
        return (
            f"employee (id={self.id}, employee_number={self.employee_number}, "
            f"name={self.name}, email={self.email}, "
            f"role_id={self.role_id})"
        )


class Client(Base):
    """Client company of Epic events

    A client is prospected and created by a sales employee (commercial, who
    remains its commercial contact. Only that employee (or management) may
    update the client's information.
    """

    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    company_name: Mapped[str] = mapped_column(String(100))
    creation_date: Mapped[datetime] = mapped_column(DateTime)
    last_update: Mapped[datetime] = mapped_column(DateTime)
    commercial_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    # object client.commercial will give you the Employee object directly.
    # back_populates establishes the bidirectional link.
    commercial: Mapped["Employee"] = relationship(
        back_populates="clients", foreign_keys=[commercial_id]
    )
    contracts: Mapped[list["Contract"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return (
            f"client (id = {self.id}, name={self.name}, email={self.email}, "
            f"phone={self.phone}, company_name={self.company_name}, "
            f"creation_date={self.creation_date}, "
            f"last_update={self.last_update}, "
            f"commercial_id={self.commercial_id})"
        )


class Contract(Base):
    """A contract linking a client to an organized event

    Created by the management department, a contract stores the
    financial terms (total and remaining amounts) and its signature
    status. An event can only be created once the contract is signed.
    """

    __tablename__ = "contract"
    id: Mapped[int] = mapped_column(primary_key=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_signed: Mapped[bool] = mapped_column(Boolean)
    creation_date: Mapped[datetime] = mapped_column(DateTime)

    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    client: Mapped["Client"] = relationship(
        back_populates="contracts", foreign_keys=[client_id]
    )
    commercial_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    commercial: Mapped["Employee"] = relationship(
        back_populates="contracts", foreign_keys=[commercial_id]
    )
    event: Mapped["Event"] = relationship(back_populates="contract", uselist=False)

    def __repr__(self) -> str:
        return (
            f"contract (id={self.id}, client_id={self.client_id}, "
            f"commercial_id={self.commercial_id}, "
            f"total_amount={self.total_amount}, "
            f"remaining_amount ={self.remaining_amount}, "
            f"is_signed={self.is_signed})"
        )


class Event(Base):
    """An event organized for a signed contract.

    Created by the sales employee once the contract is signed, then
    assigned by management to a support employee who is responsible
    for its organization.
    """

    __tablename__ = "event"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    event_date_start: Mapped[datetime] = mapped_column(DateTime)
    event_date_end: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(500))
    attendees: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(1000))
    contract_id: Mapped[int] = mapped_column(ForeignKey("contract.id"), unique=True)
    contract: Mapped["Contract"] = relationship(
        back_populates="event", foreign_keys=[contract_id]
    )
    support_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"))
    support: Mapped["Employee"] = relationship(
        back_populates="events", foreign_keys=[support_id]
    )

    def __repr__(self) -> str:
        return (
            f"event (id={self.id}, name={self.name}, "
            f"event_date_start={self.event_date_start}) "
        )

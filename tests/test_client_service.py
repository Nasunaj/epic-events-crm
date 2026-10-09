# import pytest

# from epicevents.auth import PermissionDeniedError
from epicevents.services.client_service import list_clients


def test_every_role_reads_all_clients(
    session,
    role_com,
    role_sup,
    gestion,
    commercial,
    support,
    make_employee,
    make_client,
):
    """Per the brief, read access to clients is universal (all roles)."""
    com_a = make_employee(
        employee_number="E101",
        email="a.a@epicevents.com",
        name="Al A",
        role_name="commercial",
    )
    com_b = make_employee(
        employee_number="E102",
        email="b.b@epicevents.com",
        name="Bob B",
        role_name="commercial",
    )
    client_a = make_client(commercial=com_a, email="ca@client.com", name="Client A")
    client_b = make_client(commercial=com_b, email="cb@client.com", name="Client B")

    for _ in (gestion, commercial, support):
        clients = list_clients(session)
        assert {c.id for c in clients} == {client_a.id, client_b.id}


# def test_commercial_sees_only_own_clients(session, make_employee, make_client,
#                                           role_com):
#     """A commercial sees their own client, never another commercial's."""
#     # Arrangement : deux commerciaux, un client chacun
#     com_a = make_employee(employee_number="E101", email="a.a@epicevents.com",
#                            name="Al A", role_name="commercial")
#     com_b = make_employee(employee_number="E102", email="b.b@epicevents.com",
#                            name="Bob B", role_name="commercial")
#     client_a = make_client(commercial=com_a, email="ca@client.com",
#                            name="Client A")
#     client_b = make_client(commercial=com_b, email="cb@client.com",
#                            name="Client B")
#     seen_by_a = list_clients(session, com_a)
#     assert client_a in seen_by_a
#     assert client_b not in seen_by_a
#
# def test_gestion_sees_all_clients(
#     session, role_com, gestion, make_employee, make_client
# ):
#     """Gestion sees every client, whoever the commercial is."""
#     com_a = make_employee(
#         employee_number="E101", email="a.a@epicevents.com",
#         name="Al A", role_name="commercial",
#     )
#     com_b = make_employee(
#         employee_number="E102", email="b.b@epicevents.com",
#         name="Bob B", role_name="commercial",
#     )
#     client_a = make_client(
#         commercial=com_a, email="ca@client.com", name="Client A"
#     )
#     client_b = make_client(
#         commercial=com_b, email="cb@client.com", name="Client B"
#     )
#
#     clients = list_clients(session, gestion)
#     assert len(clients) == 2
#     assert {c.id for c in clients} == {client_a.id, client_b.id}
#
# def test_support_cannot_list_clients(session, support):
#     """Test support cannot list clients."""
#     with pytest.raises(PermissionDeniedError):
#         list_clients(session, support)

from neo4j import GraphDatabase

from app.config import get_settings

settings = get_settings()

_auth_parts = settings.neo4j_auth.split("/", 1)
if len(_auth_parts) != 2:
    raise ValueError(
        f"NEO4J_AUTH must be in 'user/password' format, got: '{settings.neo4j_auth}'"
    )
_user, _password = _auth_parts

sync_neo4j_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(_user, _password),
)

import os
import yaml


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_compose(filename):
    with open(os.path.join(PROJECT_ROOT, "docker", filename)) as f:
        return yaml.safe_load(f)


def test_production_compose_has_7_services():
    compose = load_compose("docker-compose.yml")
    services = list(compose["services"].keys())
    assert len(services) == 7
    expected = {"app", "web", "postgres", "neo4j", "qdrant", "redis", "ollama"}
    assert set(services) == expected


def test_dev_compose_has_5_services():
    compose = load_compose("docker-compose.dev.yml")
    services = list(compose["services"].keys())
    assert len(services) == 5
    expected = {"postgres", "neo4j", "qdrant", "redis", "ollama"}
    assert set(services) == expected


def test_dev_compose_exposes_ports():
    compose = load_compose("docker-compose.dev.yml")
    services = compose["services"]
    assert "5432:5432" in services["postgres"]["ports"]
    assert "7474:7474" in services["neo4j"]["ports"]
    assert "7687:7687" in services["neo4j"]["ports"]
    assert "6333:6333" in services["qdrant"]["ports"]
    assert "6379:6379" in services["redis"]["ports"]
    assert "11434:11434" in services["ollama"]["ports"]


def test_production_compose_has_named_volumes():
    compose = load_compose("docker-compose.yml")
    volumes = list(compose["volumes"].keys())
    expected = {"postgres-data", "neo4j-data", "qdrant-data", "redis-data", "ollama-models"}
    assert set(volumes) == expected


def test_production_compose_has_bridge_network():
    compose = load_compose("docker-compose.yml")
    networks = compose["networks"]
    assert "osint-network" in networks
    assert networks["osint-network"]["driver"] == "bridge"


def test_all_services_on_same_network():
    compose = load_compose("docker-compose.yml")
    for name, service in compose["services"].items():
        assert "osint-network" in service.get("networks", []), f"Service {name} not on osint-network"

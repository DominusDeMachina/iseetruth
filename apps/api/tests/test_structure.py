import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_monorepo_root_files():
    assert os.path.exists(os.path.join(PROJECT_ROOT, "package.json"))
    assert os.path.exists(os.path.join(PROJECT_ROOT, "pnpm-workspace.yaml"))
    assert os.path.exists(os.path.join(PROJECT_ROOT, ".gitignore"))
    assert os.path.exists(os.path.join(PROJECT_ROOT, ".env.example"))
    assert os.path.exists(os.path.join(PROJECT_ROOT, "storage", ".gitkeep"))


def test_frontend_scaffold():
    web_dir = os.path.join(PROJECT_ROOT, "apps", "web")
    assert os.path.exists(os.path.join(web_dir, "package.json"))
    assert os.path.exists(os.path.join(web_dir, "vite.config.ts"))
    assert os.path.exists(os.path.join(web_dir, "tsconfig.json"))
    assert os.path.exists(os.path.join(web_dir, "components.json"))
    assert os.path.exists(os.path.join(web_dir, "index.html"))
    assert os.path.exists(os.path.join(web_dir, "src", "main.tsx"))
    assert os.path.exists(os.path.join(web_dir, "src", "globals.css"))
    assert os.path.exists(os.path.join(web_dir, "src", "routes", "__root.tsx"))
    assert os.path.exists(os.path.join(web_dir, "src", "routes", "index.tsx"))
    assert os.path.exists(os.path.join(web_dir, "src", "routes", "investigations", "$id.tsx"))
    assert os.path.exists(os.path.join(web_dir, "src", "routes", "status.tsx"))
    assert os.path.exists(os.path.join(web_dir, "src", "lib", "api-client.ts"))
    assert os.path.exists(os.path.join(web_dir, "src", "lib", "api-types.generated.ts"))


def test_backend_scaffold():
    api_dir = os.path.join(PROJECT_ROOT, "apps", "api")
    assert os.path.exists(os.path.join(api_dir, "pyproject.toml"))
    assert os.path.exists(os.path.join(api_dir, "uv.lock"))
    assert os.path.exists(os.path.join(api_dir, "alembic.ini"))
    assert os.path.exists(os.path.join(api_dir, "app", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "main.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "config.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "api", "v1", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "schemas", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "models", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "services", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "worker", "tasks", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "db", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "app", "llm", "__init__.py"))
    assert os.path.exists(os.path.join(api_dir, "migrations", "env.py"))
    assert os.path.exists(os.path.join(api_dir, "migrations", "versions"))


def test_docker_files():
    docker_dir = os.path.join(PROJECT_ROOT, "docker")
    assert os.path.exists(os.path.join(docker_dir, "docker-compose.yml"))
    assert os.path.exists(os.path.join(docker_dir, "docker-compose.dev.yml"))
    assert os.path.exists(os.path.join(docker_dir, "app.Dockerfile"))
    assert os.path.exists(os.path.join(docker_dir, "web.Dockerfile"))
    assert os.path.exists(os.path.join(docker_dir, "nginx.conf"))


def test_scripts():
    scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
    assert os.path.exists(os.path.join(scripts_dir, "generate-api-types.sh"))
    assert os.path.exists(os.path.join(scripts_dir, "dev.sh"))
    assert os.access(os.path.join(scripts_dir, "generate-api-types.sh"), os.X_OK)
    assert os.access(os.path.join(scripts_dir, "dev.sh"), os.X_OK)

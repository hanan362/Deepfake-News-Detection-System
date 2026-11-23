"""Static checks on the deployment files. They do not start Docker (nothing here can), so they only catch the mistakes
that can be found by reading: files that disagree with each other, missing variables, wrong paths."""
import re
from pathlib import Path

import pytest

from app.core.config import Settings

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
DOCKER_ONLY = {"INSTALL_ML", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "WEB_PORT"}


def _instructions(path: Path) -> list[str]:
    return [ln.rstrip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def _env_keys(path: Path) -> set[str]:
    keys = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#?\s*([A-Z][A-Z0-9_]+)=", ln)
        if m:
            keys.add(m.group(1))
    return keys


def test_root_dockerfile_matches_the_deployment_dockerfile():
    assert _instructions(ROOT / "Dockerfile") == _instructions(ROOT / "deployment" / "docker" / "backend.Dockerfile")


def test_compose_points_at_files_that_exist():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert set(compose["services"]) == {"db", "backend", "frontend"}
    for name in ("backend", "frontend"):
        build = compose["services"][name]["build"]
        assert (ROOT / build["context"] / build["dockerfile"]).is_file()
    assert (ROOT / "deployment" / "nginx" / "nginx.conf").is_file()


def test_production_settings_in_compose_are_safe():
    env = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["backend"]["environment"]
    assert env["ENVIRONMENT"] == "production"
    assert env["AUTO_CREATE_TABLES"] == "false"          # the schema comes from migrations
    assert env["EXPOSE_RESET_TOKEN"] == "false"
    assert str(env["SECRET_KEY"]).startswith("${SECRET_KEY:?")  # compose refuses to start without a real key
    assert "${POSTGRES_PASSWORD}" in env["DATABASE_URL"]


def test_every_variable_compose_reads_is_documented_in_env_example():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    used = set(re.findall(r"\$\{([A-Z][A-Z0-9_]+)", text))
    assert used <= _env_keys(ROOT / ".env.example"), used - _env_keys(ROOT / ".env.example")


def test_env_example_names_are_real_settings_and_hold_no_secret():
    fields = {name.upper() for name in Settings.model_fields}
    unknown = _env_keys(ROOT / ".env.example") - fields - DOCKER_ONLY
    assert not unknown, f"not a setting: {sorted(unknown)}"
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "SECRET_KEY=change-me-in-production" in text
    assert re.search(r"^ADMIN_PASSWORD=$", text, re.M) and re.search(r"^EXPOSE_RESET_TOKEN=false$", text, re.M)


def test_nginx_forwards_the_api_and_serves_the_single_page_app():
    conf = (ROOT / "deployment" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /api/" in conf and "proxy_pass http://backend:8000" in conf
    assert "try_files $uri /index.html" in conf


def test_nginx_lets_the_largest_allowed_video_through():
    """Found by running the Docker stack: a 12 MB nginx limit made videos above 12 MB fail with nginx's own HTML error page."""
    import re

    from app.core.config import get_settings

    conf = (ROOT / "deployment" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    limit_mb = int(re.search(r"client_max_body_size\s+(\d+)m;", conf).group(1))
    assert limit_mb > get_settings().max_video_mb
    timeout_s = int(re.search(r"proxy_read_timeout\s+(\d+)s;", conf).group(1))
    assert timeout_s >= 120


def test_powershell_scripts_only_point_at_files_and_folders_that_exist():
    """The PowerShell scripts could not be run in the build environment, so this only checks (statically) that every
    relative path they name exists and that braces and quotes are balanced. It does not prove the scripts run."""
    import re

    scripts = sorted((ROOT / "scripts").rglob("*.ps1"))
    assert len(scripts) >= 8
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), script.name
        assert text.count("(") == text.count(")"), script.name
        assert text.count('"') % 2 == 0, script.name
        for rel in re.findall(r"(?<![\w.])((?:backend|frontend|ai_models|scripts|deployment)(?:\\[\w.\-]+)+\.(?:py|txt|ps1|sh))", text):
            assert (ROOT / rel.replace("\\", "/")).is_file(), f"{script.name} names {rel}"
        for rel in re.findall(r"\.env\.example", text):
            assert (ROOT / rel).is_file()


def test_the_model_download_step_is_wired_into_the_ml_install_and_can_be_skipped():
    py = ROOT / "scripts" / "setup" / "download_models.py"
    assert py.is_file()
    for wrapper in ("download_models.sh", "download_models.ps1"):
        assert "download_models.py" in (ROOT / "scripts" / "setup" / wrapper).read_text(encoding="utf-8")
    sh = (ROOT / "scripts" / "setup" / "install_ml.sh").read_text(encoding="utf-8")
    ps = (ROOT / "scripts" / "setup" / "install_ml.ps1").read_text(encoding="utf-8")
    assert "download_models.py" in sh and "SKIP_MODELS" in sh
    assert "download_models.py" in ps and "SkipModels" in ps
    # A failed download must not fail the install: the models are then fetched on first use.
    assert "|| echo" in sh
    assert "Write-Warning" in ps


def test_the_download_script_refuses_unknown_names_before_touching_the_network():
    import subprocess
    import sys

    done = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "setup" / "download_models.py"), "banana"],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 2
    assert "Unknown model name" in done.stdout


def test_runtime_folders_exist_in_a_fresh_clone():
    for rel in ("storage/uploads", "storage/reports", "storage/temporary", "datasets/raw", "datasets/processed", "ai_models/checkpoints"):
        assert (ROOT / rel / ".gitkeep").is_file(), rel

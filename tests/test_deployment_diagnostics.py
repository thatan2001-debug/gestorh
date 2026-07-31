from pathlib import Path

from utils.deployment_diagnostics import DIAGNOSTIC_MARKER, deployment_metadata


def test_deployment_metadata_reads_render_environment(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_BRANCH", "main")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("RENDER_GIT_REPO_SLUG", "thatan2001-debug/gestorh")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://rh-facil.onrender.com")
    monkeypatch.setenv("RENDER_SERVICE_NAME", "rh-facil")

    assert deployment_metadata() == {
        "branch": "main",
        "commit": "abc123",
        "repository": "thatan2001-debug/gestorh",
        "external_url": "https://rh-facil.onrender.com",
        "service_name": "rh-facil",
    }


def test_diagnostics_source_contains_selector_and_marker():
    source = (
        Path(__file__).parents[1] / "utils" / "deployment_diagnostics.py"
    ).read_text(encoding="utf-8")
    assert DIAGNOSTIC_MARKER in source
    assert "¿Los aportes del periodo final ya fueron descontados en nómina? *" in source
    assert "descontados_completamente" in source
    assert "descontados_parcialmente" in source
    assert "no_descontados" in source
    assert "revision_manual" in source
    assert "Salud ya descontada ($)" in source
    assert "Pensión ya descontada ($)" in source


def test_app_entrypoint_invokes_deployment_diagnostics():
    source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "from utils.deployment_diagnostics import mostrar_diagnostico_despliegue" in source
    assert "if mostrar_diagnostico_despliegue():" in source
    assert "st.stop()" in source


def test_render_blueprint_pins_main_and_commit_deploys():
    source = (Path(__file__).parents[1] / "render.yaml").read_text(encoding="utf-8")
    assert "branch: main" in source
    assert "autoDeployTrigger: commit" in source
    assert "healthCheckPath: /_stcore/health" in source

"""Aplica de forma idempotente la instrumentación de despliegue a la app."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
RENDER = ROOT / "render.yaml"


def patch_app() -> None:
    source = APP.read_text(encoding="utf-8")
    import_line = "from utils.deployment_diagnostics import mostrar_diagnostico_despliegue"
    block = (
        "\n# Diagnóstico seguro del proceso activo de Render. Solo se muestra con\n"
        "# ?deployment_diagnostics=1 y no expone secretos.\n"
        f"{import_line}\n"
        "if mostrar_diagnostico_despliegue():\n"
        "    st.stop()\n"
    )
    if import_line not in source:
        anchor = "st.markdown(CSS, unsafe_allow_html=True)\n"
        if anchor not in source:
            raise RuntimeError("No se encontró el punto de inserción en app.py")
        source = source.replace(anchor, anchor + block, 1)
        APP.write_text(source, encoding="utf-8")


def patch_render() -> None:
    source = RENDER.read_text(encoding="utf-8")
    if "repo: https://github.com/thatan2001-debug/gestorh" not in source:
        source = source.replace(
            "    runtime: python\n",
            "    runtime: python\n"
            "    repo: https://github.com/thatan2001-debug/gestorh\n"
            "    branch: main\n"
            "    autoDeployTrigger: commit\n"
            "    healthCheckPath: /_stcore/health\n",
            1,
        )
    RENDER.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    patch_app()
    patch_render()

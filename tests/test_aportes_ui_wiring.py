from pathlib import Path


def test_formulario_liquidacion_expone_y_conecta_conciliacion_aportes():
    source = (Path(__file__).parents[1] / "utils" / "pantalla_documentos.py").read_text(encoding="utf-8")
    assert "¿Los aportes del periodo final ya fueron descontados en nómina? *" in source
    assert "descontados_completamente" in source
    assert "descontados_parcialmente" in source
    assert "no_descontados" in source
    assert "revision_manual" in source
    assert '"Estado aportes periodo final": conf.get("estado_aportes_periodo_final", "")' in source
    assert '"Aporte salud ya descontado": conf.get("aporte_salud_ya_descontado", 0)' in source
    assert '"Aporte pension ya descontado": conf.get("aporte_pension_ya_descontado", 0)' in source
    assert '"Pagos previos confirmados": bool(conf.get("pagos_previos_confirmados"))' in source
    assert '"Novedades confirmadas": bool(conf.get("novedades_confirmadas"))' in source
    assert 'st.error(f"{h.codigo}' not in source
    assert 'st.warning(f"{h.codigo}' not in source

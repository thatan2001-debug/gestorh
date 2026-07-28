"""Prueba visual responsiva de la pantalla de autenticación con Playwright."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


APP_URL = "http://127.0.0.1:8501"
VIEWPORTS = (375, 768, 1024, 1440)
ARTIFACTS = Path("test-artifacts")


def _logo_metrics(page: Page) -> dict[str, float | int | str]:
    image = page.locator('[data-testid="stImage"] img').first
    image.wait_for(state="visible", timeout=60_000)

    metrics = image.evaluate(
        """img => {
            const rect = img.getBoundingClientRect();
            const style = getComputedStyle(img);
            return {
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                renderedWidth: rect.width,
                renderedHeight: rect.height,
                left: rect.left,
                right: rect.right,
                objectFit: style.objectFit,
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity
            };
        }"""
    )

    assert metrics["naturalWidth"] >= 600
    assert metrics["naturalHeight"] >= 150
    assert metrics["renderedWidth"] > 0
    assert metrics["renderedHeight"] > 0

    natural_ratio = metrics["naturalWidth"] / metrics["naturalHeight"]
    rendered_ratio = metrics["renderedWidth"] / metrics["renderedHeight"]
    assert abs(natural_ratio - rendered_ratio) < 0.05

    viewport_width = page.viewport_size["width"]
    assert metrics["left"] >= -1
    assert metrics["right"] <= viewport_width + 1
    assert metrics["objectFit"] != "cover"
    assert metrics["visibility"] == "visible"
    assert float(metrics["opacity"]) > 0

    horizontal = page.evaluate(
        """() => ({
            viewport: document.documentElement.clientWidth,
            scroll: document.documentElement.scrollWidth
        })"""
    )
    assert horizontal["scroll"] <= horizontal["viewport"] + 1

    return metrics


def _verify_tabs(page: Page, width: int) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    login_tab = page.get_by_role("tab", name="🔐 Ingresar")
    register_tab = page.get_by_role("tab", name="✨ Crear cuenta")
    login_tab.wait_for(state="visible", timeout=60_000)
    register_tab.wait_for(state="visible", timeout=60_000)

    for name, tab in (("login", login_tab), ("register", register_tab)):
        tab.click()
        page.wait_for_timeout(350)
        metrics = _logo_metrics(page)
        screenshot = ARTIFACTS / f"auth-{width}-{name}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        results.append({"viewport": width, "tab": name, "logo": metrics})

    return results


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    all_results: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": 1000})
                page.goto(APP_URL, wait_until="networkidle", timeout=90_000)
                all_results.extend(_verify_tabs(page, width))
                page.close()
        finally:
            browser.close()

    report = ARTIFACTS / "responsive-results.json"
    report.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(json.dumps(all_results, indent=2))
    print(f"Responsive authentication checks passed: {len(all_results)} scenarios")


if __name__ == "__main__":
    main()

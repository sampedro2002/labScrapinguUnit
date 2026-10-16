from pathlib import Path

from playwright.sync_api import sync_playwright


_playwright = None
_context = None


def get_page(url):
    """Abre Chrome usando el perfil local, incluida la sesión ya iniciada."""
    global _playwright, _context

    profile_dir = Path(__file__).with_name(".chrome_profile")

    _playwright = sync_playwright().start()
    try:
        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
        )
        page = _context.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4000)
        if not any(cookie.get("name") == "sessionid" for cookie in _context.cookies()):
            print("Inicia sesión en Instagram en la ventana de Chrome que se abrió.")
            input("Cuando termines, presiona Enter para continuar (o Enter para seguir sin sesión): ")
        return page, _context
    except Exception as error:
        close_browser()
        raise RuntimeError(
            "No se pudo abrir Chrome para el scraper. Cierra la ventana anterior del scraper "
            "y vuelve a ejecutar el programa."
        ) from error


def close_browser():
    global _playwright, _context
    if _context:
        _context.close()
        _context = None
    if _playwright:
        _playwright.stop()
        _playwright = None

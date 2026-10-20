import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

_playwright = None
_context = None


def _load_env_file():
    """Carga variables desde el archivo .env si existe."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def get_env_cookies():
    """Obtiene cookies desde el archivo .env o variables de entorno."""
    _load_env_file()
    cookies = []
    seen = set()

    # 1. Cadena de cookies o JSON en INSTAGRAM_COOKIES o COOKIES
    raw_cookies = os.getenv("INSTAGRAM_COOKIES") or os.getenv("COOKIES")
    if raw_cookies:
        raw_cookies = raw_cookies.strip()
        if (raw_cookies.startswith("[") and raw_cookies.endswith("]")) or (
            raw_cookies.startswith("{") and raw_cookies.endswith("}")
        ):
            try:
                parsed = json.loads(raw_cookies)
                if isinstance(parsed, dict):
                    parsed = [parsed]
                for item in parsed:
                    name = item.get("name")
                    value = item.get("value")
                    if name and value:
                        cookies.append({
                            "name": str(name),
                            "value": str(value),
                            "domain": ".instagram.com",
                            "path": "/",
                        })
                        seen.add(str(name).lower())
            except Exception:
                pass

        if not cookies:
            for item in raw_cookies.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k:
                        cookies.append({
                            "name": k,
                            "value": v,
                            "domain": ".instagram.com",
                            "path": "/",
                        })
                        seen.add(k.lower())

    # 2. Variables individuales (SESSIONID, etc.)
    var_map = [
        ("sessionid", ["SESSIONID", "SESSION_ID", "INSTAGRAM_SESSIONID"]),
        ("ds_user_id", ["DS_USER_ID", "INSTAGRAM_DS_USER_ID"]),
        ("csrftoken", ["CSRFTOKEN", "INSTAGRAM_CSRFTOKEN"]),
        ("mid", ["MID", "INSTAGRAM_MID"]),
        ("ig_did", ["IG_DID", "INSTAGRAM_IG_DID"]),
    ]

    for cookie_name, env_names in var_map:
        if cookie_name.lower() in seen:
            continue
        for env_name in env_names:
            val = os.getenv(env_name)
            if val:
                cookies.append({
                    "name": cookie_name,
                    "value": val.strip().strip('"').strip("'"),
                    "domain": ".instagram.com",
                    "path": "/",
                })
                seen.add(cookie_name.lower())
                break

    return cookies


def get_page(url):
    """Abre Chrome usando el perfil local o las cookies cargadas desde .env."""
    global _playwright, _context

    profile_dir = Path(__file__).with_name(".chrome_profile")

    _playwright = sync_playwright().start()
    try:
        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
        )

        env_cookies = get_env_cookies()
        if env_cookies:
            _context.add_cookies(env_cookies)

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

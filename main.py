from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError, sync_playwright

LIMIT = 25
PROFILE_URL = "https://www.instagram.com/{username}/"
USER_PATH = re.compile(r"^/([A-Za-z0-9._]+)/?$")
_SCALE = {"k": 1_000, "m": 1_000_000}
APP_ID = "936619743392459"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

_FETCH_JS = """
async ([url, appId]) => {
    const response = await fetch(url, {
        credentials: "include",
        headers: {"X-IG-App-ID": appId, "X-Requested-With": "XMLHttpRequest"},
    });
    if (!response.ok) return null;
    try { return await response.json(); } catch (e) { return null; }
}
"""

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

    def add(name, value):
        name_clean = str(name).strip()
        if name_clean.lower() not in seen and value:
            seen.add(name_clean.lower())
            cookies.append({
                "name": name_clean,
                "value": str(value).strip().strip('"').strip("'"),
                "domain": ".instagram.com",
                "path": "/",
            })

    # 1. Cadena de cookies o JSON en INSTAGRAM_COOKIES o COOKIES
    raw_cookies = os.getenv("INSTAGRAM_COOKIES") or os.getenv("COOKIES")
    if raw_cookies:
        raw_cookies = raw_cookies.strip()
        if (raw_cookies.startswith("[") and raw_cookies.endswith("]")) or (
            raw_cookies.startswith("{") and raw_cookies.endswith("}")
        ):
            try:
                parsed = json.loads(raw_cookies)
                for item in (parsed if isinstance(parsed, list) else [parsed]):
                    add(item.get("name"), item.get("value"))
            except Exception:
                pass

        if not cookies:
            for item in raw_cookies.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    add(k, v)

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
            if v := os.getenv(env_name):
                add(cookie_name, v)
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

        if env_cookies := get_env_cookies():
            _context.add_cookies(env_cookies)

        page = _context.pages[0] if _context.pages else _context.new_page()
        page.goto(url, timeout=60000)
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


def safe_goto(page, url, attempts=3, timeout=60000):
    for i in range(attempts):
        try:
            page.goto(url, timeout=timeout, wait_until="commit")
            return
        except PlaywrightError as e:
            if "interrupted by another navigation" not in str(e) or i == attempts - 1:
                raise
            page.wait_for_timeout(2000)


def scroll_collect(page, container, extract, limit, max_iters=40, step=None, pause=0.8):
    seen = set()
    items = []
    unchanged = 0

    for _ in range(max_iters):
        before = len(items)
        for item in extract():
            if item not in seen:
                seen.add(item)
                items.append(item)
                if len(items) >= limit:
                    break
        if len(items) >= limit:
            break

        unchanged = unchanged + 1 if len(items) == before else 0
        if unchanged >= 5:
            break

        if step is not None:
            container.evaluate(f"el => el.scrollBy(0, {step})")
        else:
            page.evaluate("window.scrollBy(0, Math.max(500, window.innerHeight))")

        time.sleep(pause)

    return items[:limit]


# --- Métodos de parseo ---

def parse_number(text):
    if not text:
        return None
    m = re.match(r"([\d.]+)([km]?)", text.strip().lower().replace(",", ""))
    if not m:
        return None
    return int(float(m.group(1)) * _SCALE.get(m.group(2), 1))


def extract_stats(meta):
    meta = meta.replace(",", "")
    pats = {
        "followers": r"([\d.]+[km]?)\s+(seguidores|followers)",
        "following": r"([\d.]+[km]?)\s+(siguiendo|following)",
        "posts":     r"([\d.]+[km]?)\s+(publicaciones|posts)",
    }
    return {
        key: (parse_number(m.group(1)) if (m := re.search(pat, meta, re.I)) else None)
        for key, pat in pats.items()
    }


# --- Métodos de perfil ---

def run_perfil(page, username):
    safe_goto(page, PROFILE_URL.format(username=username))
    meta_loc = page.locator("meta[name='description']")
    try:
        meta_loc.wait_for(state="attached", timeout=15000)
    except PlaywrightTimeoutError:
        return None
    page.wait_for_timeout(1500)
    meta = meta_loc.get_attribute("content")
    if not meta:
        return None
    bio = page.locator("header section div[dir='auto']").all_inner_texts()
    data = {
        "username": username,
        "bio": "\n".join(t.strip() for t in bio if t.strip()) or None,
    }
    data.update(extract_stats(meta))
    print(data)
    return data


# --- Métodos de colecciones (seguidores y seguidos) ---

def _open_connection_list(page, username, kind):
    safe_goto(page, PROFILE_URL.format(username=username))
    page.locator("header").wait_for(state="visible", timeout=15000)
    link = page.locator(f'header a[href*="{kind}"]').first
    try:
        link.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        labels = ("seguidores", "followers") if kind == "followers" else ("seguidos", "following")
        link = None
        for candidate in page.locator("header a").all():
            text = (candidate.inner_text() or "").lower()
            if any(label in text for label in labels):
                link = candidate
                break
        if link is None:
            return None
    link.click()
    dialog = page.locator('div[role="dialog"]')
    try:
        dialog.wait_for(state="visible", timeout=10000)
        dialog.locator("a").first.wait_for(state="visible", timeout=10000)
        return dialog
    except PlaywrightTimeoutError:
        return None


def _scrollable_container(dialog):
    divs = dialog.locator("div")
    dimensions = divs.evaluate_all(
        "els => els.map(el => el.scrollHeight - el.clientHeight)"
    )
    candidates = [
        (difference, index)
        for index, difference in enumerate(dimensions)
        if difference > 80
    ]
    if not candidates:
        return dialog
    _, index = max(candidates)
    return divs.nth(index)


def _collect_users(page, username, kind, limit):
    dialog = _open_connection_list(page, username, kind)
    if dialog is None:
        return []

    container = _scrollable_container(dialog)

    def extract():
        links = dialog.locator("a").evaluate_all("els => els.map(a => a.href)")
        return [
            m.group(1)
            for href in links
            if (m := USER_PATH.match(urlparse(href or "").path))
            and m.group(1).lower() != username.lower()
        ]

    try:
        return scroll_collect(
            page,
            container,
            extract,
            limit,
            max_iters=80,
            step="Math.max(400, el.clientHeight * 0.8)",
        )
    finally:
        page.keyboard.press("Escape")


def run_followers(page, username, limit=25):
    return _collect_users(page, username, "followers", limit)


def run_following(page, username, limit=25):
    return _collect_users(page, username, "following", limit)


# --- Métodos de publicaciones y comentarios ---

def shortcode_to_media_id(shortcode):
    media_id = 0
    for char in shortcode:
        media_id = media_id * 64 + ALPHABET.index(char)
    return media_id


def _api_get(page, path):
    return page.evaluate(_FETCH_JS, [f"https://www.instagram.com{path}", APP_ID])


def _collect_shortcodes(page, username, limit):
    safe_goto(page, PROFILE_URL.format(username=username))
    page.locator("header").wait_for(state="visible", timeout=15000)

    def extract():
        hrefs = page.locator('a[href*="/p/"], a[href*="/reel/"]').evaluate_all(
            "els => els.map(a => a.getAttribute('href'))"
        )
        return [
            parts[-1]
            for href in hrefs
            if len(parts := [part for part in (href or "").split("/") if part]) >= 2
            and parts[-2] in ("p", "reel")
        ]

    return scroll_collect(page, page, extract, limit)


def _fetch_comments(page, media_id, limit):
    comments = []
    min_id = None
    while len(comments) < limit:
        path = f"/api/v1/media/{media_id}/comments/?can_support_threading=true"
        if min_id:
            path += f"&min_id={min_id}"
        payload = _api_get(page, path)
        if not payload:
            break
        for comment in payload.get("comments", []):
            comments.append({
                "username": (comment.get("user") or {}).get("username"),
                "text": comment.get("text", ""),
            })
            if len(comments) >= limit:
                break
        min_id = payload.get("next_min_id")
        if not min_id:
            break
        time.sleep(0.8)
    return comments


def _post_data(page, shortcode, comments_limit):
    media_id = shortcode_to_media_id(shortcode)
    payload = _api_get(page, f"/api/v1/media/{media_id}/info/")
    items = (payload or {}).get("items") or []
    if not items:
        return None
    item = items[0]

    timestamp = item.get("taken_at")
    views = next(
        (item[key] for key in ("play_count", "ig_play_count", "view_count") if item.get(key) is not None),
        "N/A",
    )
    post = {
        "shortcode": shortcode,
        "url": f"https://www.instagram.com/p/{shortcode}/",
        "caption": ((item.get("caption") or {}).get("text") or "").strip() or "Sin texto",
        "likes": item.get("like_count"),
        "comments_count": item.get("comment_count"),
        "views": views,
        "timestamp": timestamp,
        "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp else None,
    }
    if comments_limit > 0:
        post["comments"] = _fetch_comments(page, media_id, comments_limit)
    return post


def run_posts(page, username, limit=25, comments_limit=0):
    posts = []
    for shortcode in _collect_shortcodes(page, username, limit):
        try:
            post = _post_data(page, shortcode, comments_limit)
        except Exception as error:
            print(f"No se pudo leer la publicación {shortcode}: {error}")
            continue
        if post:
            posts.append(post)
        time.sleep(0.8)
    return posts


# --- Ejecución principal ---

def main():
    username = input("Usuario de Instagram: ").strip().lstrip("@").strip("/")
    if not username:
        print("Debes escribir un usuario.")
        return

    page, _ = get_page("https://www.instagram.com/")
    try:
        try:
            data = run_perfil(page, username)
        except Exception as error:
            print(f"No se pudo cargar el perfil de Instagram: {error}")
            return
        if data is None:
            print("No se pudieron obtener los datos del perfil.")
            return

        for label, key, scraper, limit in (
            ("seguidores", "followers_list", run_followers, LIMIT),
            ("seguidos", "following_list", run_following, LIMIT),
            ("publicaciones", "publications",
             lambda p, u, limit: run_posts(p, u, limit, LIMIT), LIMIT),
        ):
            print(f"Obteniendo hasta {limit} {label}...")
            try:
                data[key] = scraper(page, username, limit=limit)
                print(f"Obtenidos: {len(data[key])}")
            except Exception as error:
                data[key] = []
                print(f"No se pudieron obtener {label}: {error}")

        output_file = f"{username}_data.json"
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"Datos guardados en {output_file}")
    finally:
        close_browser()


if __name__ == "__main__":
    main()

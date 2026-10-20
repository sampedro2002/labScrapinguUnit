import time
from datetime import datetime

from colecciones import PROFILE_URL

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


def shortcode_to_media_id(shortcode):
    media_id = 0
    for char in shortcode:
        media_id = media_id * 64 + ALPHABET.index(char)
    return media_id


def _api_get(page, path):
    return page.evaluate(_FETCH_JS, [f"https://www.instagram.com{path}", APP_ID])


def _collect_shortcodes(page, username, limit):
    page.goto(PROFILE_URL.format(username=username), wait_until="commit", timeout=60000)
    page.locator("header").wait_for(state="visible", timeout=15000)
    shortcodes = []
    unchanged = 0

    for _ in range(40):
        hrefs = page.locator('a[href*="/p/"], a[href*="/reel/"]').evaluate_all(
            "els => els.map(a => a.getAttribute('href'))"
        )
        before = len(shortcodes)
        for href in hrefs:
            parts = [part for part in (href or "").split("/") if part]
            if len(parts) >= 2 and parts[-2] in ("p", "reel") and parts[-1] not in shortcodes:
                shortcodes.append(parts[-1])
        if len(shortcodes) >= limit:
            break
        unchanged = unchanged + 1 if len(shortcodes) == before else 0
        if unchanged >= 5:
            break
        page.evaluate("window.scrollBy(0, Math.max(500, window.innerHeight))")
        time.sleep(0.8)

    return shortcodes[:limit]


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

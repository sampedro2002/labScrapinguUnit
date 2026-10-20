import re
import time
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


PROFILE_URL = "https://www.instagram.com/{username}/"
USER_PATH = re.compile(r"^/([A-Za-z0-9._]+)/?$")


def _open_connection_list(page, username, kind):
    page.goto(PROFILE_URL.format(username=username), wait_until="commit", timeout=60000)
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

    users = []
    seen = set()
    container = _scrollable_container(dialog)
    unchanged = 0
    try:
        for _ in range(80):
            links = dialog.locator("a").evaluate_all("els => els.map(a => a.href)")
            before = len(users)
            for href in links:
                path = urlparse(href or "").path
                match = USER_PATH.match(path)
                if match and match.group(1).lower() != username.lower():
                    candidate = match.group(1)
                    if candidate.lower() not in seen:
                        seen.add(candidate.lower())
                        users.append(candidate)
                        if len(users) >= limit:
                            break
            if len(users) >= limit:
                break

            unchanged = unchanged + 1 if len(users) == before else 0
            if unchanged >= 5:
                break
            container.evaluate("el => el.scrollBy(0, Math.max(400, el.clientHeight * 0.8))")
            time.sleep(0.8)
    finally:
        page.keyboard.press("Escape")
    return users[:limit]


def run_followers(page, username, limit=25):
    return _collect_users(page, username, "followers", limit)


def run_following(page, username, limit=25):
    return _collect_users(page, username, "following", limit)



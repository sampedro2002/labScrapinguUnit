from parser import extract_stats
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def run_perfil(page, username):
    profile_url = f"https://www.instagram.com/{username}/"
    for attempt in range(3):
        try:
            page.goto(profile_url, timeout=60000, wait_until="commit")
            break
        except PlaywrightError as error:
            if "interrupted by another navigation" not in str(error) or attempt == 2:
                raise
            page.wait_for_timeout(2000)

    meta_locator = page.locator("meta[name='description']")
    try:
        meta_locator.wait_for(state="attached", timeout=15000)
    except PlaywrightTimeoutError:
        return None
    page.wait_for_timeout(1500)
    meta = meta_locator.get_attribute("content")
    if not meta:
        return None
    bio_items = page.locator("header section div[dir='auto']").all_inner_texts()
    data = {
        "username": username,
        "biography": "\n".join(text.strip() for text in bio_items if text.strip()) or None,
    }
    data.update(extract_stats(meta))
    print(data)
    return data

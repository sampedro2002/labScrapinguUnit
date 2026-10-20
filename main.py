import json

from browser import close_browser, get_page
from colecciones import run_followers, run_following
from perfil import run_perfil
from posts import run_posts


LIMIT = 25


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

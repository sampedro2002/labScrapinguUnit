# Scraper de perfiles de Instagram

Aplicación de línea de comandos en Python que consulta un perfil de Instagram y guarda información pública en un archivo JSON local.

## Qué obtiene

- Nombre de usuario y biografía.
- Cantidad de seguidores, seguidos y publicaciones, cuando Instagram muestra esos datos.
- Hasta 50 nombres de seguidores y 50 de seguidos.
- Hasta 50 enlaces a publicaciones o reels, junto con la descripción disponible.

El resultado se guarda como `<usuario>_data.json` en la carpeta desde la que se ejecuta `main.py`. Ese archivo puede contener datos personales recopilados: mantenlo local y no lo subas al repositorio.

## Requisitos

- Python 3.11 o compatible.
- Google Chrome instalado.
- Conexión a Internet.

Las dependencias de Python están declaradas en `requirements.txt`. Playwright usa el Chrome instalado mediante el canal `chrome`.

## Instalación y ejecución en Windows

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Si PowerShell bloquea la activación del entorno, puedes invocar directamente sus ejecutables:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Instalación y ejecución en macOS o Linux

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Uso

1. Ejecuta `python main.py`.
2. Escribe el nombre de usuario de Instagram cuando lo solicite. Se acepta con o sin `@`.
3. En el primer inicio se abrirá una ventana de Chrome. Inicia sesión en Instagram si hace falta y vuelve a la consola para presionar Enter.
4. Espera a que termine la consulta. El JSON resultante aparecerá en la carpeta del proyecto.

La sesión de Chrome se conserva localmente en `.chrome_profile/` para ejecuciones posteriores. No compartas esa carpeta: contiene datos de sesión y credenciales.

## Archivos del proyecto

- `main.py`: coordina la ejecución y guarda el resultado.
- `browser.py`: abre Chrome y reutiliza el perfil local de Playwright.
- `perfil.py`: obtiene la biografía y los datos básicos del perfil.
- `colecciones.py`: recopila seguidores, seguidos y publicaciones.
- `parser.py`: interpreta las cantidades mostradas por Instagram.
- `requirements.txt`: dependencias de Python.
- `.gitignore`: excluye archivos locales y sensibles del control de versiones.

## Qué compartir o subir al repositorio

Comparte el código fuente, `requirements.txt`, `.gitignore` y este README. No incluyas:

- `.chrome_profile/` ni ninguna carpeta de sesión o credenciales.
- Archivos `*_data.json` generados por el scraper.
- Entornos virtuales (`.venv/`, `venv/`, `env/` o `scrap/`). En otra PC se crea un entorno nuevo y se instalan las dependencias desde `requirements.txt`.
- Cachés de Python como `__pycache__/`.

El `.gitignore` cubre estos elementos para Git. Si alguno ya fue agregado al repositorio anteriormente, ignorarlo no lo quita del historial; debe retirarse del seguimiento antes de compartir el repositorio.

## Uso responsable

Usa el scraper únicamente con cuentas y datos a los que tengas autorización de acceder. Instagram puede cambiar su sitio, limitar solicitudes o requerir inicio de sesión; por eso, el scraper puede dejar de encontrar algunos datos o devolver listas vacías.

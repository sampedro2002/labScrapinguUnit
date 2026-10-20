# Scraper de Perfiles de Instagram

Aplicación de línea de comandos en Python que, mediante automatización de navegador con **Playwright** y **Google Chrome**, consulta un perfil de Instagram y extrae su información pública, métricas, lista de seguidores, seguidos, publicaciones y comentarios en un archivo JSON estructurado. Proyecto desarrollado para el laboratorio de Scraping (Arquitectura de Software, semestre 7).

---

## Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Stack Tecnológico y Justificación de Librerías](#2-stack-tecnológico-y-justificación-de-librerías)
   - [2.1 Librerías utilizadas](#21-librerías-utilizadas)
   - [2.2 Análisis comparativo: ¿Por qué estas librerías y no otras?](#22-análisis-comparativo-por-qué-estas-librerías-y-no-otras)
3. [Datos Extraídos](#3-datos-extraídos)
4. [Requisitos Previos](#4-requisitos-previos)
5. [Instalación Paso a Paso](#5-instalación-paso-a-paso)
6. [Gestión de Sesiones (Autenticación)](#6-gestión-de-sesiones-autenticación)
   - [6.1 Rol de `.chrome_profile` vs `.env`](#61-rol-de-chrome_profile-vs-env)
   - [6.2 Modo 1: Autenticación manual](#62-modo-1-autenticación-manual)
   - [6.3 Modo 2: Inyección de cookies desde `.env`](#63-modo-2-inyección-de-cookies-desde-env)
   - [6.4 Cómo obtener la cookie `sessionid`](#64-cómo-obtener-la-cookie-sessionid)
7. [Instrucciones de Uso](#7-instrucciones-de-uso)
8. [Formato del Resultado (JSON)](#8-formato-del-resultado-json)
9. [Estructura del Proyecto](#9-estructura-del-proyecto)
10. [Límites y Consideraciones Técnicas](#10-límites-y-consideraciones-técnicas)
11. [Buenas Prácticas y Exclusiones de Git](#11-buenas-prácticas-y-exclusiones-de-git)
12. [Uso Ético y Responsable](#12-uso-ético-y-responsable)
13. [Licencia](#13-licencia)

---

## 1. Descripción General

Instagram es una Single Page Application (SPA) con arquitectura dinámica, protegida por medidas anti-bot y con generación de contenido bajo demanda (scroll infinito y carga asíncrona de modales). Esta herramienta automatiza un flujo de navegación real utilizando una instancia controlada de Google Chrome, permitiendo la recolección de datos públicos respetando tiempos de espera para mitigar bloqueos temporales.

---

## 2. Stack Tecnológico y Justificación de Librerías

### 2.1 Librerías utilizadas

| Librería | Propósito principal | Tipo |
|---|---|---|
| **`playwright`** (>=1.40) | Control y automatización del navegador Chrome, manejo de contextos persistentes, esperas automáticas y ejecución de peticiones internas vía JavaScript. | Externa (`requirements.txt`) |
| **`python-dotenv`** (>=1.0.0) | Carga de variables de entorno seguras desde archivo `.env` (credenciales y cookies). | Externa (`requirements.txt`) |
| **`re`** | Expresiones regulares para parseo de métricas compactas (`1.2k`, `3M`) y extracción de IDs de publicaciones. | Estándar de Python |
| **`json`** | Deserialización de respuestas de la API interna y serialización del resultado final en JSON estructurado. | Estándar de Python |
| **`datetime` / `time`** | Conversión de marcas de tiempo UNIX a fechas legibles y control de pausas entre scrolls. | Estándar de Python |
| **`urllib.parse`** | Análisis de rutas y descarte de URLs ajenas en los modales de interacción. | Estándar de Python |
| **`pathlib`** | Gestión agnóstica de rutas en el sistema de archivos (compatible con Windows, macOS y Linux). | Estándar de Python |

---

### 2.2 Análisis comparativo: ¿Por qué estas librerías y no otras?

#### ¿Por qué Playwright y no Selenium?
- **Manejo de esperas y sincronización**: Selenium depende de esperas explícitas manuales (`WebDriverWait`) que suelen ser frágiles ante renderizados asíncronos pesados. Playwright incorpora *auto-waiting* nativo (espera automáticamente a que los selectores estén visibles, interactuables y renderizados antes de actuar).
- **Contextos persistentes (`launch_persistent_context`)**: Playwright permite montar un perfil de usuario persistente (`.chrome_profile`) de forma directa y limpia, manteniendo sesiones, almacenamiento local y caché entre corridas sin depender de configuraciones complejas de perfiles de usuario.
- **Detección anti-bot**: Selenium inyecta variables globales en el navegador (como `navigator.webdriver = true`) que son detectadas inmediatamente por los filtros anti-scraping de Instagram. Playwright interactúa mediante el protocolo CDP (Chrome DevTools Protocol) y canal `chrome`, simulando una interacción de usuario mucho más fidedigna.
- **Ejecución interna de fetch (`page.evaluate`)**: Playwright permite ejecutar peticiones dentro del contexto de la pestaña activa reutilizando directamente las credenciales de sesión y cabeceras de Instagram (`X-IG-App-ID`), evitando la necesidad de emular peticiones HTTP externas complejas.

#### ¿Por qué Playwright y no BeautifulSoup4 / Requests?
- **Naturaleza SPA de Instagram**: Herramientas como `requests` o `urllib` sólo obtienen el HTML inicial enviado por el servidor. Dado que Instagram es una aplicación web renderizada en el cliente mediante JavaScript (React), el HTML estático retornado no contiene los seguidores, comentarios ni publicaciones; sólo plantillas vacías.
- **BeautifulSoup es solo un parser**: `beautifulsoup4` no ejecuta JavaScript ni puede interactuar con el DOM (no puede hacer clic en botones, abrir diálogos ni realizar scroll infinito). Se requeriría forzosamente un navegador real.
- **Login walls y checkpoints**: Peticiones directas con `requests` son bloqueadas o redirigidas inmediatamente al muro de autenticación al carecer de un motor JS, cookies dinámicas y TLS fingerprinting adecuado.

#### ¿Por qué Playwright y no Scrapy?
- **Complejidad innecesaria**: Scrapy está optimizado para rastreo masivo concurrente en arquitecturas multipágina estáticas. Para sitios reactivos como Instagram, Scrapy requiere middlewares adicionales pesados (como `scrapy-playwright` o Splash), añadiendo capas de complejidad y configuraciones innecesarias para un script de terminal enfocado.
- **Flujo de interacción secuencial**: La extracción en este laboratorio requiere una secuencia lineal clara (abrir perfil -> extraer bio -> abrir diálogo seguidores -> scroll modal -> capturar publicaciones), modelo en el que Playwright destaca por simplicidad y legibilidad.

#### ¿Por qué `python-dotenv` y no credenciales por consola o quemadas en código?
- **Seguridad (12-Factor App)**: Quemar cookies o contraseñas en código fuente es una vulnerabilidad crítica que expone credenciales si se comparte el repositorio.
- **Historial de terminal protegido**: Pasar cookies largas (`sessionid`, tokens) como argumentos de consola (`--cookie ...`) deja los secretos guardados en el historial del sistema (`.bash_history`, `PSReadLine`), exponiéndolos a otros usuarios del equipo.

---

## 3. Datos Extraídos

| Sección | Atributos extraídos |
|---|---|
| **Perfil** | `username`, `bio`, `followers`, `following`, `posts` |
| **Seguidores y seguidos** | Lista con los nombres de usuario extraídos del modal interactivo |
| **Publicaciones** | `shortcode`, `url`, `caption`, `likes`, `comments_count`, `views`, `timestamp`, `date` |
| **Comentarios** | `username` y `text` por cada comentario dentro de las publicaciones |

> [!NOTE]
> Por defecto el programa obtiene hasta **25** elementos por sección (25 seguidores, 25 seguidos, 25 posts y 25 comentarios por post). Este límite se puede ajustar modificando la constante `LIMIT` en [`main.py`](file:///C:/Users/Det-Pc/Documents/SEMESTRE7/ARQUITECTURA/labScrapinguUnit/main.py#L11).

---

## 4. Requisitos Previos

1. **Python**: Versión 3.11 o superior.
2. **Google Chrome**: Instalado en el sistema operativo (Playwright utiliza el canal oficial `chrome`).
3. **Conexión a Internet**: Acceso estable a Instagram.
4. **Cuenta de Instagram**: Requerida para consultar listados de seguidores/seguidos y comentarios completos.

---

## 5. Instalación Paso a Paso

### 5.1 En Windows (PowerShell)

1. Crear y activar el entorno virtual:
   ```powershell
   py -m venv scrap
   .\scrap\Scripts\Activate.ps1
   ```
   *(Si PowerShell bloquea scripts por directiva de ejecución, puedes usar directamente `.\scrap\Scripts\python.exe`)*.

2. Instalar las dependencias del proyecto:
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Instalar los navegadores de Playwright:
   ```powershell
   python -m playwright install
   ```

### 5.2 En macOS o Linux

1. Crear y activar el entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instalar las dependencias y binarios:
   ```bash
   python -m pip install -r requirements.txt
   python -m playwright install
   ```

---

## 6. Gestión de Sesiones (Autenticación)

### 6.1 Rol de `.chrome_profile` vs `.env`

- **`.chrome_profile/` (Almacenamiento del navegador)**: Carpeta local donde Chrome guarda caché, almacenamiento local y cookies activas. Permite que, tras iniciar sesión una vez, las siguientes ejecuciones no requieran volver a loguearse.
- **`.env` (Inyección rápida de credenciales)**: Permite inyectar cookies directamente (por ejemplo, `SESSIONID`) sin necesidad de ingresar usuario ni contraseña en la interfaz, ideal para entornos desatendidos o para renovar una sesión vencida.

---

### 6.2 Modo 1: Autenticación manual

1. Al ejecutar el scraper por primera vez, se abrirá una ventana de Google Chrome.
2. Si no hay sesión iniciada, ingresa tus credenciales directamente en Instagram.
3. La sesión quedará guardada en `.chrome_profile/` para las siguientes ocasiones.

---

### 6.3 Modo 2: Inyección de cookies desde `.env`

1. Genera tu archivo `.env` a partir de la plantilla:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Abre `.env` e ingresa tu cookie de sesión:
   ```env
   SESSIONID=tu_sessionid_aqui
   DS_USER_ID=tu_ds_user_id_aqui      # opcional
   CSRFTOKEN=tu_csrftoken_aqui        # opcional
   ```

---

### 6.4 Cómo obtener la cookie `sessionid`

`sessionid` es una cookie con flag `HttpOnly`:
1. Inicia sesión en [instagram.com](https://www.instagram.com) desde tu navegador habitual.
2. Presiona `F12` para abrir las **DevTools** y dirígete a la pestaña **Application** (en Firefox: **Almacenamiento**).
3. En el menú izquierdo, navega a **Cookies** > `https://www.instagram.com`.
4. Busca el registro `sessionid`, copia su valor y pégalo en tu archivo `.env`.

> [!CAUTION]
> La cookie `sessionid` equivale a tu contraseña y permite el acceso total a tu cuenta. **Nunca la compartas ni la subas al repositorio.**

---

## 7. Instrucciones de Uso

Ejecuta el script unificado:

```bash
python main.py
```

1. **Ingreso de objetivo**: El programa solicitará el nombre de usuario de Instagram (con o sin `@`).
2. **Extracción automatizada**: El script consultará el perfil, abrirá los modales de conexiones y descargará las publicaciones y comentarios.
3. **Persistencia**: Se creará un archivo `<usuario>_data.json` con toda la información extraída y se mostrará un resumen formateado en la terminal.

---

## 8. Formato del Resultado (JSON)

El archivo generado `<usuario>_data.json` sigue la siguiente estructura:

```json
{
  "username": "ejemplo",
  "bio": "Texto descriptivo de la biografía",
  "followers": 15400,
  "following": 320,
  "posts": 45,
  "followers_list": [
    "usuario_a",
    "usuario_b"
  ],
  "following_list": [
    "cuenta_oficial"
  ],
  "publications": [
    {
      "shortcode": "Cx1y2Z3w4",
      "url": "https://www.instagram.com/p/Cx1y2Z3w4/",
      "caption": "Publicación de prueba",
      "likes": 230,
      "comments_count": 15,
      "views": "N/A",
      "timestamp": 1729382400,
      "date": "2026-10-19 18:40:00",
      "comments": [
        {
          "username": "seguidor1",
          "text": "Excelente publicación!"
        }
      ]
    }
  ]
}
```

---

## 9. Estructura del Proyecto

El proyecto está unificado en un único script autoportante:

```text
labScrapinguUnit/
│
├── main.py              # Script unificado (navegador, perfil, seguidores, posts, comentarios)
├── requirements.txt     # Dependencias del proyecto (Playwright y Python-dotenv)
├── .env.example         # Plantilla de variables de entorno para autenticación
├── .gitignore           # Reglas de exclusión para credenciales, perfiles y temporales
├── README.md            # Documentación técnica y guía de uso del proyecto
└── LICENSE              # Licencia MIT
```

---

## 10. Límites y Consideraciones Técnicas

1. **Políticas de Rate Limiting**: Solicitar un gran volumen de datos en poco tiempo puede activar bloqueos temporales por IP o cuenta. El script incluye pausas entre peticiones para mitigar riesgos.
2. **Cuentas Privadas**: Si la cuenta analizada es privada y tu usuario no la sigue, solo se recolectarán los metadatos públicos de la biografía.
3. **Instancias concurrentes de Chrome**: Si una ventana del scraper quedó colgada en segundo plano, el perfil `.chrome_profile` quedará bloqueado. Asegúrate de cerrar procesos huérfanos de Chrome antes de volver a ejecutar.
4. **Cambios en selectores de Instagram**: Al ser una plataforma propietaria sin API pública abierta, cambios en el DOM o en endpoints internos pueden requerir actualizaciones en los selectores.

---

## 11. Buenas Prácticas y Exclusiones de Git

El archivo `.gitignore` previene la filtración de información sensible. Asegúrate de nunca versionar:
- Archivos `.env` con credenciales reales.
- El directorio `.chrome_profile/` (contiene tokens de sesión de tu máquina).
- Archivos generados `*_data.json` con datos recolectados.
- Entornos virtuales (`scrap/`, `.venv/`) y carpetas `__pycache__/`.

---

## 12. Uso Ético y Responsable

Este desarrollo tiene fines **estrictamente académicos** en el marco del curso de Arquitectura de Software. El scraping automatizado debe realizarse exclusivamente sobre cuentas propias o con autorización expresa, respetando los Términos de Servicio de la plataforma y las regulaciones locales sobre privacidad y tratamiento de datos personales.

---

## 13. Licencia

Proyecto distribuido bajo la licencia [MIT](LICENSE).

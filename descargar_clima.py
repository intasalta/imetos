import os
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

# Cargar variables de entorno desde .env si existe (útil para pruebas locales)
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

ESTACIONES = ["00002586", "00002646"]

def run():
    if not USER or not PASS:
        raise ValueError("Error: Las variables de entorno FC_USER y FC_PASS deben estar definidas.")

    print(f"Iniciando descarga para el usuario: {USER}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True
        )
        page = context.new_page()

        print("1. Accediendo a la página de inicio de sesión...")
        page.goto("https://fieldclimate.com/auth/login", wait_until="commit", timeout=45000)

        print("2. Esperando que el formulario se renderice...")
        page.wait_for_selector("input[type='password']", timeout=45000)
        time.sleep(1)

        print("3. Rellenando credenciales...")
        page.locator("input").first.fill(USER)
        time.sleep(0.5)
        page.locator("input[type='password']").first.fill(PASS)
        time.sleep(0.5)

        print("4. Iniciando sesión...")
        page.locator("button:has-text('Sign In'), button[type='submit']").first.click()

        print("Esperando redirección del login...")
        page.wait_for_url(lambda u: "/auth/login" not in u, timeout=45000)
        print(f"Sesión iniciada correctamente. URL actual: {page.url}")
        time.sleep(3)

        archivos_descargados = []

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"\n--- Procesando Estación {est_id} ---")
            print(f"Navegando a: {station_url}")
            page.goto(station_url, wait_until="commit", timeout=45000)

            try:
                # Esperamos a que la barra de herramientas de datos esté lista
                print("Esperando botón de exportación de tabla...")
                table_btn = page.wait_for_selector("button:has(i.fa-table)", timeout=35000)
                time.sleep(2)

                print("Haciendo clic para descargar el archivo Excel (.xls)...")
                with page.expect_download(timeout=30000) as download_info:
                    table_btn.click()

                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                archivos_descargados.append(filename)
                print(f"¡Éxito! Archivo guardado como {filename} ({os.path.getsize(filename):,} bytes)")

            except Exception as e:
                print(f"Error al descargar los datos de la estación {est_id}: {e}")
                screenshot_name = f"error_{est_id}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"Captura de pantalla de error guardada como {screenshot_name}")
                raise e

        browser.close()

        # Si estamos en un repositorio Git (ej: GitHub Actions), comitear los cambios
        if archivos_descargados and os.path.exists(".git"):
            print("\nActualizando repositorio Git...")
            try:
                subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=False)
                subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=False)
                for f in archivos_descargados:
                    subprocess.run(["git", "add", f], check=False)
                subprocess.run(["git", "commit", "-m", "Actualización automática de datos climáticos .xls [skip ci]"], check=False)
                subprocess.run(["git", "push"], check=False)
                print("Archivos sincronizados en Git con éxito.")
            except Exception as git_err:
                print(f"Aviso Git: {git_err}")

        print(f"\n¡Proceso finalizado con éxito! Total archivos descargados: {len(archivos_descargados)}")

if __name__ == "__main__":
    run()

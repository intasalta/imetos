import os
import time
from playwright.sync_api import sync_playwright

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

# Lista con las estaciones que quieres descargar
ESTACIONES = ["00002586", "00002646"]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("1. Accediendo a FieldClimate...")
        page.goto("https://fieldclimate.com/login", timeout=60000)

        print("2. Iniciando sesión...")
        page.fill("input[name='email'], input[type='email']", USER)
        page.fill("input[name='password'], input[type='password']", PASS)
        page.click("button[type='submit'], button:has-text('Login'), button:has-text('Iniciar sesión')")
        
        page.wait_for_load_state("networkidle")
        time.sleep(5)

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"3. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(8) # Dar tiempo a que cargue la interfaz y los datos

            print(f"4. Descargando el archivo XLS para la estación {est_id}...")
            try:
                with page.expect_download() as download_info:
                    page.click("button[title*='xls'], button:has-text('xls'), .fa-file-excel, [tooltip*='xls']")
                
                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                print(f"¡Éxito! Archivo guardado como {filename}")
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")

        browser.close()

if __name__ == "__main__":
    run()

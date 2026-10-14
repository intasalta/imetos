import os
import time
from playwright.sync_api import sync_playwright

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

ESTACIONES = ["00002586", "00002646"]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("1. Accediendo a FieldClimate...")
        page.goto("https://fieldclimate.com/login", timeout=60000)

        print("2. Esperando a que cargue el formulario...")
        # Damos un respiro para que carguen los elementos de la SPA
        time.sleep(5)

        print("3. Rellenando credenciales...")
        # Buscamos los inputs por su posición o placeholder común de login
        # Por lo general, el primer input es el usuario/email y el segundo la contraseña
        inputs = page.locator("input")
        
        # Esperar a que al menos haya 2 inputs en pantalla
        page.wait_for_selector("input", timeout=30000)
        
        # Rellenar email (primer input de texto o email)
        inputs.nth(0).fill(USER)
        time.sleep(1)
        
        # Rellenar contraseña (segundo input o el que sea de tipo password)
        password_input = page.locator("input[type='password']").first
        password_input.fill(PASS)
        time.sleep(1)

        print("4. Haciendo clic en iniciar sesión...")
        # Buscamos el botón de submit o que contenga texto de acceso
        page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign'), button:has-text('Ingresar')").first.click()
        
        # Esperar a que la sesión inicie y redirija al dashboard
        print("Esperando redirección del login...")
        time.sleep(10)
        page.wait_for_load_state("networkidle")

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"5. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(8)

            print(f"6. Descargando el archivo XLS para la estación {est_id}...")
            try:
                with page.expect_download() as download_info:
                    # Clic en el botón de exportación de Excel/XLS
                    page.locator("button[title*='xls'], button:has-text('xls'), .fa-file-excel, [tooltip*='xls'], button .fa-download").first.click()
                
                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                print(f"¡Éxito! Archivo guardado como {filename}")
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")

        browser.close()

if __name__ == "__main__":
    run()

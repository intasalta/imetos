import os
import time
from playwright.sync_api import sync_playwright

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

ESTACIONES = ["00002586", "00002646"]

def run():
    with sync_playwright() as p:
        # Lanzamos el navegador en modo visible (headless=False por si quieres depurar) o True
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("1. Accediendo a FieldClimate...")
        page.goto("https://fieldclimate.com/login", timeout=60000)

        print("2. Esperando y rellenando credenciales...")
        # Esperamos a que aparezca cualquier campo de entrada en la página
        page.wait_for_selector("input", timeout=30000)
        time.sleep(3)

        # Buscamos de forma flexible el campo de usuario/email
        email_input = page.locator("input[name*='email'], input[name*='user'], input[type='email'], input[type='text']").first
        email_input.fill(USER)

        # Buscamos de forma flexible el campo de contraseña
        pass_input = page.locator("input[name*='pass'], input[type='password']").first
        pass_input.fill(PASS)

        print("3. Haciendo clic en iniciar sesión...")
        # Hacemos clic en el botón de login
        page.click("button[type='submit'], button:has-text('Login'), button:has-text('Sign in'), button:has-text('Entrar')")
        
        # Esperamos a que termine de cargar el dashboard post-login
        page.wait_for_load_state("networkidle")
        time.sleep(10) # Espera prudencial para la redirección

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"4. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(8)

            print(f"5. Descargando el archivo XLS para la estación {est_id}...")
            try:
                with page.expect_download() as download_info:
                    # Buscamos el botón de descarga por título, icono o texto
                    page.click("button[title*='xls'], button:has-text('xls'), .fa-file-excel, [tooltip*='xls'], button .fa-download")
                
                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                print(f"¡Éxito! Archivo guardado como {filename}")
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")

        browser.close()

if __name__ == "__main__":
    run()

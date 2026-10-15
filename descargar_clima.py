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
        time.sleep(5)

        print("2. Rellenando credenciales...")
        inputs = page.locator("input")
        page.wait_for_selector("input", timeout=30000)
        
        inputs.nth(0).fill(USER)
        time.sleep(1)
        
        password_input = page.locator("input[type='password']").first
        password_input.fill(PASS)
        time.sleep(1)

        print("3. Haciendo clic en iniciar sesión...")
        page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign'), button:has-text('Ingresar')").first.click()
        
        print("Esperando redirección del login...")
        time.sleep(10)
        page.wait_for_load_state("networkidle")

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"4. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(15) # Damos más tiempo para que carguen los componentes de la estación

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                with page.expect_download(timeout=45000) as download_info:
                    # Probamos múltiples selectores amplios para botones de exportación en plataformas modernas
                    export_btn = page.locator(
                        "button:has-text('Export'), "
                        "button:has-text('Descargar'), "
                        "button:has-text('XLS'), "
                        "[aria-label*='Export'], "
                        "[aria-label*='Download'], "
                        "[aria-label*='Excel'], "
                        ".mat-mdc-menu-trigger, "
                        "css=mat-icon:has-text('get_app'), "
                        "css=mat-icon:has-text('download')"
                    ).first
                    
                    export_btn.click()
                    
                    # Si es un menú desplegable, a veces hay que hacer un segundo clic en la opción XLS/Excel
                    time.sleep(2)
                    xls_option = page.locator("button:has-text('XLS'), a:has-text('XLS'), span:has-text('XLS'), div:has-text('XLS')")
                    if xls_option.count() > 0:
                        xls_option.first.click()
                
                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                print(f"¡Éxito! Archivo guardado como {filename}")
                
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")
                # Guardamos una captura de pantalla para inspeccionar el estado actual en el runner
                screenshot_name = f"error_{est_id}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"Captura de pantalla guardada como {screenshot_name}")
                raise e  # Fuerza el fallo del script para que se active la subida del artefacto

        browser.close()

if __name__ == "__main__":
    run()

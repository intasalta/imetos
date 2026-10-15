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
            time.sleep(15) # Tiempo prudencial para que cargue toda la gráfica y botones

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                with page.expect_download(timeout=45000) as download_info:
                    # Alternativa 1: Buscar cualquier botón con etiqueta de descarga, icono de excel o SVG interno en la barra de herramientas
                    # Alternativa 2: Localizamos el grupo de botones encima de la gráfica y seleccionamos el que corresponde a la descarga de Excel/XLS
                    download_button = page.locator("button:has(mat-icon), button:has(i), [role='button']").filter(has_text="")
                    
                    # Buscamos de forma genérica el botón de exportación por clase o posición en la botonera superior
                    # En la barra de herramientas, el botón de descarga XLS suele tener iconos asociados a archivos o descargas
                    target_btn = page.locator("button[title*='xls'], button[title*='Exportar'], button:has(i.fa-download), .mat-mdc-tooltip-trigger").first
                    
                    if target_btn.count() > 0 and target_btn.is_visible():
                        target_btn.click()
                    else:
                        # Fallback por selector amplio de botones de acción en la cabecera de datos
                        page.locator(".fa-download, .fa-file-excel").first.click()

                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                print(f"¡Éxito! Archivo guardado como {filename}")
                
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")
                screenshot_name = f"error_{est_id}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"Captura de pantalla guardada como {screenshot_name}")
                raise e

        browser.close()

if __name__ == "__main__":
    run()

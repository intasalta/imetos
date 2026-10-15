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
            time.sleep(15) # Tiempo prudencial para que cargue toda la data y gráficos

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                with page.expect_download(timeout=45000) as download_info:
                    # Intentamos ubicar el botón de descarga mediante múltiples alternativas directas
                    # Buscamos botones en la barra superior de herramientas de gráficos
                    download_clicked = False
                    
                    # Opción A: Buscar por botones que contengan íconos de descarga o exportación comunes
                    selectors = [
                        "button[title*='Download'], button[title*='Export'], button[title*='Excel'], button[title*='Descargar']",
                        "button mat-icon:has-text('download'), button mat-icon:has-text('get_app')",
                        ".fa-download, .fa-file-excel, .fa-file-csv",
                        "button:has(.fa-download), button:has(.fa-file-excel)"
                    ]
                    
                    for sel in selectors:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            loc.click()
                            download_clicked = True
                            break
                    
                    # Opción B: Si los selectores anteriores no disparan el click, usamos JavaScript para buscar 
                    # el botón de descarga en la barra superior (el que está antes del botón de tabla)
                    if not download_clicked:
                        page.evaluate("""() => {
                            // Buscamos todos los botones dentro del contenedor de la barra superior de herramientas
                            const buttons = Array.from(document.querySelectorAll('button'));
                            // Filtramos o buscamos el botón que tenga un icono de descarga o esté en la posición de exportación
                            for (let btn of buttons) {
                                if (btn.innerHTML.includes('fa-download') || btn.innerHTML.includes('download') || btn.getAttribute('aria-label')?.toLowerCase().includes('download')) {
                                    btn.click();
                                    return;
                                }
                            }
                            // Alternativa por posición de los botones superiores en FieldClimate (tercer botón de la botonera derecha)
                            const actionButtons = document.querySelectorAll('.mat-mdc-tooltip-trigger, button[mat-icon-button]');
                            if (actionButtons.length >= 3) {
                                // Por lo general el de descarga es de los primeros en la barra de herramientas de exportación
                                actionButtons[0].click(); 
                            }
                        """)

                    # Comprobación por si aparece un menú flotante con la opción de formato XLS
                    time.sleep(2)
                    xls_option = page.locator("text=XLS, text=Excel, button:has-text('XLS')")
                    if xls_option.count() > 0 and xls_option.first.is_visible():
                        xls_option.first.click()

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

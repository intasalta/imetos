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
            time.sleep(15) # Tiempo prudencial para que cargue toda la interfaz y gráficos

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                with page.expect_download(timeout=45000) as download_info:
                    # Ejecutamos un script en el navegador para hacer clic de forma segura en el botón de descarga XLS
                    # buscando por el título exacto que aparece en el tooltip ("Exportar tabla como xls") o elementos de descarga cercanos
                    clicked = page.evaluate("""() => {
                        // Buscamos todos los botones o elementos interactivos de la página
                        const elements = Array.from(document.querySelectorAll('button, [role="button"], mat-icon'));
                        
                        for (let el of elements) {
                            const title = (el.getAttribute('title') || el.getAttribute('aria-label') || '').toLowerCase();
                            const text = el.innerText.toLowerCase();
                            
                            // Coincidencia con el título exacto del botón de exportación
                            if (title.includes('xls') || title.includes('exportar') || text.includes('xls')) {
                                el.click();
                                return true;
                            }
                        }
                        
                        // Plan B: Buscar botones en la botonera superior (el de descarga suele estar cerca de los controles de vista)
                        const toolButtons = Array.from(document.querySelectorAll('button[mat-icon-button], .mat-mdc-icon-button'));
                        for (let btn of toolButtons) {
                            // Si contiene un icono o SVG relacionado con descarga / flecha hacia abajo
                            if (btn.innerHTML.includes('download') || btn.innerHTML.includes('get_app') || btn.innerHTML.includes('svg')) {
                                // Verificamos que no sea el botón de actualizar u otros
                                if (!btn.innerText.includes('ACTUALIZAR')) {
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                        
                        // Plan C por posición genérica si los anteriores fallan: el tercer o cuarto botón de la botonera superior
                        if (toolButtons.length > 2) {
                            toolButtons[2].click();
                            return true;
                        }
                        
                        return false;
                    })`;

                    if (!clicked) {
                        raise Exception("No se encontró el botón de descarga mediante JavaScript interactivo.")
                    }

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

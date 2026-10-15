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
                    # Buscamos de manera directa por el título que muestra el tooltip en español o inglés
                    download_button = page.locator("button[title*='Exportar'], button[title*='xls'], button:has(.fa-download), button:has(i.fa-download)").first
                    
                    if download_button.count() > 0 and download_button.is_visible():
                        download_button.click()
                    else:
                        # Si no lo encuentra por selector directo, ejecutamos JS seguro para hacer clic en el botón de exportación
                        page.evaluate("""() => {
                            const buttons = Array.from(document.querySelectorAll('button'));
                            for (let btn of buttons) {
                                const title = btn.getAttribute('title') || '';
                                if (title.toLowerCase().includes('exportar') || title.toLowerCase().includes('xls') || btn.innerHTML.includes('fa-download')) {
                                    btn.click();
                                    break;
                                }
                            }
                        """)

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

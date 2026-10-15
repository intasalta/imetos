import os
import time
import subprocess
import re
from playwright.sync_api import sync_playwright

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

ESTACIONES = ["00002586", "00002646"]

def run():
    with sync_playwright() as p:
        # Iniciamos con un tamaño de pantalla fijo de escritorio (1920x1080) para que la interfaz no varíe
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True
        )
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

        archivos_descargados = []

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"4. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(15)

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                # Paso 1: Hacemos clic en el botón de exportación usando la barra de herramientas superior con la nueva resolución fija
                page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (let btn of buttons) {
                        const rect = btn.getBoundingClientRect();
                        // Con viewport de 1920x1080, el botón de exportación de la gráfica se ubica en esta área superior derecha
                        if (rect.top > 250 && rect.top < 400 && rect.left > 1200) {
                            btn.click();
                            break;
                        }
                    }
                }""")
                
                # Paso 2: Esperamos que aparezca el menú flotante y capturamos la descarga al hacer clic en la opción de XLS
                with page.expect_download(timeout=45000) as download_info:
                    page.wait_for_selector(".cdk-overlay-pane", timeout=12000)
                    time.sleep(1)
                    page.locator(".cdk-overlay-pane button, .cdk-overlay-pane a, .cdk-overlay-pane div").filter(has_text=re.compile("xls|excel|exportar", re.IGNORECASE)).first.click()

                download = download_info.value
                filename = f"{est_id}_station_data.xls"
                download.save_as(filename)
                archivos_descargados.append(filename)
                print(f"¡Éxito! Archivo guardado localmente como {filename}")
                
            except Exception as e:
                print(f"Error al descargar la estación {est_id}: {e}")
                screenshot_name = f"error_{est_id}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"Captura de pantalla guardada como {screenshot_name}")
                raise e

        browser.close()

        # Sincronizar y hacer commit automático de los archivos descargados al repositorio
        if archivos_descargados:
            print("6. Subiendo archivos descargados al repositorio de GitHub...")
            subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"])
            subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"])
            
            for f in archivos_descargados:
                subprocess.run(["git", "add", f])
                
            subprocess.run(["git", "commit", "-m", "Actualización automática de datos climáticos .xls"])
            subprocess.run(["git", "push"])
            print("¡Archivos subidos y guardados en el repositorio correctamente!")

if __name__ == "__main__":
    run()

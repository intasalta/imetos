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

        archivos_descargados = []

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"4. Navegando a la estación {est_id}: {station_url}")
            page.goto(station_url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(15)

            print(f"5. Intentando descargar el archivo para la estación {est_id}...")
            try:
                # Paso A: Hacemos clic en el botón de exportación de la barra superior por coordenadas
                buttons = page.locator("button")
                count = buttons.count()
                for i in range(count):
                    b = buttons.nth(i)
                    if b.is_visible():
                        box = b.bounding_box()
                        if box and 200 < box['y'] < 350:
                            try:
                                b.click(timeout=2000)
                                break
                            except Exception:
                                continue
                
                time.sleep(2) # Pausa para que se abra el menú flotante

                # Paso B: Iniciamos la espera de descarga y hacemos clic en la opción XLS/Excel dentro del menú desplegado
                with page.expect_download(timeout=45000) as download_info:
                    popup_options = page.locator("button, a, div, span, mat-option").filter(has_text=re.compile("xls|excel|download|descargar", re.IGNORECASE))
                    if popup_options.count() > 0:
                        clicked_popup = False
                        for j in range(popup_options.count()):
                            opt = popup_options.nth(j)
                            if opt.is_visible():
                                try:
                                    opt.click(timeout=1500)
                                    clicked_popup = True
                                    break
                                except Exception:
                                    continue
                        if not clicked_popup:
                            # Si no encontró texto exacto, hacemos clic en el primer elemento visible del menú desplegable
                            page.locator(".cdk-overlay-pane button, .mat-mdc-menu-content button").first.click()
                    else:
                        # Si no hay menú y el botón descargaba directo, forzamos clic alternativo
                        page.locator("button[title*='xls'], button[title*='Exportar']").first.click()

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

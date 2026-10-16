import os
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright

# Cargar variables de entorno desde .env si existe (para pruebas locales)
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

USER = os.environ.get("FC_USER")
PASS = os.environ.get("FC_PASS")

ESTACIONES = ["00002586", "00002646"]

def convertir_xls_a_formatos(xls_path, est_id):
    """
    Convierte el archivo SpreadsheetML XML (.xls) de FieldClimate
    a formatos estándar modernos: CSV (.csv) y Excel (.xlsx).
    """
    try:
        tree = ET.parse(xls_path)
        root = tree.getroot()
        ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}

        rows = []
        for row in root.findall('.//ss:Row', ns):
            row_cells = []
            for cell in row.findall('ss:Cell', ns):
                merge = int(cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                data = cell.find('ss:Data', ns)
                val = data.text if data is not None else ''
                row_cells.append(val)
                for _ in range(merge):
                    row_cells.append(val)
            rows.append(row_cells)

        if len(rows) < 3:
            print(f"Aviso: El archivo {xls_path} no tiene suficientes filas para convertir.")
            return []

        h1 = rows[0]
        h2 = rows[1]
        headers = []
        for i in range(len(h2)):
            c1 = h1[i] if i < len(h1) and h1[i] else ''
            c2 = h2[i] if i < len(h2) and h2[i] else ''
            if c1 and c2 and c1 != c2:
                headers.append(f"{c1} - {c2}")
            elif c2:
                headers.append(c2)
            elif c1:
                headers.append(c1)
            else:
                headers.append(f"Col_{i}")

        df = pd.DataFrame(rows[2:], columns=headers)

        # Convertir columnas numéricas a números reales para evitar strings en Excel/CSV
        for col in df.columns:
            if col != 'Fecha / Hora':
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception:
                    pass

        csv_filename = f"{est_id}_station_data.csv"
        xlsx_filename = f"{est_id}_station_data.xlsx"

        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        df.to_excel(xlsx_filename, index=False)

        print(f"  -> Generado CSV: {csv_filename} ({os.path.getsize(csv_filename):,} bytes)")
        print(f"  -> Generado XLSX: {xlsx_filename} ({os.path.getsize(xlsx_filename):,} bytes)")

        return [csv_filename, xlsx_filename]

    except Exception as conv_err:
        print(f"Error al convertir {xls_path}: {conv_err}")
        return []

def run():
    if not USER or not PASS:
        raise ValueError("Error: Las variables de entorno FC_USER y FC_PASS deben estar definidas.")

    print(f"Iniciando descarga para el usuario: {USER}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True
        )
        page = context.new_page()

        print("1. Accediendo a la página de inicio de sesión...")
        page.goto("https://fieldclimate.com/auth/login", wait_until="commit", timeout=45000)

        print("2. Esperando que el formulario se renderice...")
        page.wait_for_selector("input[type='password']", timeout=90000)
        time.sleep(1)

        print("3. Rellenando credenciales...")
        page.locator("input").first.fill(USER)
        time.sleep(0.5)
        page.locator("input[type='password']").first.fill(PASS)
        time.sleep(0.5)

        print("4. Iniciando sesión...")
        page.locator("button:has-text('Sign In'), button[type='submit']").first.click()

        print("Esperando redirección del login...")
        page.wait_for_url(lambda u: "/auth/login" not in u, timeout=45000)
        print(f"Sesión iniciada correctamente. URL actual: {page.url}")
        time.sleep(3)

        archivos_generados = []

        for est_id in ESTACIONES:
            station_url = f"https://fieldclimate.com/station/{est_id}/data"
            print(f"\n--- Procesando Estación {est_id} ---")
            print(f"Navegando a: {station_url}")
            page.goto(station_url, wait_until="commit", timeout=45000)

            try:
                print("Esperando botón de exportación de tabla...")
                table_btn = page.wait_for_selector("button:has(i.fa-table)", timeout=35000)
                time.sleep(2)

                print("Haciendo clic para descargar el archivo Excel (.xls)...")
                with page.expect_download(timeout=30000) as download_info:
                    table_btn.click()

                download = download_info.value
                xls_filename = f"{est_id}_station_data.xls"
                download.save_as(xls_filename)
                archivos_generados.append(xls_filename)
                print(f"¡Éxito! Archivo XLS descargado: {xls_filename} ({os.path.getsize(xls_filename):,} bytes)")

                # Conversión automática a CSV y XLSX
                formatos_extra = convertir_xls_a_formatos(xls_filename, est_id)
                archivos_generados.extend(formatos_extra)

            except Exception as e:
                print(f"Error al descargar los datos de la estación {est_id}: {e}")
                screenshot_name = f"error_{est_id}.png"
                page.screenshot(path=screenshot_name, full_page=True)
                print(f"Captura de pantalla de error guardada como {screenshot_name}")
                raise e

        browser.close()

        # Si estamos en un repositorio Git local con upstream configurado
        if archivos_generados and os.path.exists(".git"):
            print("\nActualizando repositorio Git...")
            try:
                subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=False)
                subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=False)
                for f in archivos_generados:
                    subprocess.run(["git", "add", f], check=False)
                subprocess.run(["git", "commit", "-m", "Actualización automática de datos climáticos (.xls, .csv, .xlsx) [skip ci]"], check=False)
                subprocess.run(["git", "push"], check=False)
                print("Archivos sincronizados en Git con éxito.")
            except Exception as git_err:
                print(f"Aviso Git: {git_err}")

        print(f"\n¡Proceso finalizado con éxito! Total archivos generados: {len(archivos_generados)}")

if __name__ == "__main__":
    run()

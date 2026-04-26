import sqlite3
import time
from playwright.sync_api import sync_playwright

categorias = [
    "mercearia", "bebidas", "higiene-e-beleza", "limpeza", "bazar",
    "frios-e-laticinios", "acougue", "hortifruti", "congelados",
    "cafe-da-manha", "mamae-e-bebe", "petshop", "alimentos-funcionais"
]

BASE = "https://www.superpaguemenos.com.br"

def coletar():
    conn = sqlite3.connect('arca.db')
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS links_paguemenos")
    cursor.execute("CREATE TABLE links_paguemenos (url TEXT PRIMARY KEY, cat TEXT)")
    conn.commit()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visível pra não ser bloqueado
        page = browser.new_page()

        for slug in categorias:
            print(f"\n📦 {slug}")
            links_cat = set()

            # Intercepta respostas JSON que o browser faz internamente
            def handle_response(response):
                try:
                    if response.status != 200:
                        return
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    url = response.url
                    if "products/search" not in url and "shelf" not in url and "search" not in url:
                        return
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        for prod in data:
                            link = prod.get("link") or prod.get("url") or prod.get("detailUrl")
                            if link and link.endswith("/p"):
                                links_cat.add(link)
                                cursor.execute(
                                    "INSERT OR IGNORE INTO links_paguemenos VALUES (?, ?)",
                                    (link, slug)
                                )
                except:
                    pass

            page.on("response", handle_response)
            page.goto(f"{BASE}/{slug}", wait_until="networkidle", timeout=40000)
            time.sleep(2)

            # Coleta links do HTML inicial também
            links_html = page.eval_on_selector_all(
                'a[href$="/p"]', 'els => els.map(e => e.href)'
            )
            for link in links_html:
                links_cat.add(link)
                cursor.execute("INSERT OR IGNORE INTO links_paguemenos VALUES (?, ?)", (link, slug))
            conn.commit()

            print(f"   inicial: {len(links_cat)} links")

            # Scroll com mouse wheel real
            sem_novos = 0
            ultimo_total = 0

            while sem_novos < 5:
                # Scroll incremental com mouse
                for _ in range(8):
                    page.mouse.wheel(0, 600)
                    time.sleep(0.3)

                page.wait_for_timeout(2500)
                conn.commit()

                # Também coleta do HTML após scroll
                links_agora = page.eval_on_selector_all(
                    'a[href$="/p"]', 'els => els.map(e => e.href)'
                )
                for link in links_agora:
                    links_cat.add(link)
                    cursor.execute("INSERT OR IGNORE INTO links_paguemenos VALUES (?, ?)", (link, slug))
                conn.commit()

                if len(links_cat) > ultimo_total:
                    print(f"   {len(links_cat)} links...")
                    ultimo_total = len(links_cat)
                    sem_novos = 0
                else:
                    sem_novos += 1

            page.remove_listener("response", handle_response)
            print(f"   ✅ Total {slug}: {len(links_cat)}")

        browser.close()

    total = sqlite3.connect('arca.db').execute("SELECT COUNT(*) FROM links_paguemenos").fetchone()[0]
    print(f"\n🏁 Total no banco: {total} links")

if __name__ == "__main__":
    coletar()
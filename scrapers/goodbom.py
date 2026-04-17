import sqlite3
import requests
import re
import time
import unicodedata
from datetime import datetime
from base_scraper import BaseScraper


def normalizar_nome(nome):
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    nome = re.sub(r'\s+', ' ', nome).strip().upper()
    nome = re.sub(r'[^\w\s]', '', nome)
    return nome


class GoodBomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Rsc": "1"
        }

    def extrair(self, url_produto):
        try:
            response = requests.get(url_produto, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                print(f"⚠️ Erro HTTP {response.status_code} → {url_produto}")
                return None

            texto = response.text

            # 1. EAN — padrão brasileiro 789 (pode ser N/A, limitação conhecida)
            ean_match = re.search(r'789\d{10}', texto)
            ean_final = ean_match.group(0) if ean_match else "N/A"

            # 2. Nome — busca dentro de "product" primeiro, depois title
            nome_match = re.search(r'"product"\s*:\s*\{[^}]*?"name"\s*:\s*"([^"]+)"', texto)
            if not nome_match:
                nome_match = re.search(r'<title>([^<]+?)(?:\s*[-|]\s*GoodBom)?</title>', texto)

            nome_raw = nome_match.group(1) if nome_match else "N/A"

            # 3. Encoding fix
            try:
                nome_limpo = nome_raw.encode('raw_unicode_escape').decode('utf-8').strip().upper()
            except Exception:
                nome_limpo = nome_raw.strip().upper()

            # 4. Preço
            match_desconto = re.search(r'"priceWithDiscount":\s*([\d.]+)', texto)
            match_normal   = re.search(r'"price":\s*([\d.]+)', texto)

            preco_final = 0.0
            if match_desconto and float(match_desconto.group(1)) > 0:
                preco_final = float(match_desconto.group(1))
            elif match_normal:
                preco_final = float(match_normal.group(1))

            # 5. ID de Origem
            id_match = re.search(r'-(\d+)$', url_produto.strip())
            id_origem = id_match.group(1) if id_match else "N/A"

            # 6. Imagem
            img_match = re.search(r'(https://phygital-files\.mercafacil\.com[^"\']+\.(?:jpeg|jpg|png|webp))', texto)
            url_img = img_match.group(1) if img_match else "N/A"

            # 7. Marca e categoria
            marca_match     = re.search(r'"brand"\s*:\s*"([^"]+)"', texto)
            categoria_match = re.search(r'"category"\s*:\s*"([^"]+)"', texto)

            return {
                "id_origem":        id_origem,
                "ean":              ean_final,
                "nome":             nome_limpo,
                "nome_normalizado": normalizar_nome(nome_limpo),
                "marca":            marca_match.group(1) if marca_match else "N/A",
                "categoria":        categoria_match.group(1).upper() if categoria_match else "GERAL",
                "preco":            preco_final,
                "mercado":          "GoodBom",
                "unidade":          "Mogi Mirim",
                "url_imagem":       url_img,
                "url_produto":      url_produto,
                "data_extracao":    datetime.now().isoformat(),
                "status":           "bronze"
            }

        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return None


def processar_banco():
    scraper  = GoodBomScraper()
    db_mongo = scraper.conectar()

    if db_mongo is None:
        print("❌ Abortando: falha na conexão com o MongoDB.")
        return

    try:
        conn_sqlite = sqlite3.connect('arca.db')
        cursor      = conn_sqlite.cursor()
        cursor.execute("SELECT url FROM links")
        produtos = cursor.fetchall()
        conn_sqlite.close()
    except Exception as e:
        print(f"❌ Erro ao ler o SQLite: {e}")
        scraper.client.close()
        return

    total   = len(produtos)
    ok      = 0
    falhas  = 0

    print(f"🚀 Iniciando coleta de {total} produtos...")

    for i, (url,) in enumerate(produtos, 1):
        dados = scraper.extrair(url)

        if dados:
            try:
                resultado = db_mongo['precos_crus'].update_one(
                    {"url_produto": dados["url_produto"]},
                    {"$set": dados},
                    upsert=True
                )
                ok += 1
                print(f"[{i}/{total}] ✅ {dados['nome'][:35]:<35} | R$ {dados['preco']:.2f} | norm: {dados['nome_normalizado'][:30]}")
            except Exception as e:
                falhas += 1
                print(f"[{i}/{total}] ❌ Erro ao salvar: {e}")
        else:
            falhas += 1
            print(f"[{i}/{total}] ⚠️ Extração falhou → {url}")

        time.sleep(1.2)

    scraper.client.close()
    print(f"\n🏁 Coleta finalizada! Salvos: {ok} | Falhas: {falhas} | Total: {total}")


if __name__ == "__main__":
    # DEBUG — testa uma URL antes de rodar tudo
    # scraper = GoodBomScraper()
    # url_teste = "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/arroz-tp-1-oliron-5kg-19241"
    # print(scraper.extrair(url_teste))

    # COMPLETO
    processar_banco()
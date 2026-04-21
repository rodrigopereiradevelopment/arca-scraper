import requests
from bs4 import BeautifulSoup
import sqlite3
import time

def coletar_pague_menos():
    # Mapeamento de categorias do Pague Menos
    categorias = {
        "Arroz": "https://www.superpaguemenos.com.br/mercearia/arroz",
        "Feijão": "https://www.superpaguemenos.com.br/mercearia/feijao",
        "Óleo": "https://www.superpaguemenos.com.br/mercearia/oleos",
        "Café": "https://www.superpaguemenos.com.br/mercearia/cafe",
        "Legumes": "https://www.superpaguemenos.com.br/hortifruti/legumes",
        "Verduras": "https://www.superpaguemenos.com.br/hortifruti/verduras",
        "Frutas": "https://www.superpaguemenos.com.br/hortifruti/frutas",
        "Ovos": "https://www.superpaguemenos.com.br/hortifruti/ovos/ovos-de-galinha",
        "Carnes": "https://www.superpaguemenos.com.br/acougue/bovinos",
        "Leite": "https://www.superpaguemenos.com.br/matinais/leites",
        "Limpeza": "https://www.superpaguemenos.com.br/limpeza",
        "Higiene": "https://www.superpaguemenos.com.br/higiene-e-beleza"
    }

    conn = sqlite3.connect('arca.db')
    cursor = conn.cursor()

    # --- MUDANÇA 1: Tabela exclusiva para o Pague Menos ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS links_paguemenos 
                      (url TEXT PRIMARY KEY, nome TEXT, cat TEXT)''')

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for nome_cat, url_base in categorias.items():
        print(f"🔍 [Pague Menos] Raspando Categoria: {nome_cat}")
        try:
            # Pegando as 2 primeiras páginas de cada categoria
            for pagina in range(1, 3): 
                url = f"{url_base}?page={pagina}"
                res = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(res.content, 'html.parser')
                
                produtos = soup.find_all('a', class_='item-image')

                if not produtos:
                    break 

                for item in produtos:
                    link = item['href']
                    if not link.startswith('http'):
                        link = "https://www.superpaguemenos.com.br" + link
                    
                    img = item.find('img')
                    nome = img.get('title', 'Produto sem nome') if img else "N/A"
                    
                    print(f"   ✅ {nome}")

                    # --- MUDANÇA 2: Inserindo na tabela correta ---
                    cursor.execute("INSERT OR REPLACE INTO links_paguemenos VALUES (?, ?, ?)", 
                                 (link, nome, nome_cat))
                
                conn.commit()
                time.sleep(1) 

        except Exception as e:
            print(f"❌ Erro na categoria {nome_cat}: {e}")

    conn.close()
    print("\n🚀 LINKS DO PAGUE MENOS SINCRONIZADOS NA TABELA links_paguemenos!")

if __name__ == "__main__":
    coletar_pague_menos()
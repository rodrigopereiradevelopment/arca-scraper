import requests
from bs4 import BeautifulSoup
import sqlite3

def coletar_seletivo():
    categorias = {
       # Mercearia
        "Arroz": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-basica-arroz-5/",
        "Feijão": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-basica-feijao-78/",
        "Óleo": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-basica-oleo-24/",
        "Café": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-basica-cafe-76/",
        "Macarrão": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-basica-massas-81/",
        "Farinaceos-grãos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/mercearia-salgada-farinaceos-graos-44",
        
        # Perecíveis
        "Hortifruti": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/hortifrutigranjeiro-1/",
        "Açougue": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/acougue-47/",
        "Peixaria": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/peixaria-82",
        "Leite": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/leites-iogurtes-e-achocolatados-leites-62/",
        "Ovos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/ovos-91/",
        "Padaria": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/padaria-50",
        
        # Higiene e Limpeza
        "Limpeza": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/limpeza-122/",
        "Higiene": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/higiene-e-cuidados-pessoais-102/",

        # Pet Shop
        "Pet Shop": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/pet-shop-14",

        # Magazine
        "Magazine": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/magazine-16"
    }
    # Cria o banco de dados local na hora
    conn = sqlite3.connect('arca.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS links (url TEXT PRIMARY KEY, nome TEXT, cat TEXT)''')

    for nome_cat, url in categorias.items():
        print(f"🔍 Raspando: {nome_cat}")
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            produtos = soup.find_all('a', class_='ktiOQb')[:6]

            for item in produtos:
                link = "https://www.goodbom.com.br" + item['href']
                nome = item.find('span', class_='product-name').get_text().strip()
                print(f"   ✅ {nome}")
                cursor.execute("INSERT OR REPLACE INTO links VALUES (?, ?, ?)", (link, nome, nome_cat))
            conn.commit()
        except Exception as e:
            print(f"❌ Erro: {e}")

    conn.close()
    print("\n🚀 TUDO SALVO NO ARCA.DB!")

if __name__ == "__main__":
    coletar_seletivo()

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
        "Legumes": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/legumes-30/",
        "Frutas": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/frutas-49",
        "Verduras": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Verdura",
        "Bovino": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/bovino-114",
        "Avicola": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/avicola-48",
        "Suino": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/suino-97",
        "Peixaria": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/peixaria-82",
        "Leite": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Leite",
        "Embutidos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/frios-e-embutidos-embutidos-38",
        "Congelados-doces": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/congelados-doces-10",
        "Conservas": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/refrigerados-conservas-94",
        "Ovos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Ovos",
        "Padaria": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/padaria-51",
        "Padaria produção propria": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/producao-propria-123",
        
        # Higiene e Limpeza
        "Limpeza sabão": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Sab%C3%A3o",
        "Limpeza detergente": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Detergente",
        "Limpeza pesada": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Limpeza%20pesada",
        "Higiene pessoal": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=higiene-pessoal",
        "Sabonete": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Sabonete",
        "Shampoo": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Shampoo",
        "Creme dental": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/busca?q=Creme%20dental",

        # Pet Shop
        "Pet Shop Alimentos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/pet-shop-15",
        "Pet-shop Alimentos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/alimentos-15?ordem=HIGHER_PRICE&menor=3.19&maior=140.9&page=1",
        "Pet shop higiene e limpeza": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/higiene-e-limpeza-84",

        # Magazine
        "Magazine automotivo": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/automotivo-60",
        "Magazine utilidades de limpeza": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/utilidades-de-limpeza-93",
        "Magazine brinquedos": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/brinquedos-96",
        "Magazine esporte lazer": "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/esportelazer-40",
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
            produtos = soup.find_all('a', class_='ktiOQb')[:30]

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

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

def coletar_seletivo():
    # Adicionei a barra "/" ao final das novas URLs para evitar erros de redirecionamento
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
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client.arca_db
        colecao = db.links_monitorados
    except Exception as e:
        print(f"❌ Erro ao conectar no MongoDB: {e}")
        return

    for nome_cat, url in categorias.items():
        print(f"\n🔍 Buscando itens de: {nome_cat}")
        
        try:
            # User-Agent ajuda a não ser bloqueado como robô
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            produtos = soup.find_all('a', class_='ktiOQb')[:6]
            
            if not produtos:
                print(f"⚠️ Nenhum produto encontrado em {nome_cat}. Verifique a URL.")

            for item in produtos:
                path = item['href']
                full_link = "https://www.goodbom.com.br" + path
                nome_prod = item.find('span', class_='product-name').get_text()
                
                print(f"   📌 {nome_prod}") # Mostra o produto no terminal

                colecao.update_one(
                    {"url": full_link},
                    {"$set": {
                        "url": full_link, 
                        "nome": nome_prod, 
                        "categoria": nome_cat,
                        "mercado": "GoodBom"
                    }},
                    upsert=True
                )
        except Exception as e:
            print(f"❌ Erro ao acessar {nome_cat}: {e}")

    print("\n✅ Base de dados do GoodBom atualizada com sucesso!")

if __name__ == "__main__":
    coletar_seletivo()
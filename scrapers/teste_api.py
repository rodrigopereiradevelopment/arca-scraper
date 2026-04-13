import requests
import json

# A URL do produto que você mandou
url = "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/manteiga-extra-csal-catupiry-200g-7366"

# O 'Rsc': '1' avisa ao servidor que você quer os dados (JSON) e não o site inteiro (HTML)
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Rsc": "1" 
}

try:
    response = requests.get(url, headers=headers)
    
    # O formato do Next.js vem com uns números no início (ex: 2:[...])
    # Vamos limpar o texto para transformar em JSON puro
    raw_text = response.text
    json_data = raw_text.split(':', 1)[1] # Pega tudo depois do primeiro ':'
    
    data = json.loads(json_data)
    
    # Navegando na estrutura que você descobriu
    produto = data[0]['product']
    nome = produto['name']
    preco_com_desconto = produto['priceWithDiscount']
    preco_normal = produto['price']

    print(f"--- Produto Encontrado ---")
    print(f"Nome: {nome}")
    print(f"Preço Normal: R$ {preco_normal}")
    print(f"Preço ARCA (Desconto): R$ {preco_com_desconto}")

except Exception as e:
    print(f"Erro ao processar: {e}")
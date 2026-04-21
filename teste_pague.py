import requests
from bs4 import BeautifulSoup

url = "https://www.superpaguemenos.com.br/hortifruti"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8"
}

print(f"🚀 [ARCA] Testando raspagem via HTML em: {url}")

try:
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Busca os blocos de produtos
    itens = soup.find_all(class_='item-product')
    
    if not itens:
        print("⚠️  Nenhum item encontrado com 'item-product'. Tentando seletores genéricos...")
        itens = soup.select('.shelf-item') or soup.select('li[data-id]')

    print(f"📦 Encontrados {len(itens)} possíveis produtos.\n")

    for i, item in enumerate(itens[:15]): 
        try:
            # 1. Busca o nome no atributo 'title' da imagem (que vimos no seu debug!)
            img_tag = item.find('img')
            nome = img_tag.get('title') if img_tag else "Nome não encontrado"

            # 2. Busca o preço no item-price (que é o padrão desse layout)
            # Vamos tentar 'price' e 'item-price'
            preco_tag = item.find(class_='item-price') or item.find(class_='best-price')
            
            # Se o preço for um bloco com vários textos, pegamos o texto limpo
            preco = preco_tag.get_text(strip=True) if preco_tag else "R$ 0,00"
            
            # 2. Busca o preço de forma mais abrangente
            # Tentamos as classes mais comuns da VTEX Legada
            preco_tag = item.find(class_='best-price') or \
                        item.find(class_='item-price') or \
                        item.find(class_='valor')
            
            if preco_tag:
                preco = preco_tag.get_text(strip=True)
            else:
                # Se não achou pela classe, procura qualquer tag que contenha "R$"
                fallback_preco = item.find(lambda tag: tag.name in ['span', 'div', 'strong'] and 'R$' in tag.text)
                preco = fallback_preco.get_text(strip=True) if fallback_preco else "R$ 0,00"

            print(f"{i+1}. ✅ {nome} -> {preco}")
            
        except Exception as e:
            print(f"❌ Erro no item {i}: {e}")

except Exception as e:
    print(f"❌ Erro geral: {e}")
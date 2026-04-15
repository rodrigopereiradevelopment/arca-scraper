from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

chrome_options = Options()
chrome_options.add_argument('--headless') # Sem janela
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# O segredo do Termux é apontar para o binário do Chromium que você instalou
service = Service('/data/data/com.termux/files/usr/bin/chromedriver')

driver = webdriver.Chrome(service=service, options=chrome_options)

print("🌐 Acessando São Vicente pelo Celular...")
driver.get("https://www.svicente.com.br/arroz-tipo-1-agulhinha-camil-5kg/p")

# Pega o título só pra testar
print(f"✅ Título capturado: {driver.title}")

driver.quit()

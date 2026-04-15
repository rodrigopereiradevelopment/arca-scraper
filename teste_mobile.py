from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
# Bloqueia tudo que pesa: imagens, extensões e GPU
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--blink-settings=imagesEnabled=false')
chrome_options.add_argument('--incognito')

service = Service('/data/data/com.termux/files/usr/bin/chromedriver')

try:
    print("🚀 Iniciando motor do Chromium...")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    
    print("🌐 Acessando site...")
    driver.get("https://www.google.com") # Teste primeiro com o Google (é mais leve)
    
    print(f"✅ Conectado! Título: {driver.title}")
    driver.quit()
except Exception as e:
    print(f"❌ Erro: {e}")

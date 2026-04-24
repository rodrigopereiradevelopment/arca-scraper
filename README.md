![CI Arca Scraper](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/main.yml/badge.svg)

# 🛒 ARCA - Inteligência em Preços (Mogi Mirim)

O **ARCA** é um ecossistema de captura e análise de dados focado no varejo de Mogi Mirim. O objetivo é centralizar preços de 6 grandes redes de supermercados, permitindo uma comparação precisa e em tempo real para o consumidor final.

## 🚀 Jornada Técnica

O projeto evoluiu através de etapas críticas de engenharia de dados:

* **Mapeamento de Alvos:** Análise técnica dos portais de 6 mercados para identificar tecnologias de renderização (SSR, SPAs e APIs).
* **Validação de Captura (BS4 & Playwright):** Prototipagem inicial usando raspagem de HTML e automação de navegador.
* **Migração para APIs (Otimização):** Transição estratégica para o consumo de APIs internas (REST, GraphQL e Feeds), reduzindo drasticamente o tempo de execução e o consumo de banda.
* **Escalabilidade & Big Data:** Implementação de rotinas para carga total (estimada em +15.000 itens por mercado).
* **Resiliência de Infraestrutura:** * **Gerenciamento de Tráfego:** Implementação de `time.sleep` e rotação de headers para evitar bloqueios de IP (Anti-Bot).
    * **Volume de Dados:** Otimização de escritas em lote (*Bulk Write*) para garantir que o **MongoDB Atlas** suporte o volume massivo sem estourar o buffer de memória.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.12
* **Banco de Dados:** MongoDB Atlas (Cloud NoSQL)
* **Bibliotecas Principais:** `requests`, `pymongo`, `beautifulsoup4`
* **Ambiente de Dev:** Linux Mint (Desktop) & Termux (Mobile)
* **CI/CD:** GitHub Actions para análise estática de código.

## 📖 Como Usar

1. **Clonar o repositório:**
```bash
git clone [https://github.com/rodrigopereiradevelopment/arca-scraper.git](https://github.com/rodrigopereiradevelopment/arca-scraper.git)
cd arca-scraper
```

2. **Configurar o ambiente:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **⚙️ Configurar Variáveis de Ambiente** (.env):
Crie um arquivo .env na raiz do projeto e cole o seguinte (ajustando suas credenciais):
```bash
# Banco de Dados
MONGO_URI=mongodb+srv://<USUARIO>:<SENHA>@arca-cluster.xo5yomu.mongodb.net/?appName=arca-cluster

# Chave pública diária (Ponto Novo)
API_AUTHORIZATION_TOKEN=owrF028ztCGzNh2nIr57mq447qKveGHr6bEGsgVPmjuxbiWPiZ5s2P0wEEjC9SXbZsh3r0JCXSvV4CRuRNrQQJ6mrav1C3mFfgyZ
```

4. **Executar o pipeline completo:**
```bash
python3 main.py
```

**🛡️ Segurança**
: O arquivo .env real contém suas credenciais privadas e nunca deve ser enviado para o GitHub. Ele já está listado no .gitignore deste projeto.
```

## ⚠️ Aviso Ético e Legal

​Este projeto foi desenvolvido estritamente para fins educacionais e como Trabalho de Conclusão de Curso (TCC). O scraper respeita os intervalos de requisição para não sobrecarregar os servidores dos estabelecimentos citados. Os dados coletados são de domínio público.

## ⚖️ Licença

​Este projeto está sob a licença MIT - veja o arquivo LICENSE para detalhes.

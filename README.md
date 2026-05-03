# 🛒 ARCA - Comparação de Preços (Mogi Mirim)

![Pipeline Status](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/ci.yml/badge.svg)

O **ARCA** é um ecossistema de captura e análise de dados focado no varejo de Mogi Mirim. O objetivo é centralizar preços de **6 grandes redes de supermercados**, permitindo uma comparação precisa para o consumidor final.

---

## 🏪 Mercados Monitorados

| Mercado | Método | Produtos |
|---------|--------|----------|
| **Atacadão** | GraphQL API | ~8.400 |
| **São Vicente** | API Demandware | ~13.200 |
| **Pague Menos** | HTML Parsing | ~16.200 |
| **Ponto Novo** | API REST (MobileSim) | ~5.200 |
| **Imperial** | API REST (MobileSim) | ~3.100 |
| **GoodBom** | HTML Parsing (Regex) | ~11.100 |
| **TOTAL** | | **~57.000** |

---

## 🧠 Arquitetura de Dados (Bronze → Silver → Gold)

```
arca_bronze (dados crus) → limpeza_silver.py → arca_silver (dados padronizados)
│                                                        │
6 scrapers                                        arca-ionic (app mobile)
(upsert diário)                                   (consome via Supabase)
```

---

## ⚡ Performance (Otimizações)

| Scraper | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| **Atacadão** | 1h30 | **4min** | **-95%** |
| **São Vicente** | 3h00 | **56min** | **-69%** |
| **GoodBom** | 1h00 | **32min** | **-47%** |
| **Pipeline total** | ~5h45 | **~3h20** | **-43%** |

**Técnicas utilizadas:**
- `ThreadPoolExecutor` para paralelismo (3-5 workers)
- `bulk_write` no MongoDB (lotes de 50-1000)
- Normalização centralizada na `BaseScraper`
- Conexões independentes por thread

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.12
- **Banco de Dados:** MongoDB Atlas (Cloud NoSQL)
- **Bibliotecas:** `requests`, `pymongo`, `beautifulsoup4`, `ftfy`, `python-dotenv`
- **CI/CD:** GitHub Actions (execução semanal automática)
- **Dev:** Linux Mint (Desktop) + Termux (Mobile)

---

## 🚀 Instalação e Uso

### 1. Clonar o repositório

```bash
git clone https://github.com/rodrigopereiradevelopment/arca-scraper.git
cd arca-scraper
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
MONGO_URI=mongodb+srv://<USUARIO>:<SENHA>@arca-cluster.xo5yomu.mongodb.net/
IMPERIAL_TOKEN=seu_token_aqui
API_AUTHORIZATION_TOKEN=seu_token_aqui
```

### 4. Executar

```bash
python3 main.py
```

---

## 📊 Estrutura do Projeto

```
arca-scraper/
├── scrapers/
│   ├── base_scraper.py      # Classe base (conexão, normalização, upsert)
│   ├── atacadao.py          # GraphQL (104 subcategorias, paralelo)
│   ├── sao_vicente.py       # API Demandware (15 categorias, paralelo)
│   ├── paguemenos.py        # HTML parsing (13 categorias)
│   ├── goodbom.py           # Regex parsing (9 categorias, paralelo)
│   ├── imperial.py          # API MobileSim
│   └── ponto_novo.py        # API MobileSim
├── limpeza_silver.py        # Pipeline Bronze → Silver
├── main.py                  # Orquestrador principal
├── requirements.txt
└── .github/workflows/       # CI/CD (segunda-feira 00:00 BRT)
```

---

## 🔄 Pipeline Automatizado

O GitHub Actions executa automaticamente:

- **Schedule:** Toda segunda-feira às 00:00 (horário de Brasília)
- **Push:** A cada novo commit na branch `main`
- **Manual:** Via botão "Run workflow" no GitHub

Tempo médio: **~3h20** (limite: 6h)

---

## ⚠️ Aviso Ético e Legal

Este projeto foi desenvolvido para fins educacionais como Trabalho de Conclusão de Curso (TCC) na ETEC Pedro Ferreira Alves.

- ✅ Respeita intervalos de requisição (`time.sleep`)
- ✅ User-Agent identificado como bot acadêmico
- ✅ Dados coletados são de domínio público
- ✅ Sem intenção de sobrecarregar servidores

---

## 📄 Licença

Este projeto está sob a licença MIT — veja o arquivo `LICENSE` para detalhes.

---

## 👤 Autor

**Rodrigo Pereira**  
GitHub: [@rodrigopereiradevelopment](https://github.com/rodrigopereiradevelopment)  
Contato: [rodrigopereira.development@gmail.com](mailto:rodrigopereira.development@gmail.com)  
Projeto relacionado: [arca-ionic](https://github.com/rodrigopereiradevelopment/arca-ionic) (App Mobile)

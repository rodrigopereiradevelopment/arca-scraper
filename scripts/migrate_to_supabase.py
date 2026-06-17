# scripts/migrate_to_supabase.py
"""
Migração completa do MongoDB para Supabase
Versão Python equivalente ao TypeScript original
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from pymongo import MongoClient
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONSTANTES E MAPEAMENTOS
# ============================================================

# Mapeamento mercado -> supermercado_id (baseado no seu Supabase)
MERCADO_PARA_SUPERMERCADO_ID: Dict[str, int] = {
    "Imperial": 1,
    "Ponto Novo": 2,
    "GoodBom": 3,
    "Atacadão": 4,
    "Pague Menos": 5,
    "PagueMenos": 5,
    "São Vicente": 6,
}

# Mapeamento categoria -> categoria_id (ajuste conforme seu banco)
CATEGORIA_PARA_ID: Dict[str, int] = {
    # Frios e Laticínios
    "laticinios": 1,
    "frios e laticinios": 1,
    "frios-laticinios": 1,
    "frios": 1,
    "frios e congelados": 1,
    "frios laticinios": 1,
    # Açougue / Carnes
    "acougue": 2,
    "acougue-47": 2,
    "carnes aves peixes": 2,
    "carnes": 2,
    "peixaria-82": 2,
    "peixaria": 2,
    # Bebidas
    "bebidas": 3,
    "bebidas alcoolicas": 3,
    "bebidas alcoólicas": 3,
    "bebidas-alcoolicas": 3,
    "agua": 3,
    "cerveja": 3,
    "sucos": 3,
    # Higiene e Limpeza
    "higiene": 4,
    "higiene e beleza": 4,
    "higiene-beleza": 4,
    "limpeza": 4,
    "petshop": 4,
    "mundo pet": 4,
    "mamae e bebe": 4,
    # Padaria
    "padaria": 5,
    "padaria-50": 5,
    # Hortifruti
    "hortifruti": 6,
    "hortifrutigranjeiro-1": 6,
    "frutas e verduras": 6,
    "hortifrúti": 6,
    # Mercearia / Grãos
    "cafe da manha": 7,
    "café da manhã": 7,
    "cafe-da-manha": 7,
    "cafe": 7,
    "café": 7,
    "graos": 7,
    "mercearia": 9,
    "congelados": 8,
    "congelados-6": 8,
    "bazar": 9,
    "magazine-16": 9,
    "utilidades": 9,
    "saudaveis organicos": 7,
    # Snacks / Doces
    "biscoitos salgadinhos": 10,
    "doces sobremesas": 10,
    "biscoitos": 10,
    "doces": 10,
    "lanchonete": 9,
}

# Mapeamento para códigos numéricos (Ponto Novo)
PONTO_NOVO_MAP: Dict[int, int] = {
    4112: 7,   # mercearia
    2015: 3,   # bebidas
    3382: 4,   # higiene-e-beleza
    1348: 4,   # limpeza
    1292: 9,   # bazar
    1009: 1,   # frios-e-laticinios
    1072: 7,   # cafe-da-manha
    576: 8,    # congelados
    823: 4,    # mamae-e-bebe
    425: 4,    # petshop
    314: 2,    # acougue
    249: 6,    # hortifruti
    419: 9,    # festivos
}

# Mapeamento para códigos string (Atacadão)
ATACADAO_MAP: Dict[str, int] = {
    "012": 7,  # Mercearia
    "002": 3,  # Bebidas
    "003": 3,  # Bebidas Alcoolicas
    "010": 6,  # Hortifruti
    "005": 2,  # Carnes Aves Peixes
    "008": 1,  # Frios Laticinios
    "006": 8,  # Congelados
    "009": 4,  # Higiene Beleza
    "011": 4,  # Limpeza
    "004": 10, # Biscoitos Salgadinhos
    "007": 10, # Doces Sobremesas
    "015": 5,  # Padaria
    "016": 7,  # Saudaveis Organicos
    "001": 9,  # Bazar Utilidades
    "014": 4,  # Mundo Pet
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def is_ean_valido(ean: Optional[str]) -> bool:
    """Valida se é um EAN real (8 ou 13 dígitos, apenas números)"""
    if not ean:
        return False
    return bool(re.match(r'^\d{8}$|^\d{13}$', ean))


def extrair_marca(nome: str, marca_mongo: Optional[str]) -> str:
    """Extrai marca real do nome do produto"""
    if marca_mongo and marca_mongo != "N/A":
        return marca_mongo
    partes = nome.split(" ")
    return " ".join(partes[:2])


def normalizar_categoria(categoria: str, mercado: str, nome: str = "") -> Optional[int]:
    """Normaliza categoria de qualquer mercado para o categoria_id do Supabase"""
    if not categoria:
        return None

    # Override por nome do produto (corrige erros de classificação dos mercados)
    nome_upper = nome.upper() if nome else ""
    if nome_upper:
        # Grãos e Cereais (7)
        if re.search(r'\b(ARROZ|FEIJÃO|FEIJAO|FARINHA|AÇÚCAR|ACUCAR|CAFÉ|CAFE|MACARRÃO|MACARRAO|FUBÁ|FUBA|LENTILHA|ERVILHA|SOJA|GRÃO DE BICO|GRAO DE BICO)\b', nome_upper):
            return 7
        # Laticínios (1)
        if re.search(r'\b(LEITE|QUEIJO|MANTEIGA|IOGURTE|CREME DE LEITE|REQUEIJÃO|REQUEIJAO|MUÇARELA|MUCARELA|PRATO|MINAS|CHEDDAR|RICOTA|COTAGE)\b', nome_upper):
            return 1
        # Carnes e Peixes (2)
        if re.search(r'\b(CARNE|FRANGO|PEIXE|BOVINO|SUÍNO|SUINO|FILE|FILÉ|PICANHA|ALCATRA|COXÃO|COXAO|PATINHO|MAMINHA|ACÉM|ACEM|PALETA|LINGUIÇA|LINGUICA|SALSICHA|HAMBURGUER|BISTECA|COSTELA|CORDEIRO)\b', nome_upper):
            return 2
        # Bebidas (3)
        if re.search(r'\b(ÁGUA|AGUA|REFRIGERANTE|SUCO|CERVEJA|VINHO|ENERGÉTICO|ENERGETICO|ISOTÔNICO|ISOTONICO|CHÁ|CHA|LEITE|NÉCTAR|NECTAR)\b', nome_upper) and not re.search(r'\b(LEITE EM PÓ|LEITE EM PO|LEITE CONDENSADO|CREME DE LEITE)\b', nome_upper):
            return 3
        # Higiene e Limpeza (4)
        if re.search(r'\b(SABÃO|SABAO|SABONETE|DETERGENTE|DESODORANTE|SHAMPOO|CONDICIONADOR|ESCOVA DENTAL|PASTA DENTAL|CREME DENTAL|FRALDA|ABSORVENTE|PAPEL HIGIÊNICO|PAPEL HIGIENICO|LENÇO|LENCO|ALVEJANTE|ÁGUA SANITARIA|AGUA SANITARIA|DESINFETANTE|INSETICIDA|AMACIANTE|ESPONJA|LIMPADOR|SABÃO EM PÓ|SABAO EM PO|DETERGENTE EM PÓ)\b', nome_upper):
            return 4
        # Padaria (5)
        if re.search(r'\b(PÃO|PAO|PÃO DE QUEIJO|PAO DE QUEIJO|BISNAGA|BAGUETE|BROA|CROISSANT|BOLO|TORRADA|SONHO|PÃO FRANCÊS|PAO FRANCES)\b', nome_upper):
            return 5
        # Frutas e Verduras (6)
        if re.search(r'\b(BANANA|MAÇÃ|MAÇA|LARANJA|UVA|MAMÃO|MAMAO|ABACAXI|MELANCIA|ALFACE|TOMATE|CEBOLA|BATATA|CENOURA|CHUCHU|ABOBRINHA|VAGEM|BRÓCOLIS|BROCOLIS|COUVE|ESPINAFRE|ALHO)\b', nome_upper):
            return 6
        # Congelados (8)
        if re.search(r'\b(SORVETE|PIZZA|LASANHA|NUGGETS|BATATA FRITA|HAMBÚRGUER CONGELADO|HAMBURGUER CONGELADO)\b', nome_upper):
            return 8

    cat_lower = categoria.lower().strip()

    # Mapeamento direto
    if cat_lower in CATEGORIA_PARA_ID:
        return CATEGORIA_PARA_ID[cat_lower]

    # Códigos numéricos (Ponto Novo)
    if cat_lower.isdigit():
        codigo = int(cat_lower)
        if codigo in PONTO_NOVO_MAP:
            return PONTO_NOVO_MAP[codigo]

    # Códigos string (Atacadão)
    if cat_lower in ATACADAO_MAP:
        return ATACADAO_MAP[cat_lower]

    return None


def mapear_tipo(categoria: str, categoria_id: Optional[int]) -> str:
    """Mapeia tipo do produto baseado na categoria_id"""
    if categoria_id:
        tipo_por_categoria = {2: "acougue", 5: "padaria", 6: "hortifruti"}
        if categoria_id in tipo_por_categoria:
            return tipo_por_categoria[categoria_id]

    cat_lower = categoria.lower() if categoria else ""
    if "acougue" in cat_lower or "carne" in cat_lower or "peixe" in cat_lower:
        return "acougue"
    if "padaria" in cat_lower or "pao" in cat_lower or "pão" in cat_lower:
        return "padaria"
    if "hortifruti" in cat_lower or "fruta" in cat_lower or "verdura" in cat_lower:
        return "hortifruti"
    if "lanchonete" in cat_lower:
        return "lanchonete"

    return "industrializado"


# ============================================================
# FUNÇÃO PRINCIPAL DE MIGRAÇÃO
# ============================================================

def migrate_products_to_supabase(batch_size: int = 100):
    """
    Migração completa: produtos + preço atual + histórico
    """
    # Conexões
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    mongo_db = mongo_client["arca_bronze"]
    collection = mongo_db["produtos"]

    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    total = collection.count_documents({})
    migrados = 0
    ja_existiam = 0
    erros_produto = 0
    precos_inseridos = 0
    historico_inserido = 0
    erros_preco = 0

    categorias_nao_mapeadas = set()
    mercados_nao_mapeados = set()

    print(f"🔄 Iniciando migração de {total} produtos...")

    for skip in range(0, total, batch_size):
        batch = list(collection.find({}).skip(skip).limit(batch_size))
        print(f"\n📦 Lote {skip // batch_size + 1}: {len(batch)} produtos")

        for mongo_product in batch:
            try:
                # 1. Buscar produto existente por nome normalizado
                existing = supabase.table("produtos") \
                    .select("id") \
                    .eq("nome", mongo_product.get("nome_normalizado")) \
                    .limit(1) \
                    .execute()

                produto_id = None

                if not existing.data:
                    # 2. Inserir novo produto
                    categoria_id = normalizar_categoria(
                        mongo_product.get("categoria", ""),
                        mongo_product.get("mercado", ""),
                        mongo_product.get("nome", "")
                    )

                    if categoria_id is None and mongo_product.get("categoria"):
                        categorias_nao_mapeadas.add(
                            f'"{mongo_product.get("categoria")}" ({mongo_product.get("mercado")})'
                        )

                    # Verifica EAN duplicado
                    ean_para_usar = None
                    if is_ean_valido(mongo_product.get("ean")):
                        ean_exists = supabase.table("produtos") \
                            .select("id") \
                            .eq("codigo_barras", mongo_product.get("ean")) \
                            .maybe_single() \
                            .execute()

                        if not ean_exists.data:
                            ean_para_usar = mongo_product.get("ean")

                    # Insere produto
                    produto_data = {
                        "nome": mongo_product.get("nome_normalizado"),
                        "marca": extrair_marca(
                            mongo_product.get("nome", ""),
                            mongo_product.get("marca")
                        ),
                        "codigo_barras": ean_para_usar,
                        "imagem_url": mongo_product.get("url_imagem"),
                        "categoria_id": categoria_id,
                        "tipo": mapear_tipo(
                            mongo_product.get("categoria", ""),
                            categoria_id
                        ),
                        "ativo": True,
                    }

                    result = supabase.table("produtos") \
                        .insert(produto_data) \
                        .select("id") \
                        .single() \
                        .execute()

                    produto_id = result.data["id"]
                    migrados += 1
                else:
                    produto_id = existing.data[0]["id"]
                    ja_existiam += 1

                # 3. Processar preços
                supermercado_id = MERCADO_PARA_SUPERMERCADO_ID.get(mongo_product.get("mercado", ""))
                if not supermercado_id:
                    mercados_nao_mapeados.add(mongo_product.get("mercado", ""))
                    continue

                todos_os_precos = []

                # Preço atual
                preco_atual = mongo_product.get("preco_atual")
                if preco_atual:
                    data_coleta = mongo_product.get("data_ultima_coleta")
                    if isinstance(data_coleta, datetime):
                        data_coleta_str = data_coleta.isoformat()
                    else:
                        data_coleta_str = data_coleta

                    todos_os_precos.append({
                        "preco": preco_atual,
                        "data_coleta": data_coleta_str,
                        "promocao": False,
                        "fonte_dados": "scraping",
                        "produto_id": produto_id,
                        "supermercado_id": supermercado_id,
                    })

                # Histórico de preços
                historico = mongo_product.get("historico_precos", [])
                data_ultima_coleta = mongo_product.get("data_ultima_coleta")

                if isinstance(data_ultima_coleta, datetime):
                    data_ultima_coleta_str = data_ultima_coleta.strftime("%Y-%m-%d")
                else:
                    data_ultima_coleta_str = str(data_ultima_coleta)[:10] if data_ultima_coleta else ""

                for h in historico:
                    if not h.get("preco") or not h.get("data"):
                        continue

                    data_hist = h.get("data")
                    if isinstance(data_hist, datetime):
                        data_hist_str = data_hist.strftime("%Y-%m-%d")
                    else:
                        data_hist_str = str(data_hist)[:10]

                    if data_hist_str == data_ultima_coleta_str:
                        continue

                    todos_os_precos.append({
                        "preco": h.get("preco"),
                        "data_coleta": h.get("data"),
                        "promocao": False,
                        "fonte_dados": "scraping",
                        "produto_id": produto_id,
                        "supermercado_id": supermercado_id,
                    })

                # 4. Inserir todos os preços
                if todos_os_precos:
                    result = supabase.table("precos") \
                        .insert(todos_os_precos) \
                        .execute()

                    if result.data:
                        precos_inseridos += 1
                        historico_inserido += len(todos_os_precos) - 1
                    else:
                        erros_preco += 1

            except Exception as e:
                print(f"❌ Erro no produto {mongo_product.get('nome', 'unknown')}: {e}")
                erros_produto += 1

        print(f"✅ Lote concluído. Progresso: {min(skip + batch_size, total)}/{total}")

    # Relatório final
    print(f"\n🎉 Migração concluída!")
    print(f"  📦 Produtos novos:      {migrados}")
    print(f"  ♻️  Já existiam:         {ja_existiam}")
    print(f"  💰 Preços inseridos:    {precos_inseridos}")
    print(f"  📜 Histórico inserido:  {historico_inserido}")
    print(f"  ❌ Erros produto:       {erros_produto}")
    print(f"  ❌ Erros preço:         {erros_preco}")

    if categorias_nao_mapeadas:
        print(f"\n⚠️  Categorias não mapeadas ({len(categorias_nao_mapeadas)} únicas):")
        for c in sorted(categorias_nao_mapeadas):
            print(f"   - {c}")

    if mercados_nao_mapeados:
        print(f"\n⚠️  Mercados não mapeados ({len(mercados_nao_mapeados)} únicos):")
        for m in sorted(mercados_nao_mapeados):
            print(f"   - {m}")

    return {
        "migrados": migrados,
        "ja_existiam": ja_existiam,
        "precos_inseridos": precos_inseridos,
        "historico_inserido": historico_inserido,
        "erros_produto": erros_produto,
        "erros_preco": erros_preco,
        "total": total
    }


# ============================================================
# SINCRONIZAÇÃO DIÁRIA
# ============================================================

def sync_updated_prices():
    """Sincronização diária — insere apenas produtos/preços das últimas 24h"""
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    mongo_db = mongo_client["arca_bronze"]
    collection = mongo_db["produtos"]

    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    ontem = datetime.now() - timedelta(days=1)

    produtos_atualizados = list(collection.find({
        "data_ultima_coleta": {"$gte": ontem}
    }))

    print(f"🔄 Sincronizando {len(produtos_atualizados)} produtos atualizados...")

    precos_inseridos = 0
    erros = 0

    for produto in produtos_atualizados:
        try:
            # Busca produto no Supabase
            supabase_produto = supabase.table("produtos") \
                .select("id") \
                .eq("nome", produto.get("nome_normalizado")) \
                .maybe_single() \
                .execute()

            if not supabase_produto.data:
                continue

            supermercado_id = MERCADO_PARA_SUPERMERCADO_ID.get(produto.get("mercado", ""))
            if not supermercado_id or not produto.get("preco_atual"):
                continue

            data_coleta = produto.get("data_ultima_coleta")
            if isinstance(data_coleta, datetime):
                hoje = data_coleta.strftime("%Y-%m-%d")
                data_coleta_str = data_coleta.isoformat()
            else:
                hoje = str(data_coleta)[:10]
                data_coleta_str = data_coleta

            # Verifica se já existe preço para hoje
            ja_existe = supabase.table("precos") \
                .select("id") \
                .eq("produto_id", supabase_produto.data["id"]) \
                .eq("supermercado_id", supermercado_id) \
                .gte("data_coleta", f"{hoje}T00:00:00") \
                .lt("data_coleta", f"{hoje}T23:59:59") \
                .maybe_single() \
                .execute()

            if ja_existe.data:
                continue

            # Insere novo preço
            result = supabase.table("precos") \
                .insert({
                    "preco": produto.get("preco_atual"),
                    "data_coleta": data_coleta_str,
                    "promocao": False,
                    "fonte_dados": "scraping",
                    "produto_id": supabase_produto.data["id"],
                    "supermercado_id": supermercado_id,
                }) \
                .execute()

            if result.data:
                precos_inseridos += 1
            else:
                erros += 1

        except Exception as e:
            print(f"❌ Erro em {produto.get('nome', 'unknown')}: {e}")
            erros += 1

    print(f"💰 {precos_inseridos} novos preços sincronizados")
    print(f"✅ Sync concluído! Preços inseridos: {precos_inseridos} | Erros: {erros}")
    return {"precos_inseridos": precos_inseridos, "erros": erros, "total_processados": len(produtos_atualizados)}


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="Apenas sincronização diária")
    parser.add_argument("--batch", type=int, default=100, help="Tamanho do lote")
    args = parser.parse_args()

    if args.sync:
        sync_updated_prices()
    else:
        migrate_products_to_supabase(batch_size=args.batch)
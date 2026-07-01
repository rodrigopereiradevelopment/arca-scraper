"""
Sync de UM mercado específico para o Supabase
Executado em paralelo pelo GitHub Actions
"""

import os
import re
import argparse
from datetime import datetime
from pymongo import MongoClient
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MERCADO_IDS = {
    "atacadao": 4,
    "sao_vicente": 6,
    "pague_menos": 5,
    "ponto_novo": 2,
    "imperial": 1,
    "goodbom": 3,
}

MERCADO_DISPLAY = {
    "atacadao": "Atacadão",
    "sao_vicente": "São Vicente",
    "pague_menos": "PagueMenos",
    "ponto_novo": "Ponto Novo",
    "imperial": "Imperial",
    "goodbom": "GoodBom",
}

CATEGORIA_IDS = {
    "acougue": 2, "acougue-47": 2,
    "bebidas": 3, "bebidas alcoolicas": 3, "bebidas alcoólicas": 3, "bebidas-alcoolicas": 3,
    "agua": 3, "cerveja": 3, "sucos": 3,
    "frios e laticinios": 1, "frios laticinios": 1, "frios e congelados": 1, "frios": 1,
    "hortifruti": 6, "hortifrutigranjeiro": 6, "hortifrutigranjeiro-1": 6,
    "frutas e verduras": 6, "hortifrúti": 6,
    "higiene e beleza": 4, "higiene beleza": 4, "higiene-beleza": 4,
    "higiene": 4, "limpeza": 4, "petshop": 4, "pet shop": 4,
    "mundo pet": 4, "mamae e bebe": 4,
    "mercearia": 9, "padaria": 5, "padaria-50": 5,
    "congelados": 8, "congelados-6": 8,
    "bazar": 9, "magazine": 9, "magazine-16": 9,
    "utilidades": 9, "lanchonete": 9,
    "cafe da manha": 7, "café da manhã": 7, "cafe-da-manha": 7,
    "cafe": 7, "café": 7, "graos": 7, "saudaveis organicos": 7,
    "biscoitos salgadinhos": 10, "doces sobremesas": 10,
    "biscoitos": 10, "doces": 10,
    "peixaria": 2, "peixaria-82": 2,
    "carnes aves peixes": 2, "carnes": 2,
}


def normalizar_categoria(categoria: str, nome: str = "") -> int | None:
    if not categoria:
        return None

    nome_upper = nome.upper() if nome else ""
    if nome_upper:
        if re.search(r'\b(BISCOITO|BOLACHA|SALGADINHO|CHIPS|SNACKS|TORRESMO|AMENDOIM|CHOCOLATE|BALAS|PIRULITO|CHICLETE|BOMBOM|WAFER|WAFFER|GOMA|DOCE|GELEIA|GOIABADA|MARSHMALLOW|CONFEITO|GRANULADO)\b', nome_upper):
            return 10
        if re.search(r'\b(ARROZ|FEIJÃO|FEIJAO|FARINHA|FARELO|FUBÁ|FUBA|AÇÚCAR|ACUCAR|ADOCANTE|CAFÉ|CAFE|MACARRÃO|MACARRAO|ESPAGUETE|LAMEN|MIOJO|LENTILHA|ERVILHA|GRÃO DE BICO|GRAO DE BICO|SOJA)\b', nome_upper):
            return 7
        if re.search(r'\b(LEITE|QUEIJO|MANTEIGA|MARGARINA|IOGURTE|REQUEIJÃO|REQUEIJAO|MUÇARELA|MUCARELA|PRATO|MINAS|CHEDDAR|RICOTA|COTAGE|CREME DE LEITE|CREME DELEITE|NATA|COALHADA)\b', nome_upper):
            return 1
        if re.search(r'\b(CARNE|FRANGO|PEIXE|BOVINO|SUÍNO|SUINO|PICANHA|ALCATRA|COXÃO|COXAO|LINGUIÇA|LINGUICA|SALSICHA|HAMBURGUER|BACON|PERNIL|LOMBO|PEITO DE FRANGO|COSTELA|CORDEIRO|BISTECA)\b', nome_upper):
            return 2
        if re.search(r'\b(SABÃO|SABAO|SABONETE|DETERGENTE|SHAMPOO|CONDICIONADOR|DESODORANTE|ALVEJANTE|ÁGUA SANITÁRIA|AGUA SANITARIA|DESINFETANTE|INSETICIDA|AMACIANTE|LIMPADOR|ESPONJA|ESCOVA DENTAL|PASTA DENTAL|CREME DENTAL|FRALDA|ABSORVENTE|PAPEL HIGIÊNICO|PAPEL HIGIENICO|PAPEL TOALHA|LENÇO|LENCO UMEDECIDO|HIDRATANTE|PERFUME|COLÔNIA|COLONIA|PROTETOR SOLAR|LÂMINA|LAMINA|APARELHO DE BARBEAR|BARBEAR)\b', nome_upper):
            return 4
        if re.search(r'\b(BANANA|MAÇÃ|MAÇA|LARANJA|UVA|MAMÃO|MAMAO|ABACAXI|MELANCIA|MELÃO|MELAO|ALFACE|TOMATE|CEBOLA|BATATA|CENOURA|CHUCHU|ABOBRINHA|VAGEM|BRÓCOLIS|BROCOLIS|COUVE|ESPINAFRE|ALHO|ABÓBORA|ABOBORA|BERINJELA|PIMENTÃO|PIMENTAO|REPOLHO|BETERRABA|MANDIOCA|AIPIM|INHAME|CARÁ|CARA)\b', nome_upper):
            return 6
        if re.search(r'\b(ÁGUA|AGUA|REFRIGERANTE|SUCO|CERVEJA|VINHO|ENERGÉTICO|ENERGETICO|ISOTÔNICO|ISOTONICO|CHÁ|CHA|BEBIDA|CAPSULA)\b', nome_upper):
            return 3
        if re.search(r'\b(PÃO|PAO|PÃO DE QUEIJO|PAO DE QUEIJO|BISNAGA|BAGUETE|BROA|CROISSANT|BOLO|TORRADA|SONHO)\b', nome_upper):
            return 5
        if re.search(r'\b(SORVETE|PIZZA|LASANHA|NUGGETS|BATATA FRITA|HAMBÚRGUER CONGELADO|HAMBURGUER CONGELADO)\b', nome_upper):
            return 8
        if re.search(r'\b(DOG|CAT|CAES|GATO|RACAO|RAÇÃO|PET|PETS|AREIA DE GATO|OSSINHO)\b', nome_upper):
            return 4

    cat = categoria.lower().strip()
    for key, value in CATEGORIA_IDS.items():
        if key in cat:
            return value
    return None


def upsert_produtos_batch(supabase, produtos_data: list[dict]) -> dict:
    """Upsert batch de produtos, retorna {nome: id}"""
    resultado = {}
    for i in range(0, len(produtos_data), 500):
        lote_raw = produtos_data[i:i + 500]
        # Dedup por nome dentro do lote (ON CONFLICT não aceita duplicatas no mesmo batch)
        vistos = set()
        lote = []
        for p in lote_raw:
            if p["nome"] not in vistos:
                vistos.add(p["nome"])
                lote.append(p)
        if not lote:
            continue
        try:
            resp = supabase.table("produtos").upsert(
                lote, on_conflict="nome"
            ).select("id,nome").execute()
            for item in resp.data:
                resultado[item["nome"]] = item["id"]
        except Exception as e:
            print(f"   ⚠️ Erro no batch upsert ({len(lote)} itens): {e}")
            for p in lote:
                try:
                    r = supabase.table("produtos").upsert(
                        p, on_conflict="nome"
                    ).select("id,nome").execute()
                    if r.data:
                        resultado[r.data[0]["nome"]] = r.data[0]["id"]
                except Exception:
                    pass
    return resultado


def sync_mercado(mercado_nome: str):
    mercado_display = MERCADO_DISPLAY.get(mercado_nome, mercado_nome)
    supermercado_id = MERCADO_IDS.get(mercado_nome)

    if not supermercado_id:
        print(f"❌ Mercado desconhecido: {mercado_nome}")
        return

    print(f"🔄 Sincronizando: {mercado_display} (ID: {supermercado_id})")

    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client["arca_bronze"]
    supabase = create_client(
        os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    # ═══════════════════════════════════════════════
    # FASE 1: Carrega produtos do MongoDB
    # ═══════════════════════════════════════════════
    produtos_mongo = list(db.produtos.find({
        "mercado": {"$regex": mercado_display, "$options": "i"}
    }))
    print(f"📦 {len(produtos_mongo)} produtos encontrados no MongoDB")

    # ═══════════════════════════════════════════════
    # FASE 2: Batch upsert de produtos no Supabase
    # ═══════════════════════════════════════════════
    print("⏳ Fazendo upsert dos produtos...")
    produtos_para_upsert = []
    for p in produtos_mongo:
        nome = p.get("nome_normalizado") or p.get("nome")
        if not nome:
            continue
        preco = p.get("preco_atual") or p.get("preco")
        if not preco:
            continue

        ean = p.get("ean", "")
        codigo_barras = (
            ean if isinstance(ean, str) and len(ean) in [8, 13] and ean.isdigit()
            else None
        )

        categoria_id = normalizar_categoria(p.get("categoria", ""), nome)

        produtos_para_upsert.append({
            "nome": nome,
            "marca": p.get("marca", "N/A"),
            "codigo_barras": codigo_barras,
            "imagem_url": p.get("url_imagem"),
            "categoria_id": categoria_id,
            "ativo": True,
        })

    mapa_nome_id = upsert_produtos_batch(supabase, produtos_para_upsert)
    print(f"   ✅ {len(mapa_nome_id)} produtos mapeados")

    # ═══════════════════════════════════════════════
    # FASE 3: Últimos preços do mercado no Supabase
    # ═══════════════════════════════════════════════
    print("⏳ Buscando últimos preços no Supabase...")
    precos_existentes = {}
    try:
        offset = 0
        TAM_PAGINA = 1000
        while True:
            resp = supabase.rpc("ultimos_precos_mercado", {
                "p_supermercado_id": supermercado_id
            }).range(offset, offset + TAM_PAGINA - 1).execute()

            if not resp.data:
                break

            for pr in resp.data:
                precos_existentes[pr["produto_id"]] = pr

            offset += TAM_PAGINA
            if len(resp.data) < TAM_PAGINA:
                break

        print(f"   ✅ {len(precos_existentes)} produtos com preço no Supabase")
    except Exception as e:
        print(f"   ⚠️ Erro ao buscar preços: {e}")
        precos_existentes = {}

    # ═══════════════════════════════════════════════
    # FASE 4: Filtra só produtos com preço alterado
    # ═══════════════════════════════════════════════
    precos_novos = []
    for p in produtos_mongo:
        nome = p.get("nome_normalizado") or p.get("nome")
        if not nome:
            continue

        produto_id = mapa_nome_id.get(nome)
        if not produto_id:
            continue

        preco = p.get("preco_atual") or p.get("preco")
        if not preco:
            continue

        ultimo = precos_existentes.get(produto_id)
        if ultimo and float(ultimo["preco"]) == float(preco):
            continue

        data_coleta = p.get("data_ultima_coleta") or p.get("data_extracao")
        if isinstance(data_coleta, datetime):
            data_coleta_str = data_coleta.isoformat()
        else:
            data_coleta_str = datetime.now().isoformat()

        precos_novos.append({
            "preco": float(preco),
            "data_coleta": data_coleta_str,
            "produto_id": produto_id,
            "supermercado_id": supermercado_id,
            "fonte_dados": "scraping",
            "promocao": False,
        })

    print(f"   🔍 {len(precos_novos)} preços alterados a inserir")

    # ═══════════════════════════════════════════════
    # FASE 5: Batch insert dos preços novos
    # ═══════════════════════════════════════════════
    inseridos = 0
    erros = 0

    try:
        for i in range(0, len(precos_novos), 500):
            lote = precos_novos[i:i + 500]
            try:
                supabase.table("precos").insert(lote).execute()
                inseridos += len(lote)
                print(f"   📤 Lote inserido — {inseridos}/{len(precos_novos)}")
            except Exception as e:
                print(f"   ⚠️ Erro no lote de {len(lote)} precos: {e}")
                erros += len(lote)
    finally:
        mongo_client.close()

    # ═══════════════════════════════════════════════
    # FASE 6: Equivalências incrementais
    # ═══════════════════════════════════════════════
    produtos_sem_equivalente = []
    for pid in set(mapa_nome_id.values()):
        try:
            resp = supabase.rpc("produto_tem_equivalentes", {"p_produto_id": pid}).execute()
            if resp.data and resp.data[0] == False:
                produtos_sem_equivalente.append(pid)
        except Exception:
            pass

    if produtos_sem_equivalente:
        print(f"🔗 Gerando equivalências para {len(produtos_sem_equivalente)} novos produtos...")
        for pid in produtos_sem_equivalente:
            try:
                supabase.rpc("backfill_produto", {"p_produto_id": pid}).execute()
            except Exception as e:
                print(f"   ⚠️ Erro backfill_produto({pid}): {e}")
        print(f"   ✅ Equivalências geradas")
    else:
        print(f"   ✅ Nenhum produto novo precisa de equivalência")

    ignorados = len(produtos_mongo) - inseridos - erros
    print(f"\n📊 Resultado {mercado_display}:")
    print(f"   ✅ Inseridos:  {inseridos}")
    print(f"   ⏭️  Ignorados:  {ignorados}")
    print(f"   ❌ Erros:      {erros}")
    print(f"   📦 Total:      {len(produtos_mongo)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mercado", required=True,
                        choices=list(MERCADO_IDS.keys()),
                        help="Mercado a sincronizar")
    args = parser.parse_args()
    sync_mercado(args.mercado)

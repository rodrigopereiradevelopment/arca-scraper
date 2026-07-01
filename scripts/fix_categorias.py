"""
Fix products with null categoria_id in Supabase.
Uses name-based rules (same logic as normalizar_categoria) to assign correct categoria_id.
"""
import os
import re
from supabase import create_client

# Same mapping as migrate_to_supabase.py
CATEGORIA_PARA_ID = {
    "laticinios": 1, "frios e laticinios": 1, "frios-laticinios": 1,
    "frios": 1, "frios e congelados": 1, "frios laticinios": 1,
    "acougue": 2, "acougue-47": 2, "carnes aves peixes": 2, "carnes": 2,
    "peixaria-82": 2, "peixaria": 2,
    "bebidas": 3, "bebidas alcoolicas": 3, "bebidas alcoólicas": 3,
    "bebidas-alcoolicas": 3, "agua": 3, "cerveja": 3, "sucos": 3,
    "higiene": 4, "higiene e beleza": 4, "higiene-beleza": 4,
    "limpeza": 4, "petshop": 4, "mundo pet": 4, "mamae e bebe": 4,
    "padaria": 5, "padaria-50": 5,
    "hortifruti": 6, "hortifrutigranjeiro-1": 6, "frutas e verduras": 6, "hortifrúti": 6,
    "cafe da manha": 7, "café da manhã": 7, "cafe-da-manha": 7,
    "cafe": 7, "café": 7, "graos": 7, "mercearia": 9,
    "congelados": 8, "congelados-6": 8,
    "bazar": 9, "magazine-16": 9, "utilidades": 9,
    "saudaveis organicos": 7,
    "biscoitos salgadinhos": 10, "doces sobremesas": 10,
    "biscoitos": 10, "doces": 10, "lanchonete": 9,
}

# Priority: name-based keyword matching (most specific first)
# Returns (categoria_id, matched_key) or None
# Additional patterns for products that didn't match
NAME_RULES_EXTRA = [
    # Macarrão (MAC = macarrão abreviado)
    (r'\bMAC\.', 7),
    (r'\bMAC INST', 7),
    # Chicken = frango
    (r'\bCHICKEN\b', 2),
    # Bebida/Beverage
    (r'\bBEBIDA\b', 3),
    # DOG/CAT/PET = petshop
    (r'\bDOG\b', 4),
    (r'\bCAT\b', 4),
    # Geleia/Mocoto = doces
    (r'\bGELEIA\b', 10),
    (r'\bMOCOTO\b', 10),
    # Cápsula = bebidas
    (r'\bCAPSULA\b', 3),
    # PROVOLONE = frios (queijo)
    (r'\bPROVOLONE\b', 1),
    # Massas (talharim, rondelli, capeletti)
    (r'\bMASSA\b', 7),
    (r'\b(TALHARIM|RONDELLI|CAPELETTI|RAVIOLI|CANELONE|LASANHA)\b', 7),
    # Oleo lubrificante = bazar/default
    (r'\bÓLEO LUB\b', 9),
    # Cremes e loções = higiene/beleza
    (r'\b(LOÇÃO|LOCAO|CREME HIDRATANTE|HIDRATANTE CORPORAL)\b', 4),
    # Xampu / condicionador com caracteres corrompidos
    (r'\bCONDICIONA', 4),
    (r'\bSHAMPOO\b', 4),
]

NAME_RULES = [
    # Category 7 - Grãos, Cereais, Mercearia
    (r'\b(?:ARROZ|FEIJÃO|FEIJAO)\b', 7),
    (r'\b(?:FARINHA|FARELO|FUBÁ|FUBA)\b', 7),
    (r'\b(?:AÇÚCAR|ACUCAR|ADOCANTE)\b', 7),
    (r'\b(?:CAFÉ|CAFE)\b', 7, lambda n: 'LEITE' not in n.upper() and 'CREME' not in n.upper()),
    (r'\b(?:MACARRÃO|MACARRAO|ESPAGUETE|LAMEN|MIOJO)\b', 7),
    (r'\b(?:LENTILHA|ERVILHA|GRÃO DE BICO|GRAO DE BICO|SOJA)\b', 7),
    (r'\b(?:ÓLEO|AZEITE|VINAGRE|MOLHO|MAIONESE|KETCHUP|MOSTARDA|TEMPERO|CALDO)\b', 7),
    (r'\b(?:SAL|ORÉGANO|OREGANO|CANELA|CURRY|COM|PÁPRICA|PAPRICA|CEBOLA EMPANADA)\b', 7),
    (r'\b(?:SOPA|CREME DE CEbola|CREME DE CEBOLA)\b', 7),
    (r'\b(?:LEITE EM PÓ|LEITE EM PO|LEITE CONDENSADO)\b', 7),
    # Category 1 - Laticínios / Frios
    (r'\b(?:LEITE|QUEIJO|MANTEIGA|MARGARINA|IOGURTE|REQUEIJÃO|REQUEIJAO)\b', 1),
    (r'\b(?:CREME DE LEITE|CREME DELEITE|MUÇARELA|MUCARELA|PRATO|MINAS|CHEDDAR|RICOTA|COTAGE)\b', 1),
    (r'\b(?:IOGURTE|YOGURTE|COALHADA|NATA)\b', 1),
    # Category 2 - Carnes / Peixes / Açougue
    (r'\b(?:CARNE|FRANGO|PEIXE|BOVINO|SUÍNO|SUINO|FILE|FILÉ|PICANHA|ALCATRA|COXÃO|COXAO)\b', 2),
    (r'\b(?:PATINHO|MAMINHA|ACÉM|ACEM|PALETA|LINGUIÇA|LINGUICA|SALSICHA|HAMBURGUER)\b', 2),
    (r'\b(?:BISTECA|COSTELA|CORDEIRO|BACON|PERNIL|LOMBO|PEITO DE FRANGO|ASA)\b', 2),
    # Category 3 - Bebidas (except milk-based)
    (r'\b(?:ÁGUA|AGUA|REFRIGERANTE|SUCO|CERVEJA|VINHO|ENERGÉTICO|ENERGETICO|ISOTÔNICO|ISOTONICO|CHÁ|CHA)\b', 3),
    # Category 4 - Higiene e Limpeza
    (r'\b(?:SABÃO|SABAO|SABONETE|DETERGENTE|DESODORANTE|SHAMPOO|CONDICIONADOR)\b', 4),
    (r'\b(?:ESCOVA DENTAL|PASTA DENTAL|CREME DENTAL|FRALDA|ABSORVENTE)\b', 4),
    (r'\b(?:PAPEL HIGIÊNICO|PAPEL HIGIENICO|PAPEL TOALHA|LENÇO|LENCO UMEDECIDO)\b', 4),
    (r'\b(?:ALVEJANTE|ÁGUA SANITÁRIA|AGUA SANITARIA|DESINFETANTE|INSETICIDA|AMACIANTE|LIMPADOR|DESINFETANTE|ESPONJA)\b', 4),
    (r'\b(?:SABÃO EM PÓ|SABAO EM PO|DETERGENTE EM PÓ|DETERGENTE EM PO|LAVA ROUPAS)\b', 4),
    (r'\b(?:HIGIENE|BELEZA|COSMÉTICO|COSMETICO|PERFUME|COLÔNIA|COLONIA|PROTETOR SOLAR)\b', 4),
    (r'\b(?:LÂMINA|LAMINA|APARELHO DE BARBEAR|BARBEAR|CREME DE BARBEAR)\b', 4),
    # Category 5 - Padaria
    (r'\b(?:PÃO|PAO|PÃO DE QUEIJO|PAO DE QUEIJO|BISNAGA|BAGUETE|BROA|CROISSANT|BOLO|TORRADA|SONHO)\b', 5),
    # Category 6 - Hortifrúti
    (r'\b(?:BANANA|MAÇÃ|MA�A|LARANJA|UVA|MAMÃO|MAMAO|ABACAXI|MELANCIA|MELÃO|MELAO)\b', 6),
    (r'\b(?:ALFACE|TOMATE|CEBOLA|BATATA|CENOURA|CHUCHU|ABOBRINHA|VAGEM|BRÓCOLIS|BROCOLIS|COUVE|ESPINAFRE|ALHO)\b', 6),
    (r'\b(?:ABÓBORA|ABOBORA|BERINJELA|PIMENTÃO|PIMENTAO|REPOLHO|BETERRABA|MANDIOCA|AIPIM|INHAME|CARÁ|CARA)\b', 6),
    # Category 8 - Congelados
    (r'\b(?:SORVETE|PIZZA|LASANHA|NUGGETS|BATATA FRITA|HAMBÚRGUER CONGELADO|HAMBURGUER CONGELADO)\b', 8),
    # Category 10 - Biscoitos / Doces / Salgadinhos
    (r'\b(?:BISCOITO|BOLACHA|SALGADINHO|CHIPS|SNACKS|TORRESMO|AMENDOIM)\b', 10),
    (r'\b(?:CHOCOLATE|BALAS|PIRULITO|CHICLETE|GOMA|DOCE|BOMBOM|WAFFER|WAFER|MARMITA)\b', 10),
    # Category 4 (pet) - remaining petshop
    (r'\b(?:PET|RAÇÃO|RACAO|GATO|CACHORRO|AREIA DE GATO|OSSINHO)\b', 4),
]


# Combine all rules
ALL_NAME_RULES = NAME_RULES + NAME_RULES_EXTRA

def normalizar_categoria_por_nome(nome: str) -> int | None:
    """Determine categoria_id from product name using keyword rules."""
    if not nome:
        return None
    nome_u = nome.upper()

    for rule in ALL_NAME_RULES:
        pattern = rule[0]
        cat_id = rule[1]
        condition = rule[2] if len(rule) > 2 else None
        if re.search(pattern, nome_u):
            if condition is None or condition(nome):
                return cat_id
    return None


def main():
    supabase = create_client(
        os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )

    # Load all products with null categoria_id
    all_null = []
    page = 0
    while True:
        resp = supabase.table('produtos') \
            .select('id,nome') \
            .is_('categoria_id', 'null') \
            .limit(1000) \
            .offset(page * 1000) \
            .execute()
        if not resp.data:
            break
        all_null.extend(resp.data)
        page += 1
        print(f'Loaded page {page} ({len(all_null)} so far)')

    print(f'\nTotal products with null categoria_id: {len(all_null)}')

    # Group by computed categoria_id for batch updates
    updates_by_cat: dict[int, list[int]] = {}
    unmatched: list[dict] = []

    for prod in all_null:
        cat_id = normalizar_categoria_por_nome(prod['nome'])
        if cat_id is not None:
            updates_by_cat.setdefault(cat_id, []).append(prod['id'])
        else:
            unmatched.append(prod)

    print(f'\nProducts matched to a category: {len(all_null) - len(unmatched)}')
    print(f'Products still unmatched: {len(unmatched)}')
    for cat_id, ids in sorted(updates_by_cat.items()):
        print(f'  Category {cat_id}: {len(ids)} products')

    # Show some unmatched examples
    if unmatched:
        print('\nUnmatched examples (first 10):')
        for p in unmatched[:10]:
            print(f'  - {p["id"]}: {p["nome"][:80]}')

    # Perform batch updates
    total_updated = 0
    for cat_id, ids in updates_by_cat.items():
        # Update in chunks of 1000
        for i in range(0, len(ids), 1000):
            chunk = ids[i:i+1000]
            resp = supabase.table('produtos') \
                .update({'categoria_id': cat_id}) \
                .in_('id', chunk) \
                .execute()
            total_updated += len(chunk)
            print(f'  Updated {total_updated}/{len(all_null)}...')

    # Assign unmatched to category 9 (Bazar/Utilidades/Mercearia geral)
    if unmatched:
        un_ids = [p['id'] for p in unmatched]
        for i in range(0, len(un_ids), 200):
            chunk = un_ids[i:i+200]
            try:
                supabase.table('produtos') \
                    .update({'categoria_id': 9}) \
                    .in_('id', chunk) \
                    .execute()
                total_updated += len(chunk)
            except Exception as e:
                print(f'  Error updating chunk {i}-{i+len(chunk)}: {e}')
                # Try one by one for remaining
                for pid in chunk:
                    try:
                        supabase.table('produtos') \
                            .update({'categoria_id': 9}) \
                            .eq('id', pid) \
                            .execute()
                        total_updated += 1
                    except Exception as e2:
                        print(f'  Error updating product {pid}: {e2}')
        print(f'  Assigned {len(un_ids)} unmatched to category 9 (default)')

    print(f'\nDone! Total updated: {total_updated}')


if __name__ == '__main__':
    main()

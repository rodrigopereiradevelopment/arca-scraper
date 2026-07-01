"""
Fix ALL products — reavalia categoria_id pelo nome.
Corrige produtos que foram classificados errado por bugs anteriores.
"""
import os
import re
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

supabase_url = os.environ['NEXT_PUBLIC_SUPABASE_URL']
service_key = os.environ['SUPABASE_SERVICE_ROLE_KEY']

headers = {
    'apikey': service_key,
    'Authorization': f'Bearer {service_key}',
    'Content-Type': 'application/json',
}

CATEGORY_NAMES = {
    1: 'Laticínios', 2: 'Carnes e Peixes', 3: 'Bebidas',
    4: 'Higiene e Limpeza', 5: 'Padaria e Confeitaria', 6: 'Frutas e Verduras',
    7: 'Grãos e Cereais', 8: 'Congelados', 9: 'Mercearia', 10: 'Petiscos e Snacks',
}

ALL_NAME_RULES = [
    # Category 10 - Biscoitos/Doces/Salgadinhos (must come first)
    (r'\b(BISCOITO|BOLACHA|SALGADINHO|CHIPS|SNACKS|TORRESMO|AMENDOIM)\b', 10),
    (r'\b(CHOCOLATE|BALAS|PIRULITO|CHICLETE|BOMBOM|WAFER|WAFFER|MARMITA)\b', 10),
    (r'\b(GELEIA|GOIABADA|MARSHMALLOW|CONFEITO|GRANULADO)\b', 10),
    (r'\bGOMA\b', 10),
    # Category 7 - Grãos, Cereais
    (r'\b(ARROZ|FEIJÃO|FEIJAO)\b', 7),
    (r'\b(FARINHA|FARELO|FUBÁ|FUBA)\b', 7),
    (r'\b(AÇÚCAR|ACUCAR|ADOCANTE)\b', 7),
    (r'\b(CAFÉ|CAFE)\b', 7, lambda n: 'LEITE' not in n.upper() and 'CREME' not in n.upper()),
    (r'\b(MACARRÃO|MACARRAO|ESPAGUETE|LAMEN|MIOJO)\b', 7),
    (r'\b(LENTILHA|ERVILHA|GRÃO DE BICO|GRAO DE BICO|SOJA)\b', 7),
    (r'\b(ÓLEO|AZEITE|VINAGRE|MOLHO|MAIONESE|KETCHUP|MOSTARDA|TEMPERO|CALDO)\b', 7),
    (r'\b(SAL|ORÉGANO|OREGANO|CANELA|CURRY|PÁPRICA|PAPRICA|CEBOLA EMPANADA)\b', 7),
    (r'\b(SOPA|CREME DE CEBOLA)\b', 7),
    (r'\b(LEITE EM PÓ|LEITE EM PO|LEITE CONDENSADO)\b', 7),
    # Category 1 - Laticínios / Frios
    (r'\b(LEITE\s|QUEIJO|MANTEIGA|MARGARINA|IOGURTE|REQUEIJÃO|REQUEIJAO)\b', 1),
    (r'\b(CREME DE LEITE|CREME DELEITE|MUÇARELA|MUCARELA|PRATO|MINAS|CHEDDAR|RICOTA|COTAGE)\b', 1),
    (r'\b(IOGURTE|YOGURTE|COALHADA|NATA)\b', 1),
    (r'\bPROVOLONE\b', 1),
    # Category 2 - Carnes / Açougue
    (r'\b(CARNE|FRANGO|PEIXE|BOVINO|SUÍNO|SUINO|FILE|FILÉ|PICANHA|ALCATRA|COXÃO|COXAO)\b', 2),
    (r'\b(PATINHO|MAMINHA|ACÉM|ACEM|PALETA|LINGUIÇA|LINGUICA|SALSICHA|HAMBURGUER)\b', 2),
    (r'\b(BISTECA|COSTELA|CORDEIRO|BACON|PERNIL|LOMBO|PEITO DE FRANGO|ASA)\b', 2),
    (r'\bCHICKEN\b', 2),
    # Category 3 - Bebidas
    (r'\b(ÁGUA|AGUA|REFRIGERANTE|SUCO|CERVEJA|VINHO|ENERGÉTICO|ENERGETICO|ISOTÔNICO|ISOTONICO|CHÁ|CHA)\b', 3),
    (r'\bBEBIDA\b', 3),
    (r'\bCAPSULA\b', 3),
    # Category 4 - Higiene e Limpeza
    (r'\b(SABÃO|SABAO|SABONETE|DETERGENTE|DESODORANTE|SHAMPOO|CONDICIONADOR)\b', 4),
    (r'\b(ESCOVA DENTAL|PASTA DENTAL|CREME DENTAL|FRALDA|ABSORVENTE)\b', 4),
    (r'\b(PAPEL HIGIÊNICO|PAPEL HIGIENICO|PAPEL TOALHA|LENÇO|LENCO UMEDECIDO)\b', 4),
    (r'\b(ALVEJANTE|ÁGUA SANITÁRIA|AGUA SANITARIA|DESINFETANTE|INSETICIDA|AMACIANTE|LIMPADOR|DESINFETANTE|ESPONJA)\b', 4),
    (r'\b(SABÃO EM PÓ|SABAO EM PO|DETERGENTE EM PÓ|DETERGENTE EM PO|LAVA ROUPAS)\b', 4),
    (r'\b(HIGIENE|BELEZA|COSMÉTICO|COSMETICO|PERFUME|COLÔNIA|COLONIA|PROTETOR SOLAR)\b', 4),
    (r'\b(LÂMINA|LAMINA|APARELHO DE BARBEAR|BARBEAR|CREME DE BARBEAR)\b', 4),
    (r'\b(LOÇÃO|LOCAO|CREME HIDRATANTE|HIDRATANTE CORPORAL)\b', 4),
    (r'\bCONDICIONA', 4),
    (r'\bSHAMPOO\b', 4),
    # Category 5 - Padaria
    (r'\b(PÃO|PAO|PÃO DE QUEIJO|PAO DE QUEIJO|BISNAGA|BAGUETE|BROA|CROISSANT|BOLO|TORRADA|SONHO)\b', 5),
    # Category 6 - Hortifrúti
    (r'\b(BANANA|MAÇÃ|MAÇA|LARANJA|UVA|MAMÃO|MAMAO|ABACAXI|MELANCIA|MELÃO|MELAO)\b', 6),
    (r'\b(ALFACE|TOMATE|CEBOLA|BATATA|CENOURA|CHUCHU|ABOBRINHA|VAGEM|BRÓCOLIS|BROCOLIS|COUVE|ESPINAFRE|ALHO)\b', 6),
    (r'\b(ABÓBORA|ABOBORA|BERINJELA|PIMENTÃO|PIMENTAO|REPOLHO|BETERRABA|MANDIOCA|AIPIM|INHAME|CARÁ|CARA)\b', 6),
    # Category 8 - Congelados
    (r'\b(SORVETE|PIZZA|LASANHA|NUGGETS|BATATA FRITA)\b', 8),
    # Category 4 (pet) - remaining petshop
    (r'\b(PET|RAÇÃO|RACAO|GATO|CACHORRO|AREIA DE GATO|OSSINHO)\b', 4),
    (r'\b(DOG|CAT)\b', 4),
]


def normalizar(nome: str) -> int | None:
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
    print('=== Fix ALL categorias ===\n')

    # 1. Load all products (cursor-based pagination)
    all_prods = []
    last_id = 0
    while True:
        r = requests.get(
            f'{supabase_url}/rest/v1/produtos',
            params={
                'select': 'id,nome,categoria_id',
                'limit': 1000,
                'order': 'id.asc',
                'id': f'gt.{last_id}',
            },
            headers=headers,
        )
        data = r.json()
        if not isinstance(data, list) or not data:
            break
        all_prods.extend(data)
        last_id = data[-1]['id']
        print(f'  Loaded {len(all_prods)} products...', end='\r')

    print(f'\n\nTotal products loaded: {len(all_prods)}')

    # 2. Classify each product
    updates: dict[int, list[int]] = {}
    stats_current = {k: 0 for k in range(1, 11)}
    stats_fixed = {k: 0 for k in range(1, 11)}
    changes = {k: {d: 0 for d in range(1, 11)} for k in range(1, 11)}
    unchanged = 0
    no_match = []

    for prod in all_prods:
        cur = prod.get('categoria_id')
        stats_current[cur] = stats_current.get(cur, 0) + 1

        computed = normalizar(prod['nome'])

        if computed is None:
            no_match.append(prod)
            continue

        if cur == computed:
            unchanged += 1
            continue

        updates.setdefault(computed, []).append(prod['id'])
        stats_fixed[computed] = stats_fixed.get(computed, 0) + 1
        changes.setdefault(cur, {}).setdefault(computed, 0)
        changes[cur][computed] = changes[cur][computed] + 1

    # 3. Report
    print(f'\nUnchanged: {unchanged}')
    print(f'To fix: {sum(stats_fixed.values())}')
    print(f'No name match (will keep current): {len(no_match)}')
    if no_match:
        for p in no_match[:5]:
            nome = p['nome'][:60]
            print(f'  - [{p["categoria_id"]}] {nome}')

    print(f'\n=== Proposed changes ===')
    for cur_cat in sorted(changes):
        for new_cat in sorted(changes[cur_cat]):
            qty = changes[cur_cat][new_cat]
            if qty > 0:
                cur_nome = CATEGORY_NAMES.get(cur_cat, f'ID {cur_cat}') if cur_cat else 'NULL'
                new_nome = CATEGORY_NAMES.get(new_cat, f'ID {new_cat}')
                print(f'  {cur_nome} ({cur_cat}) → {new_nome} ({new_cat}): {qty} produtos')

    # 4. Ask before applying
    total_to_fix = sum(stats_fixed.values())
    if total_to_fix == 0:
        print('\nNada para corrigir!')
        return

    print(f'\nTotal a corrigir: {total_to_fix} produtos')

    # 5. Apply updates
    applied = 0
    for cat_id, ids in sorted(updates.items()):
        if not ids:
            continue
        cat_nome = CATEGORY_NAMES.get(cat_id, f'ID {cat_id}')
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            resp = requests.patch(
                f'{supabase_url}/rest/v1/produtos',
                params={'id': f'in.({",".join(str(x) for x in chunk)})'},
                json={'categoria_id': cat_id},
                headers={**headers, 'Prefer': 'return=minimal'},
            )
            if resp.status_code != 204:
                print(f'  Error updating cat {cat_id} chunk: {resp.status_code}')
                # Try one by one
                for pid in chunk:
                    r2 = requests.patch(
                        f'{supabase_url}/rest/v1/produtos',
                        params={'id': f'eq.{pid}'},
                        json={'categoria_id': cat_id},
                        headers={**headers, 'Prefer': 'return=minimal'},
                    )
                    if r2.status_code == 204:
                        applied += 1
            else:
                applied += len(chunk)
            if (i // 200) % 5 == 0:
                print(f'  {cat_nome}: {applied}/{total_to_fix}...')
        print(f'  {cat_nome}: {len(ids)} done')

    # 6. Verify
    r = requests.get(
        f'{supabase_url}/rest/v1/produtos',
        params={'select': 'categoria_id', 'limit': 200},
        headers=headers,
    )
    remaining = r.json()
    dist = Counter(x.get('categoria_id') for x in remaining)
    print(f'\n=== Distribution (sample of {len(remaining)}) ===')
    for k in sorted(dist.keys()):
        nome = CATEGORY_NAMES.get(k, f'ID {k}') if k else 'NULL'
        print(f'  {nome} ({k}): {dist[k]}')

    print(f'\nDone! Total updated: {applied}')


if __name__ == '__main__':
    main()

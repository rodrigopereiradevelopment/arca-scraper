"""
Fix remaining null categoria_id using direct REST API calls.
"""
import os, re, requests, time

supabase_url = os.environ.get('SUPABASE_URL') or os.environ['NEXT_PUBLIC_SUPABASE_URL']
service_key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ['SUPABASE_SERVICE_ROLE_KEY']

headers = {
    'apikey': service_key,
    'Authorization': f'Bearer {service_key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# All name matching rules (same as before)
import re as re_module

ALL_NAME_RULES = [
    # Category 7 - Grãos, Cereais, Mercearia
    (r'\b(?:ARROZ|FEIJÃO|FEIJAO)\b', 7),
    (r'\b(?:FARINHA|FARELO|FUBÁ|FUBA)\b', 7),
    (r'\b(?:AÇÚCAR|ACUCAR|ADOCANTE)\b', 7),
    (r'\b(?:CAFÉ|CAFE)\s', 7),
    (r'\bMAC\.', 7),
    (r'\bMAC INST', 7),
    (r'\bMACARRAO\b', 7),
    (r'\bMACARRÃO\b', 7),
    (r'\b(?:ESPAGUETE|LAMEN|MIOJO)\b', 7),
    (r'\b(?:LENTILHA|ERVILHA|GRÃO DE BICO|GRAO DE BICO|SOJA)\b', 7),
    (r'\b(?:ÓLEO|AZEITE|VINAGRE|MOLHO|MAIONESE|KETCHUP|MOSTARDA|TEMPERO|CALDO)\b', 7),
    (r'\b(?:SAL|ORÉGANO|OREGANO|CANELA|CURRY|PÁPRICA|PAPRICA|CEBOLA EMPANADA)\b', 7),
    (r'\b(?:SOPA|CREME DE CEBOLA)\b', 7),
    (r'\b(?:LEITE EM PÓ|LEITE EM PO|LEITE CONDENSADO)\b', 7),
    (r'\b(?:SALGADINHO|CHIPS|SNACKS|TORRESMO|AMENDOIM)\b', 10),
    # Category 1 - Laticínios
    (r'\b(?:LEITE\s|QUEIJO|MANTEIGA|MARGARINA|IOGURTE|REQUEIJÃO|REQUEIJAO)\b', 1),
    (r'\b(?:CREME DE LEITE|MUÇARELA|MUCARELA|PRATO|MINAS|CHEDDAR|RICOTA)\b', 1),
    # Category 2 - Carnes
    (r'\b(?:CARNE|FRANGO|PEIXE|BOVINO|SUÍNO|SUINO|PICANHA|ALCATRA|LINGUIÇA|LINGUICA|SALSICHA|HAMBURGUER)\b', 2),
    (r'\b(?:BACON|PERNIL|LOMBO|PEITO DE FRANGO|COSTELA|CORDEIRO)\b', 2),
    (r'\bCHICKEN\b', 2),
    # Category 3 - Bebidas
    (r'\b(?:ÁGUA|AGUA|REFRIGERANTE|SUCO|CERVEJA|VINHO|ENERGÉTICO|ENERGETICO|ISOTÔNICO|ISOTONICO|CHÁ|CHA)\b', 3),
    (r'\bBEBIDA\b', 3),
    (r'\bCAPSULA\b', 3),
    # Category 4 - Higiene e Limpeza (including pet)
    (r'\b(?:SABÃO|SABAO|SABONETE|DETERGENTE|DESODORANTE|SHAMPOO|CONDICIONADOR)\b', 4),
    (r'\b(?:ESCOVA DENTAL|PASTA DENTAL|CREME DENTAL|FRALDA|ABSORVENTE)\b', 4),
    (r'\b(?:PAPEL HIGIÊNICO|PAPEL HIGIENICO|PAPEL TOALHA|LENÇO|LENCO)\b', 4),
    (r'\b(?:ALVEJANTE|ÁGUA SANITÁRIA|AGUA SANITARIA|DESINFETANTE|INSETICIDA|AMACIANTE|LIMPADOR|ESPONJA)\b', 4),
    (r'\b(?:SABÃO EM PÓ|SABAO EM PO|LAVA ROUPAS)\b', 4),
    (r'\b(?:HIDRATANTE|PERFUME|COLÔNIA|COLONIA|PROTETOR SOLAR)\b', 4),
    (r'\b(?:LÂMINA|LAMINA|APARELHO DE BARBEAR|BARBEAR)\b', 4),
    (r'\b(?:DOG|CAT|CAES|GATO|RACAO|PET|PETS)\b', 4),
    # Category 5 - Padaria
    (r'\b(?:PÃO|PAO|PÃO DE QUEIJO|PAO DE QUEIJO|BISNAGA|BAGUETE|BROA|CROISSANT|BOLO|TORRADA)\b', 5),
    # Category 6 - Hortifrúti
    (r'\b(?:BANANA|MAÇÃ|MA�A|LARANJA|UVA|MAMÃO|MAMAO|ABACAXI|MELANCIA|MELÃO|MELAO)\b', 6),
    (r'\b(?:ALFACE|TOMATE|CEBOLA|BATATA|CENOURA|CHUCHU|ABOBRINHA|VAGEM|BRÓCOLIS|BROCOLIS|COUVE|ESPINAFRE|ALHO)\b', 6),
    # Category 8 - Congelados
    (r'\b(?:SORVETE|PIZZA|LASANHA|NUGGETS|BATATA FRITA)\b', 8),
    # Category 10 - Biscoitos / Doces
    (r'\b(?:BISCOITO|BOLACHA|SALGADINHO|CHOCOLATE|BALAS|PIRULITO|CHICLETE|GOMA|DOCE|BOMBOM|WAFER|WAFFER)\b', 10),
    (r'\b(?:GELEIA|GOIABADA|MARSHMALLOW|CONFEITO|GRANULADO)\b', 10),
]

def normalizar_por_nome(nome):
    if not nome:
        return None
    nome_u = nome.upper()
    for pattern, cat_id in ALL_NAME_RULES:
        if re_module.search(pattern, nome_u):
            return cat_id
    return None


def main():
    # Get all null products
    all_null = []
    page = 0
    last_id = 0
    while True:
        r = requests.get(
            f'{supabase_url}/rest/v1/produtos',
            params={
                'categoria_id': 'is.null',
                'select': 'id,nome',
                'limit': 1000,
                'id': f'gt.{last_id}',
                'order': 'id.asc'
            },
            headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'}
        )
        data = r.json()
        if not isinstance(data, list) or not data:
            break
        all_null.extend(data)
        last_id = data[-1]['id']
        page += 1
        print(f'  Page {page}: {len(data)} products (last_id={last_id})')

    print(f'\nTotal with null categoria_id: {len(all_null)}')

    # Categorize
    matched = {7: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 8: [], 10: [], 9: []}
    for prod in all_null:
        cat = normalizar_por_nome(prod['nome'])
        if cat is not None:
            matched[cat].append(prod['id'])
        else:
            matched[9].append(prod['id'])

    for cat, ids in sorted(matched.items()):
        if ids:
            print(f'  Category {cat}: {len(ids)} products')

    # Update using REST API PATCH (direct)
    total = 0
    for cat_id, ids in sorted(matched.items()):
        if not ids:
            continue
        for i in range(0, len(ids), 200):
            chunk = ids[i:i+200]
            resp = requests.patch(
                f'{supabase_url}/rest/v1/produtos',
                params={'id': f'in.({",".join(str(x) for x in chunk)})'},
                json={'categoria_id': cat_id},
                headers=headers
            )
            if resp.status_code == 204:
                pass  # success
            else:
                print(f'  Error updating cat {cat_id} chunk: {resp.status_code} {resp.text}')
            total += len(chunk)
        print(f'  Updated cat {cat_id}: {len(ids)} products')

    print(f'\nDone! Total updated: {total}')

    # Verify
    r = requests.get(
        f'{supabase_url}/rest/v1/produtos',
        params={'categoria_id': 'is.null', 'select': 'id', 'limit': 5},
        headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'}
    )
    print(f'Remaining null after fix: {len(r.json())}')


if __name__ == '__main__':
    main()

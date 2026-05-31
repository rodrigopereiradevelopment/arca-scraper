from fastembed import TextEmbedding
from supabase import create_client
import os, re, time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ✨ Modelo leve, sem PyTorch, funciona em qualquer CPU
model = TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def normalizar(nome: str) -> str:
    nome = nome.upper()
    nome = re.sub(r'(\d+)\s*KG', r'\1KG', nome)
    nome = re.sub(r'(\d+)\s*G\b', r'\1G', nome)
    nome = re.sub(r'(\d+)\s*ML', r'\1ML', nome)
    nome = re.sub(r'(\d+)\s*L\b', r'\1L', nome)
    nome = re.sub(r'(\d+)\s*LITROS?', r'\1L', nome)
    for r in ['PACOTE', 'EMBALAGEM', 'UNIDADE', 'CX', 'CAIXA', 'OFERTA']:
        nome = nome.replace(r, '')
    return re.sub(r'\s+', ' ', nome).strip()

def processar_em_lotes():
    print("🚀 Iniciando geração de embeddings...")
    
    tamanho_lote = 200
    total_processados = 0

    while True:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

            response = supabase.table("produtos") \
                .select("id, nome") \
                .is_("embedding", "null") \
                .limit(tamanho_lote) \
                .execute()
            
            produtos = response.data
            if not produtos:
                print(f"\n✅ Concluído! Total: {total_processados} produtos")
                break

            nomes = [normalizar(p['nome']) for p in produtos]
            
            # ✨ fastembed retorna generator, converte pra lista
            embeddings = list(model.embed(nomes))

            ids = [p['id'] for p in produtos]
            embeddings_list = [str(e.tolist()) for e in embeddings]

            supabase.rpc('atualizar_embeddings', {
                'p_ids': ids,
                'p_embeddings': embeddings_list
            }).execute()

            total_processados += len(produtos)
            print(f"  ✅ {total_processados} produtos processados...")
            time.sleep(0.5)

        except Exception as e:
            print(f"  ⚠️ Erro, tentando de novo em 5s... ({e})")
            time.sleep(5)
            continue

if __name__ == "__main__":
    processar_em_lotes()
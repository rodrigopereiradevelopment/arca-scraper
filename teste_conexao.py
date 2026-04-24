import requests
try:
    res = requests.get("https://api.mobilesim.com.br/user/v1.02/tabs", timeout=10)
    print(f"Conexao API: {res.status_code}")
    if res.status_code == 200:
        print("Sucesso! A internet da escola permite o acesso.")
except Exception as e:
    print(f"Erro ao conectar: {e}")

import os
"""
GCB Discador Preditivo — Demo
Liga para uma lista de contatos e conecta na Clara automaticamente.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")

# Número que aparece pra quem recebe a ligação
FROM_NUMBER = "+551151189954"

# TeXML App ID da Clara
CLARA_TEXML_APP_ID = "2924083901620028790"

# AI Assistant ID da Clara
CLARA_ASSISTANT_ID = "assistant-402286c0-bb62-4af9-ae5b-ad5be9faa21b"

# Lista de contatos pra ligar
CONTATOS = [
    {"nome": "Pedro Jesus",    "numero": "+5511991986241"},
    {"nome": "Marcos",         "numero": "+5511999999991"},  # trocar pelo número real
    {"nome": "Alexsander",     "numero": "+5511999999992"},  # trocar pelo número real
]

# Intervalo entre ligações (segundos)
INTERVALO = 5

# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------

def telnyx_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://api.telnyx.com/v2{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return None, str(e)


def ligar(contato):
    nome = contato["nome"]
    numero = contato["numero"]
    print(f"\n📞 Ligando para {nome} ({numero})...")

    resp, err = telnyx_post(f"/texml/ai_calls/{CLARA_TEXML_APP_ID}", {
        "From": FROM_NUMBER,
        "To": numero,
        "AIAssistantId": CLARA_ASSISTANT_ID,
        "MachineDetection": "Enable",
        "AsyncAmd": True,
        "DetectionMode": "Premium",
    })

    if err:
        print(f"   ❌ Erro: {err}")
        return {"nome": nome, "numero": numero, "status": "erro", "detalhe": err}

    call_id = resp.get("call_sid", "—") if resp else "—"
    print(f"   ✅ Chamada iniciada | status: {resp.get('status','—')} | call_sid: {call_id}")
    return {"nome": nome, "numero": numero, "status": "discando", "call_id": call_id}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  GCB Investimentos — Discador Demo")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)
    print(f"\n📋 {len(CONTATOS)} contatos na fila:\n")
    for c in CONTATOS:
        print(f"   • {c['nome']} — {c['numero']}")

    print(f"\n🚀 Iniciando em 3 segundos...")
    time.sleep(3)

    resultados = []
    for i, contato in enumerate(CONTATOS):
        resultado = ligar(contato)
        resultados.append(resultado)

        if i < len(CONTATOS) - 1:
            print(f"   ⏳ Aguardando {INTERVALO}s antes da próxima...")
            time.sleep(INTERVALO)

    print("\n" + "=" * 50)
    print("  RESULTADO FINAL")
    print("=" * 50)
    for r in resultados:
        icone = "✅" if r["status"] == "discando" else "❌"
        print(f"  {icone} {r['nome']}: {r['status']}")

    print(f"\n✔ Campanha concluída — {sum(1 for r in resultados if r['status']=='discando')}/{len(resultados)} chamadas iniciadas")

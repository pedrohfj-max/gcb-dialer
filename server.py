"""
MCP Server — GCB Investimentos Demo
Expõe 3 tools para o agente de voz Clara usar durante chamadas:
  - buscar_investidor(cpf)
  - buscar_produtos_recomendados(perfil, valor)
  - registrar_interesse(cpf, produto, horario_contato)
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config SMS (Telnyx)
# ---------------------------------------------------------------------------

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
TELNYX_MESSAGING_PROFILE = os.environ.get("TELNYX_MESSAGING_PROFILE", "40019d29-dc9e-44d7-b761-f1c2172ab44f")
SMS_FROM = "GCBInvest"

# Mapa CPF → número celular (para demo)
TELEFONES = {
    "123.456.789-00": "+5511991986241",  # Carlos Eduardo → Pedro (demo)
    "987.654.321-00": "+5511991986241",
    "456.789.123-00": "+5511991986241",
    "321.654.987-00": "+5511991986241",
    "654.321.098-00": "+5511991986241",
}


def enviar_sms(telefone: str, nome: str, produto: str) -> bool:
    """Envia SMS de confirmação via Telnyx."""
    mensagem = (
        f"Ola, {nome.split()[0]}! "
        f"Confirmamos seu interesse no produto {produto} da GCB Investimentos. "
        f"Um especialista entrara em contato em breve. Obrigada!"
    )
    payload = json.dumps({
        "from": SMS_FROM,
        "to": telefone,
        "messaging_profile_id": TELNYX_MESSAGING_PROFILE,
        "text": mensagem,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.telnyx.com/v2/messages",
        data=payload,
        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"[SMS] Erro HTTP {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"[SMS] Erro: {e}")
        return False

# ---------------------------------------------------------------------------
# Dados mockados
# ---------------------------------------------------------------------------

INVESTIDORES = {
    "123.456.789-00": {
        "nome": "Carlos Eduardo Mendes",
        "cpf": "123.456.789-00",
        "perfil_risco": "moderado",
        "valor_disponivel": 50000.0,
        "historico_produtos": ["Precatório Federal"],
        "ultimo_contato": "2025-11-15",
    },
    "987.654.321-00": {
        "nome": "Fernanda Lima Sousa",
        "cpf": "987.654.321-00",
        "perfil_risco": "conservador",
        "valor_disponivel": 15000.0,
        "historico_produtos": ["Debênture D+1 Plus"],
        "ultimo_contato": "2026-01-08",
    },
    "456.789.123-00": {
        "nome": "Rafael Oliveira Costa",
        "cpf": "456.789.123-00",
        "perfil_risco": "arrojado",
        "valor_disponivel": 200000.0,
        "historico_produtos": ["Operação Metrus", "Carteira de Pré-RPVs"],
        "ultimo_contato": "2026-02-20",
    },
    "321.654.987-00": {
        "nome": "Ana Paula Rodrigues",
        "cpf": "321.654.987-00",
        "perfil_risco": "conservador",
        "valor_disponivel": 8000.0,
        "historico_produtos": [],
        "ultimo_contato": "2025-09-30",
    },
    "654.321.098-00": {
        "nome": "Marcelo Teixeira Alves",
        "cpf": "654.321.098-00",
        "perfil_risco": "moderado",
        "valor_disponivel": 75000.0,
        "historico_produtos": ["Carteira de Pré-RPVs"],
        "ultimo_contato": "2026-03-10",
    },
}

PRODUTOS = [
    {
        "nome": "Operação Metrus",
        "rentabilidade": "25% ao ano",
        "minimo": 1000.0,
        "vencimento": "março de 2030",
        "liquidez": "No vencimento",
        "perfis": ["arrojado", "moderado"],
    },
    {
        "nome": "Carteira de Pré-RPVs",
        "rentabilidade": "20% ao ano",
        "minimo": 1000.0,
        "vencimento": "setembro de 2027",
        "liquidez": "No vencimento",
        "perfis": ["arrojado", "moderado", "conservador"],
    },
    {
        "nome": "Precatório Federal",
        "rentabilidade": "20% ao ano",
        "minimo": 1000.0,
        "vencimento": "dezembro de 2027",
        "liquidez": "No vencimento",
        "perfis": ["arrojado", "moderado", "conservador"],
    },
    {
        "nome": "Debênture D+1 Plus",
        "rentabilidade": "20% ao ano",
        "minimo": 1000.0,
        "vencimento": "Sem vencimento fixo",
        "liquidez": "1 dia útil",
        "perfis": ["conservador", "moderado"],
    },
]

LEADS_FILE = os.path.join(os.path.dirname(__file__), "leads.json")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("GCB Investimentos Demo")


@mcp.tool()
def buscar_investidor(cpf: str) -> dict:
    """
    Busca o perfil de um investidor pelo CPF.
    Retorna nome, perfil de risco, valor disponível para investimento,
    histórico de produtos e data do último contato.
    Use esta ferramenta antes de fazer recomendações.
    """
    # Normalizar CPF para busca
    cpf_normalizado = cpf.strip()
    investidor = INVESTIDORES.get(cpf_normalizado)

    if not investidor:
        # Tentar sem formatação
        cpf_digits = "".join(filter(str.isdigit, cpf))
        for key, val in INVESTIDORES.items():
            if "".join(filter(str.isdigit, key)) == cpf_digits:
                investidor = val
                break

    if not investidor:
        return {
            "encontrado": False,
            "mensagem": "Investidor não encontrado na base. Pode ser um novo cliente.",
        }

    return {
        "encontrado": True,
        "nome": investidor["nome"],
        "cpf": investidor["cpf"],
        "perfil_risco": investidor["perfil_risco"],
        "valor_disponivel_reais": investidor["valor_disponivel"],
        "historico_produtos": investidor["historico_produtos"],
        "ultimo_contato": investidor["ultimo_contato"],
    }


@mcp.tool()
def buscar_produtos_recomendados(perfil: str, valor: float) -> dict:
    """
    Retorna os produtos do portfólio GCB adequados ao perfil do investidor e valor disponível.
    perfil: 'conservador', 'moderado' ou 'arrojado'
    valor: valor disponível para investimento em reais
    """
    perfil = perfil.lower().strip()
    recomendados = [
        p for p in PRODUTOS
        if perfil in p["perfis"] and valor >= p["minimo"]
    ]

    if not recomendados:
        return {
            "recomendacoes": [],
            "mensagem": f"Nenhum produto disponível para o perfil '{perfil}' com valor de R$ {valor:.2f}.",
        }

    return {
        "recomendacoes": [
            {
                "nome": p["nome"],
                "rentabilidade": p["rentabilidade"],
                "minimo": f"R$ {p['minimo']:,.0f}",
                "vencimento": p["vencimento"],
                "liquidez": p["liquidez"],
            }
            for p in recomendados
        ],
        "total_encontrados": len(recomendados),
    }


@mcp.tool()
def registrar_interesse(cpf: str, produto: str, horario_contato: str) -> dict:
    """
    Registra o interesse do investidor em um produto.
    Use ao final da conversa quando o investidor confirmar interesse.
    cpf: CPF do investidor
    produto: nome do produto de interesse
    horario_contato: horário preferido para o especialista entrar em contato (manhã, tarde ou noite)
    """
    investidor = INVESTIDORES.get(cpf.strip())
    nome = investidor["nome"] if investidor else "Não identificado"

    lead = {
        "cpf": cpf,
        "nome": nome,
        "produto": produto,
        "horario_contato": horario_contato,
        "registrado_em": datetime.now().isoformat(),
    }

    # Salvar no arquivo
    try:
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leads = []

    leads.append(lead)

    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    # Disparar SMS de confirmação
    sms_enviado = False
    telefone = TELEFONES.get(cpf.strip())
    if telefone and investidor:
        sms_enviado = enviar_sms(telefone, nome, produto)

    return {
        "sucesso": True,
        "mensagem": f"Interesse de {nome} no produto '{produto}' registrado com sucesso.",
        "horario_retorno": horario_contato,
        "proximo_passo": "Um especialista da GCB entrará em contato no período informado.",
        "sms_confirmacao": "enviado" if sms_enviado else "nao_configurado",
    }


# ---------------------------------------------------------------------------
# HTTP endpoint /sms — recebe webhook da Clara e dispara SMS
# ---------------------------------------------------------------------------

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse

async def sms_endpoint(request: Request):
    """Recebe chamada da Clara e envia SMS de confirmação via Telnyx."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    nome = body.get("nome", "Investidor")
    produto = body.get("produto", "produto selecionado")
    telefone = body.get("telefone") or "+5511991986241"  # fallback demo

    ok = enviar_sms(telefone, nome, produto)
    return JSONResponse({"sms_enviado": ok, "para": telefone})


CONTATOS_DIALER = [
    {"nome": "Pedro Jesus",  "numero": "+5511991986241"},
    {"nome": "Marcos",       "numero": "+5511999999991"},  # trocar pelo número real
    {"nome": "Alexsander",   "numero": "+5511999999992"},  # trocar pelo número real
]

CAMPAIGN_STATUS = {}  # numero -> status


async def dialer_endpoint(request: Request):
    """Interface visual do discador."""
    rows = ""
    for c in CONTATOS_DIALER:
        status = CAMPAIGN_STATUS.get(c["numero"], "aguardando")
        if status == "aguardando":
            badge = '<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">⏳ Aguardando</span>'
        elif status == "discando":
            badge = '<span style="background:#1d4ed8;color:white;padding:3px 12px;border-radius:12px;font-size:13px;animation:pulse 1s infinite">📞 Discando...</span>'
        elif status == "atendeu":
            badge = '<span style="background:#15803d;color:white;padding:3px 12px;border-radius:12px;font-size:13px">✅ Atendeu</span>'
        elif status == "erro":
            badge = '<span style="background:#b91c1c;color:white;padding:3px 12px;border-radius:12px;font-size:13px">❌ Não atendeu</span>'
        else:
            badge = f'<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">{status}</span>'

        rows += f"""
        <tr>
            <td style="font-weight:500">{c['nome']}</td>
            <td style="color:#64748b">{c['numero']}</td>
            <td>{badge}</td>
        </tr>"""

    from starlette.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="3">
  <title>GCB — Discador Inteligente</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
    .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; }}
    h1 {{ font-size: 24px; font-weight: 700; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-top: 4px; }}
    .btn {{ background: #3b82f6; color: white; border: none; padding: 12px 28px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
    .btn:hover {{ background: #2563eb; }}
    .btn-stop {{ background: #ef4444; }}
    .btn-stop:hover {{ background: #dc2626; }}
    .card {{ background: #1e293b; border-radius: 16px; overflow: hidden; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #1e293b; color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; padding: 14px 20px; text-align: left; border-bottom: 1px solid #334155; }}
    td {{ padding: 16px 20px; font-size: 15px; border-bottom: 1px solid #1e293b; }}
    tr:last-child td {{ border-bottom: none; }}
    .stats {{ display: flex; gap: 16px; margin-bottom: 24px; }}
    .stat {{ background: #1e293b; border-radius: 12px; padding: 20px 24px; flex: 1; }}
    .stat-val {{ font-size: 32px; font-weight: 700; }}
    .stat-label {{ color: #64748b; font-size: 13px; margin-top: 4px; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.6}} }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>🤖 GCB — Discador Inteligente</h1>
      <p class="subtitle">Clara liga automaticamente e qualifica cada investidor</p>
    </div>
    <a href="/dialer/start" class="btn">▶ Iniciar Campanha</a>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-val">{len(CONTATOS_DIALER)}</div>
      <div class="stat-label">Contatos na fila</div>
    </div>
    <div class="stat">
      <div class="stat-val">{sum(1 for s in CAMPAIGN_STATUS.values() if s == 'atendeu')}</div>
      <div class="stat-label">Chamadas atendidas</div>
    </div>
    <div class="stat">
      <div class="stat-val">{sum(1 for s in CAMPAIGN_STATUS.values() if s == 'discando')}</div>
      <div class="stat-label">Em andamento</div>
    </div>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr><th>Nome</th><th>Número</th><th>Status</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <p style="color:#334155;font-size:12px;text-align:center">Atualiza automaticamente a cada 3 segundos</p>
</body>
</html>"""
    return HTMLResponse(html)


async def dialer_start(request: Request):
    """Dispara as ligações em background."""
    import threading

    def run_campaign():
        import urllib.request as ur
        import json as js
        for c in CONTATOS_DIALER:
            CAMPAIGN_STATUS[c["numero"]] = "discando"
            payload = js.dumps({
                "From": "+551151189954",
                "To": c["numero"],
                "AIAssistantId": "assistant-402286c0-bb62-4af9-ae5b-ad5be9faa21b",
                "MachineDetection": "Enable",
                "AsyncAmd": True,
                "DetectionMode": "Premium",
            }).encode()
            req = ur.Request(
                "https://api.telnyx.com/v2/texml/ai_calls/2924083901620028790",
                data=payload,
                headers={
                    "Authorization": f"Bearer {TELNYX_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with ur.urlopen(req, timeout=10) as resp:
                    result = js.load(resp)
                    if result.get("status") in ("queued", "ringing"):
                        CAMPAIGN_STATUS[c["numero"]] = "atendeu"
                    else:
                        CAMPAIGN_STATUS[c["numero"]] = "discando"
            except Exception as e:
                CAMPAIGN_STATUS[c["numero"]] = "erro"
            import time; time.sleep(6)

    threading.Thread(target=run_campaign, daemon=True).start()
    from starlette.responses import RedirectResponse
    return RedirectResponse("/dialer", status_code=303)


async def dashboard_endpoint(request: Request):
    """Dashboard HTML para visualizar leads em tempo real."""
    try:
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leads = []

    rows = ""
    for lead in reversed(leads):
        status = lead.get("status", "")
        badge_color = "#22c55e" if status == "interesse_confirmado" else "#94a3b8"
        badge_label = "✅ Interesse" if status == "interesse_confirmado" else "📋 " + status.replace("_", " ").title()
        rows += f"""
        <tr>
            <td>{lead.get("nome_investidor", "—")}</td>
            <td>{lead.get("produto_interesse", "—")}</td>
            <td>{lead.get("valor_disponivel", "—")}</td>
            <td>{lead.get("horario_contato", "—")}</td>
            <td><span style="background:{badge_color};color:white;padding:3px 10px;border-radius:12px;font-size:13px">{badge_label}</span></td>
            <td style="color:#94a3b8;font-size:12px">{lead.get("registrado_em","")[:19].replace("T"," ")}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5">
  <title>GCB Investimentos — Leads ao Vivo</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px; }}
    h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 28px; }}
    .badge-live {{ display: inline-block; background: #ef4444; color: white; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-left: 10px; animation: pulse 1.5s infinite; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.5}} }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }}
    th {{ background: #1e293b; color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
    td {{ padding: 14px 16px; font-size: 14px; border-bottom: 1px solid #1e293b; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #263348; }}
    .total {{ margin-top: 16px; color: #64748b; font-size: 13px; }}
  </style>
</head>
<body>
  <h1>GCB Investimentos <span class="badge-live">● AO VIVO</span></h1>
  <p class="subtitle">Leads capturados pela Clara — atualiza a cada 5 segundos</p>
  <table>
    <thead>
      <tr>
        <th>Nome</th><th>Produto</th><th>Valor</th><th>Horário</th><th>Status</th><th>Registrado em</th>
      </tr>
    </thead>
    <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:#475569;padding:32px">Aguardando leads...</td></tr>'}</tbody>
  </table>
  <p class="total">Total: {len(leads)} lead{"s" if len(leads) != 1 else ""} registrado{"s" if len(leads) != 1 else ""}</p>
</body>
</html>"""
    from starlette.responses import HTMLResponse
    return HTMLResponse(html)


async def lead_endpoint(request: Request):
    """Substitui webhook.site — registra lead e dispara SMS se interesse confirmado."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    nome = body.get("nome_investidor", "Investidor")
    produto = body.get("produto_interesse", "")
    status = body.get("status", "")
    horario = body.get("horario_contato", "")

    print(f"[LEAD] {nome} | {produto} | {status} | {horario}")

    # Salvar no leads.json
    lead = {**body, "registrado_em": datetime.now().isoformat()}
    try:
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        leads = []
    leads.append(lead)
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    # Disparar SMS se interesse confirmado
    sms_ok = False
    if status == "interesse_confirmado" and produto:
        sms_ok = enviar_sms("+5511991986241", nome, produto)
        print(f"[SMS] Enviado: {sms_ok}")

    return JSONResponse({
        "sucesso": True,
        "mensagem": f"Lead {nome} registrado.",
        "sms_enviado": sms_ok
    })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import uvicorn
    from mcp.server.fastmcp import FastMCP

    transport = sys.argv[1] if len(sys.argv) > 1 else "sse"
    print(f"🚀 MCP Server GCB Investimentos iniciando (transport: {transport})...")
    print("   Acesse: http://localhost:8000/sse")
    print("   SMS endpoint: http://localhost:8000/sms")

    if transport == "sse":
        mcp._custom_starlette_routes = [
            Route("/sms", sms_endpoint, methods=["POST"]),
            Route("/lead", lead_endpoint, methods=["POST"]),
            Route("/dashboard", dashboard_endpoint, methods=["GET"]),
            Route("/dialer", dialer_endpoint, methods=["GET"]),
            Route("/dialer/start", dialer_start, methods=["GET"]),
        ]
        # Build the Starlette app and run with uvicorn on 0.0.0.0
        starlette_app = mcp.sse_app()
        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=8000)
    else:
        mcp.run(transport=transport)

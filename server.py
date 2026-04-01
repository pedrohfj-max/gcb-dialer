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
HUBSPOT_TOKEN = os.environ.get("HUBSPOT_TOKEN", "")


def criar_lead_hubspot(nome: str, telefone: str, produto: str, horario: str) -> bool:
    """Cria contato + deal no HubSpot quando lead é qualificado."""
    if not HUBSPOT_TOKEN:
        print("[HUBSPOT] Token não configurado, pulando")
        return False
    headers = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}
    nome_parts = nome.strip().split(" ", 1)
    primeiro = nome_parts[0]
    sobrenome = nome_parts[1] if len(nome_parts) > 1 else ""

    contact_id = None
    # Primeiro: buscar se já existe pelo telefone
    try:
        search_payload = json.dumps({
            "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": telefone}]}],
            "properties": ["firstname", "lastname", "phone"],
            "limit": 1
        }).encode()
        req_search = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/contacts/search",
            data=search_payload, headers=headers, method="POST")
        with urllib.request.urlopen(req_search, timeout=8) as r:
            results = json.load(r).get("results", [])
            if results:
                contact_id = results[0]["id"]
                print(f"[HUBSPOT] Contato existente encontrado ID {contact_id}")
    except Exception as e:
        print(f"[HUBSPOT] Erro busca: {e}")

    if not contact_id:
        try:
            payload = json.dumps({"properties": {
                "firstname": primeiro, "lastname": sobrenome, "phone": telefone,
                "hs_lead_status": "IN_PROGRESS",
            }}).encode()
            req = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/contacts",
                data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as r:
                contact_id = json.load(r).get("id")
                print(f"[HUBSPOT] Contato criado ID {contact_id}")
        except urllib.error.HTTPError as e:
            if e.code != 409:
                print(f"[HUBSPOT] Erro contato: {e.code}")
                return False

    try:
        payload2 = json.dumps({"properties": {
            "dealname": f"{nome} — {produto}",
            "dealstage": "appointmentscheduled",
            "pipeline": "default",
            "description": f"Lead qualificado pela Clara. Produto: {produto}. Horário: {horario}.",
        }}).encode()
        req2 = urllib.request.Request("https://api.hubapi.com/crm/v3/objects/deals",
            data=payload2, headers=headers, method="POST")
        with urllib.request.urlopen(req2, timeout=8) as r:
            deal_id = json.load(r).get("id")
            print(f"[HUBSPOT] Deal criado ID {deal_id}")

        if contact_id and deal_id:
            assoc = json.dumps({"inputs": [{"from": {"id": deal_id}, "to": {"id": contact_id}, "type": "deal_to_contact"}]}).encode()
            req3 = urllib.request.Request("https://api.hubapi.com/crm/v3/associations/deals/contacts/batch/create",
                data=assoc, headers=headers, method="POST")
            urllib.request.urlopen(req3, timeout=5)
        return True
    except Exception as e:
        print(f"[HUBSPOT] Erro deal: {e}")
        return False

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
STATE_FILE = os.path.join(os.path.dirname(__file__), "campaign_state.json")


def save_state():
    """Persiste o estado da campanha em arquivo."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "contatos": CONTATOS_DIALER,
                "status": CAMPAIGN_STATUS,
                "retries": CAMPAIGN_RETRIES,
                "cooldown": {k: v for k, v in COOLDOWN_UNTIL.items()},
                "active_calls": ACTIVE_CALLS,
            }, f, ensure_ascii=False)
    except Exception as e:
        print(f"[STATE] Erro ao salvar: {e}")


def load_state():
    """Carrega estado da campanha do arquivo."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        CONTATOS_DIALER.clear()
        CONTATOS_DIALER.extend(state.get("contatos", []))
        CAMPAIGN_STATUS.update(state.get("status", {}))
        CAMPAIGN_RETRIES.update(state.get("retries", {}))
        COOLDOWN_UNTIL.update({k: float(v) for k, v in state.get("cooldown", {}).items()})
        print(f"[STATE] Carregado: {len(CONTATOS_DIALER)} contatos")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[STATE] Erro ao carregar: {e}")

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


CONTATOS_DIALER = []  # preenchido via upload de CSV
CAMPAIGN_STATUS = {}   # numero -> status
CAMPAIGN_RETRIES = {}  # numero -> tentativas feitas
CAMPAIGN_PAUSED = False
CAMPAIGN_CONFIG = {
    "max_retries": 3,
    "retry_interval": 120,   # segundos entre tentativas
    "intervalo_chamadas": 8, # segundos entre chamadas
    "max_simultaneas": 3,    # máximo de chamadas ao mesmo tempo
    "cooldown_dias": 7,      # dias sem ligar após sem_interesse ou esgotado
    "horario_inicio": "09:00",  # hora de início
    "horario_fim": "20:00",     # hora de fim
    "timezone": "America/Sao_Paulo",
}
ACTIVE_CALLS = 0        # contador de chamadas ativas
COOLDOWN_UNTIL = {}     # numero -> timestamp de quando pode ligar de novo
NOTIFICATIONS = []      # lista de notificações para o pop-up
CALLS_ANSWERED = set()  # números que atenderam (para distinguir de não atendeu)
CALL_START_TIME = {}    # numero -> timestamp de quando a chamada foi iniciada


async def dialer_paste(request: Request):
    """Recebe contatos colados como texto e atualiza a lista."""
    from starlette.responses import RedirectResponse
    form = await request.form()
    text = form.get("text", "").strip()

    CONTATOS_DIALER.clear()
    CAMPAIGN_STATUS.clear()
    CAMPAIGN_RETRIES.clear()
    COOLDOWN_UNTIL.clear()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("nome"):
            continue
        parts = line.split(",", 1)
        if len(parts) == 2:
            nome = parts[0].strip()
            numero = parts[1].strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if numero and not numero.startswith("+"):
                numero = "+55" + numero.lstrip("0")
            if nome and numero:
                CONTATOS_DIALER.append({"nome": nome, "numero": numero})

    save_state()
    return RedirectResponse("/dialer", status_code=303)


async def dialer_upload(request: Request):
    """Recebe CSV com contatos e atualiza a lista."""
    from starlette.responses import HTMLResponse, RedirectResponse
    import csv, io

    form = await request.form()
    file = form.get("file")
    if not file:
        return HTMLResponse("Nenhum arquivo enviado.", status_code=400)

    content = await file.read()
    text = content.decode("utf-8-sig").strip()

    CONTATOS_DIALER.clear()
    CAMPAIGN_STATUS.clear()
    CAMPAIGN_RETRIES.clear()

    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        nome = row.get("nome") or row.get("Nome") or row.get("name") or ""
        numero = row.get("numero") or row.get("Numero") or row.get("telefone") or row.get("Telefone") or ""
        numero = numero.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if numero and not numero.startswith("+"):
            numero = "+55" + numero.lstrip("0")
        if nome and numero:
            CONTATOS_DIALER.append({"nome": nome.strip(), "numero": numero})

    save_state()
    return RedirectResponse("/dialer", status_code=303)


async def dialer_endpoint(request: Request):
    """Interface visual do discador."""
    from starlette.responses import HTMLResponse

    rows = ""
    for c in CONTATOS_DIALER:
        status = CAMPAIGN_STATUS.get(c["numero"], "aguardando")
        if status == "aguardando":
            badge = '<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">⏳ Aguardando</span>'
        elif status == "discando":
            badge = '<span style="background:#1d4ed8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📞 Discando...</span>'
        elif status == "atendeu":
            badge = '<span style="background:#15803d;color:white;padding:3px 12px;border-radius:12px;font-size:13px">✅ Atendeu</span>'
        elif "chamada" in status:
            badge = '<span style="background:#0891b2;color:white;padding:3px 12px;border-radius:12px;font-size:13px;animation:pulse 1s infinite">📱 Em chamada...</span>'
        elif "qualificado" in status:
            badge = '<span style="background:#15803d;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🏆 Qualificado</span>'
        elif status == "caixa_postal":
            badge = '<span style="background:#78350f;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📱 Caixa postal</span>'
        elif status == "nao_atendeu":
            badge = '<span style="background:#92400e;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📵 Não atendeu</span>'
        elif status == "erro":
            badge = '<span style="background:#b91c1c;color:white;padding:3px 12px;border-radius:12px;font-size:13px">❌ Erro</span>'
        elif status == "sem_interesse":
            badge = '<span style="background:#6b21a8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">👋 Sem interesse</span>'
        elif status.startswith("discando"):
            badge = f'<span style="background:#1d4ed8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📞 {status.capitalize()}</span>'
        elif status.startswith("esgotado"):
            badge = f'<span style="background:#4b5563;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🚫 {status.capitalize()}</span>'
        elif status.startswith("cooldown"):
            badge = f'<span style="background:#7c3aed;color:white;padding:3px 12px;border-radius:12px;font-size:13px">⏱ {status.capitalize()}</span>'
        elif "horário" in status:
            badge = f'<span style="background:#0369a1;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🕘 {status.capitalize()}</span>'
        else:
            badge = f'<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">{status}</span>'

        rows += f"""
        <tr>
            <td style="font-weight:500">{c['nome']}</td>
            <td style="color:#64748b">{c['numero']}</td>
            <td>{badge}</td>
        </tr>"""

    empty_msg = ""
    if not CONTATOS_DIALER:
        empty_msg = '<tr><td colspan="3" style="text-align:center;color:#475569;padding:32px">Faça upload de um CSV para começar</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <title>GCB — Discador Inteligente</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
    .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; }}
    h1 {{ font-size: 24px; font-weight: 700; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-top: 4px; }}
    .btn {{ background: #3b82f6; color: white; border: none; padding: 12px 28px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
    .btn:hover {{ background: #2563eb; }}
    .btn:disabled {{ background: #334155; cursor: not-allowed; }}
    .upload-area {{ background: #1e293b; border: 2px dashed #334155; border-radius: 12px; padding: 24px; margin-bottom: 24px; display: flex; align-items: center; gap: 16px; }}
    .upload-area input[type=file] {{ color: #94a3b8; }}
    .upload-btn {{ background: #0f766e; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }}
    .card {{ background: #1e293b; border-radius: 16px; overflow: hidden; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #1e293b; color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; padding: 14px 20px; text-align: left; border-bottom: 1px solid #334155; }}
    td {{ padding: 16px 20px; font-size: 15px; border-bottom: 1px solid #1e293b; }}
    tr:last-child td {{ border-bottom: none; }}
    .stats {{ display: flex; gap: 16px; margin-bottom: 24px; }}
    .stat {{ background: #1e293b; border-radius: 12px; padding: 20px 24px; flex: 1; }}
    .stat-val {{ font-size: 32px; font-weight: 700; }}
    .stat-label {{ color: #64748b; font-size: 13px; margin-top: 4px; }}
    .hint {{ color: #475569; font-size: 12px; margin-top: 8px; }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.6}} }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>🤖 GCB — Discador Inteligente</h1>
      <p class="subtitle">Clara liga automaticamente e qualifica cada investidor</p>
    </div>
    <div style="display:flex;gap:10px">
      {'<a href="/dialer/start" class="btn">▶ Iniciar Campanha</a>' if CONTATOS_DIALER else '<button class="btn" disabled>▶ Iniciar Campanha</button>'}
      {'<a href="/dialer/pause" class="btn" style="background:#f59e0b">⏸ Pausar</a>' if not CAMPAIGN_PAUSED else '<a href="/dialer/pause" class="btn" style="background:#22c55e">▶ Retomar</a>'}
      <a href="/dialer/report" class="btn" style="background:#6366f1">📊 Relatório</a>
    </div>
  </div>

  <div class="upload-area" style="margin-bottom:16px">
    <form action="/dialer/config" method="post" style="display:flex;align-items:flex-end;gap:20px;width:100%;flex-wrap:wrap">
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">MAX TENTATIVAS</label>
        <input type="number" name="max_retries" value="{CAMPAIGN_CONFIG['max_retries']}" min="1" max="10"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:80px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">INTERVALO ENTRE TENTATIVAS (min)</label>
        <input type="number" name="retry_interval" value="{CAMPAIGN_CONFIG['retry_interval'] // 60}" min="1" max="60"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:80px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">INTERVALO ENTRE CHAMADAS (seg)</label>
        <input type="number" name="intervalo_chamadas" value="{CAMPAIGN_CONFIG['intervalo_chamadas']}" min="5" max="60"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:80px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">CHAMADAS SIMULTÂNEAS</label>
        <input type="number" name="max_simultaneas" value="{CAMPAIGN_CONFIG['max_simultaneas']}" min="1" max="10"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:80px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">COOLDOWN (dias)</label>
        <input type="number" name="cooldown_dias" value="{CAMPAIGN_CONFIG['cooldown_dias']}" min="1" max="90"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:80px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">INÍCIO</label>
        <input type="time" name="horario_inicio" value="{CAMPAIGN_CONFIG['horario_inicio']}"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:100px;font-size:15px">
      </div>
      <div>
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:4px">FIM</label>
        <input type="time" name="horario_fim" value="{CAMPAIGN_CONFIG['horario_fim']}"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px 12px;width:100px;font-size:15px">
      </div>
      <button type="submit" style="background:#475569;color:white;border:none;padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">💾 Salvar</button>
    </form>
  </div>

  <div class="upload-area" style="flex-direction:column;align-items:flex-start">
    <div style="font-weight:600;margin-bottom:12px">📋 Adicionar contatos</div>
    <div style="display:flex;gap:16px;width:100%;flex-wrap:wrap">
      <!-- Opção 1: colar texto -->
      <form action="/dialer/paste" method="post" style="flex:1;min-width:280px">
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:6px">COLAR LISTA (nome,numero — um por linha)</label>
        <textarea name="text" rows="4" placeholder="Nome do Contato,11999999999&#10;Outro Contato,11988888888"
          style="width:100%;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:10px;font-size:13px;font-family:monospace;resize:vertical"></textarea>
        <button type="submit" class="upload-btn" style="margin-top:8px;width:100%">✅ Carregar lista</button>
      </form>
      <!-- Opção 2: upload arquivo -->
      <form action="/dialer/upload" method="post" enctype="multipart/form-data" style="flex:1;min-width:280px">
        <label style="color:#64748b;font-size:12px;display:block;margin-bottom:6px">OU FAZER UPLOAD DE ARQUIVO CSV</label>
        <input type="file" name="file" accept=".csv,.txt"
          style="color:#94a3b8;background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px;width:100%">
        <button type="submit" class="upload-btn" style="margin-top:8px;width:100%">📂 Enviar arquivo</button>
      </form>
    </div>
    <p class="hint" style="margin-top:8px">Formato: nome,numero — sem código de país (ex: 11991986241)</p>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-val" id="stat-total">{len(CONTATOS_DIALER)}</div>
      <div class="stat-label">Contatos na fila</div>
    </div>
    <div class="stat">
      <div class="stat-val" id="stat-atendidas">{sum(1 for s in CAMPAIGN_STATUS.values() if "qualificado" in s)}</div>
      <div class="stat-label">Qualificados</div>
    </div>
    <div class="stat">
      <div class="stat-val" id="stat-ligando">{ACTIVE_CALLS}</div>
      <div class="stat-label">Ligando agora</div>
    </div>
    <div class="stat" style="border-left:3px solid #334155">
      <div class="stat-val" id="stat-simult" style="font-size:18px;color:#64748b">{ACTIVE_CALLS}/{CAMPAIGN_CONFIG['max_simultaneas']}</div>
      <div class="stat-label">Simultâneas</div>
    </div>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr><th>Nome</th><th>Número</th><th>Status</th></tr>
      </thead>
      <tbody id="contact-table">{rows or empty_msg}</tbody>
    </table>
  </div>

  <p style="color:#334155;font-size:12px;text-align:center" id="last-update">Aguardando...</p>
</div>

<script>
// Atualiza só a tabela e os stats — sem recarregar a página inteira
async function refreshStatus() {{
  try {{
    const r = await fetch('/dialer/status');
    const data = await r.json();

    // Atualiza stats
    document.getElementById('stat-total').textContent = data.total;
    document.getElementById('stat-atendidas').textContent = data.atendidas;
    document.getElementById('stat-ligando').textContent = data.ligando;
    document.getElementById('stat-simult').textContent = data.ligando + '/' + data.max_simult;

    // Atualiza tabela
    document.getElementById('contact-table').innerHTML = data.rows_html;

    // Timestamp
    const now = new Date().toLocaleTimeString('pt-BR');
    document.getElementById('last-update').textContent = 'Última atualização: ' + now;
  }} catch(e) {{}}
}}

setInterval(refreshStatus, 3000);
refreshStatus();
</script>

<!-- Pop-up de notificação -->
<div id="notif-container" style="position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:12px;z-index:999;max-width:360px"></div>

<script>
function showNotif(n) {{
  const el = document.createElement('div');
  el.style.cssText = 'background:#15803d;color:white;padding:16px 20px;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:slideIn .3s ease;font-size:14px;line-height:1.5';
  el.innerHTML = `<div style="font-weight:700;font-size:16px;margin-bottom:4px">🏆 Lead Qualificado!</div>
    <div><strong>${{n.nome}}</strong> confirmou interesse</div>
    <div style="color:#86efac">📈 ${{n.produto}}</div>
    <div style="color:#86efac;font-size:12px;margin-top:4px">⏰ Melhor horário: ${{n.horario || 'não informado'}} &nbsp;·&nbsp; ${{n.timestamp}}</div>`;
  document.getElementById('notif-container').appendChild(el);
  setTimeout(() => el.remove(), 8000);
}}

async function checkNotifs() {{
  try {{
    const r = await fetch('/dialer/notifications');
    const data = await r.json();
    (data.notifications || []).forEach(showNotif);
  }} catch(e) {{}}
}}

// Verificar notificações a cada 2 segundos
setInterval(checkNotifs, 2000);
</script>

<style>
@keyframes slideIn {{
  from {{ transform: translateX(120%); opacity: 0; }}
  to {{ transform: translateX(0); opacity: 1; }}
}}
</style>
</body>
</html>"""
    return HTMLResponse(html)


async def dialer_start(request: Request):
    """Dispara as ligações em background."""
    global CAMPAIGN_PAUSED
    import threading
    from starlette.responses import RedirectResponse

    CAMPAIGN_PAUSED = False

    def dentro_horario():
        """Verifica se está dentro do horário permitido (suporta HH:MM)."""
        from datetime import datetime as _dt
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(CAMPAIGN_CONFIG["timezone"])
            agora = _dt.now(tz)
        except Exception:
            agora = _dt.now()
        agora_str = agora.strftime("%H:%M")
        return CAMPAIGN_CONFIG["horario_inicio"] <= agora_str < CAMPAIGN_CONFIG["horario_fim"]

    def fazer_ligacao(numero, nome):
        """Faz uma ligação e retorna True se foi enfileirada com sucesso."""
        global ACTIVE_CALLS
        import urllib.request as ur
        import json as js, time

        # Esperar se atingiu limite de simultâneas
        while ACTIVE_CALLS >= CAMPAIGN_CONFIG["max_simultaneas"]:
            time.sleep(2)

        ACTIVE_CALLS += 1
        CALL_START_TIME[numero] = time.time()
        payload = js.dumps({
            "From": "+551151189954",
            "To": numero,
            "AIAssistantId": "assistant-402286c0-bb62-4af9-ae5b-ad5be9faa21b",
            "MachineDetection": "Enable",
            "AsyncAmd": True,
            "DetectionMode": "Premium",
            "StatusCallback": "https://gcb-dialer-production.up.railway.app/dialer/webhook",
            "StatusCallbackMethod": "POST",
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
                return result.get("status") in ("queued", "ringing")
        except Exception:
            return False
        finally:
            # Decrementar após ~30s (tempo médio de atendimento/não atendimento)
            def decrement():
                global ACTIVE_CALLS
                time.sleep(30)
                ACTIVE_CALLS = max(0, ACTIVE_CALLS - 1)
            import threading
            threading.Thread(target=decrement, daemon=True).start()

    def ligar_com_retry(c):
        """Gerencia ligação + retries para um único contato. Bloqueia até terminar."""
        import time
        numero = c["numero"]
        nome = c["nome"]
        max_r = CAMPAIGN_CONFIG["max_retries"]

        for tentativa in range(1, max_r + 1):
            # Pausado?
            while CAMPAIGN_PAUSED:
                time.sleep(1)

            # Fora do horário?
            while not dentro_horario():
                CAMPAIGN_STATUS[numero] = f"aguardando horário ({CAMPAIGN_CONFIG['horario_inicio']}h-{CAMPAIGN_CONFIG['horario_fim']}h)"
                time.sleep(60)

            # Já finalizado por lead?
            current = CAMPAIGN_STATUS.get(numero, "")
            if "qualificado" in current or current == "sem_interesse":
                return

            # Verificar de novo antes de ligar — pode ter qualificado durante o retry interval
            st = CAMPAIGN_STATUS.get(numero, "")
            if "qualificado" in st or st in ("atendeu", "sem_interesse"):
                print(f"[DIALER] {nome} já finalizado ({st}), pulando tentativa {tentativa}")
                return

            # Fazer a ligação
            CAMPAIGN_RETRIES[numero] = tentativa
            CAMPAIGN_STATUS[numero] = f"discando ({tentativa}/{max_r})"
            save_state()
            print(f"[DIALER] {nome} — tentativa {tentativa}/{max_r}")

            ok = fazer_ligacao(numero, nome)
            if not ok:
                CAMPAIGN_STATUS[numero] = "erro"
                save_state()
                break

            # Esperar o webhook confirmar resultado (timeout de 90s)
            deadline = time.time() + 90
            while time.time() < deadline:
                if CAMPAIGN_PAUSED:
                    time.sleep(1)
                    continue
                st = CAMPAIGN_STATUS.get(numero, "")
                # Terminou — webhook chegou
                if st in ("nao_atendeu", "caixa_postal", "atendeu") or "qualificado" in st or st == "sem_interesse":
                    break
                time.sleep(2)

            # Verificar resultado final
            st = CAMPAIGN_STATUS.get(numero, "")
            if "qualificado" in st or st in ("atendeu", "sem_interesse"):
                return  # sucesso

            if st in ("nao_atendeu", "caixa_postal", "erro") or "discando" in st:
                if tentativa < max_r:
                    # Aguardar intervalo de retry
                    print(f"[RETRY] {nome} — aguardando {CAMPAIGN_CONFIG['retry_interval']}s antes da tentativa {tentativa+1}")
                    time.sleep(CAMPAIGN_CONFIG["retry_interval"])
                else:
                    # Esgotou
                    CAMPAIGN_STATUS[numero] = f"esgotado ({tentativa} tentativas)"
                    dias = CAMPAIGN_CONFIG["cooldown_dias"]
                    COOLDOWN_UNTIL[numero] = time.time() + (dias * 86400)
                    save_state()
                    print(f"[ESGOTADO] {nome} após {tentativa} tentativas")

    def run_campaign():
        import time

        for c in list(CONTATOS_DIALER):
            # Pausado?
            while CAMPAIGN_PAUSED:
                time.sleep(1)

            numero = c["numero"]

            # Pular já finalizados
            st = CAMPAIGN_STATUS.get(numero, "")
            if "qualificado" in st or st in ("atendeu", "sem_interesse"):
                continue

            # Cooldown ativo?
            cooldown_end = COOLDOWN_UNTIL.get(numero, 0)
            if time.time() < cooldown_end:
                restante = int((cooldown_end - time.time()) / 3600)
                CAMPAIGN_STATUS[numero] = f"cooldown ({restante}h)"
                save_state()
                continue

            # Ligar com retry (bloqueante por contato)
            ligar_com_retry(c)

            # Intervalo entre contatos diferentes
            if not CAMPAIGN_PAUSED:
                time.sleep(CAMPAIGN_CONFIG["intervalo_chamadas"])

    threading.Thread(target=run_campaign, daemon=True).start()
    return RedirectResponse("/dialer", status_code=303)


async def dialer_webhook(request: Request):
    """Recebe eventos de status das chamadas (AMD, atendida, encerrada, etc)."""
    import time
    try:
        # Telnyx envia como form ou JSON
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)
    except Exception:
        body = {}

    call_status = body.get("CallStatus", "")
    to_number = body.get("To", "").strip()
    amd_result = body.get("AnsweredBy", "")  # machine / human / unknown

    print(f"[WEBHOOK] To:{to_number} Status:{call_status} AMD:{amd_result} Body:{dict(list(body.items())[:6])}")

    # Normalize number — try with and without + prefix
    to_variants = {to_number, "+" + to_number.lstrip("+"), to_number.lstrip("+")}

    # Find matching key in CAMPAIGN_STATUS
    matched_number = None
    for variant in to_variants:
        if variant in CAMPAIGN_STATUS:
            matched_number = variant
            break
    # Also try partial match
    if not matched_number:
        for num in list(CAMPAIGN_STATUS.keys()):
            if num.lstrip("+") == to_number.lstrip("+"):
                matched_number = num
                break

    print(f"[WEBHOOK] Matched: {matched_number} | Status keys: {list(CAMPAIGN_STATUS.keys())}")

    # Se caixa postal detectada
    if amd_result in ("machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other", "fax"):
        if matched_number:
            CAMPAIGN_STATUS[matched_number] = "caixa_postal"
            print(f"[AMD] Caixa postal: {matched_number}")
            save_state()

    # Se atendeu (in-progress = alguém atendeu o telefone)
    elif call_status == "in-progress":
        if matched_number:
            CALLS_ANSWERED.add(matched_number)
            CAMPAIGN_STATUS[matched_number] = "📱 Em chamada..."
            save_state()
            print(f"[WEBHOOK] Atendeu: {matched_number}")

    # Se não atendeu
    elif call_status in ("no-answer", "busy", "failed", "canceled"):
        if matched_number and CAMPAIGN_STATUS.get(matched_number) != "caixa_postal":
            CAMPAIGN_STATUS[matched_number] = "nao_atendeu"
            save_state()

    # Chamada encerrada
    elif call_status == "completed":
        if matched_number:
            current = CAMPAIGN_STATUS.get(matched_number, "")
            already_qualified = "qualificado" in current or current == "sem_interesse"
            if not already_qualified:
                # Usar duração enviada pela Telnyx pra distinguir atendeu de não atendeu
                try:
                    duration_sec = int(body.get("CallDuration", 0))
                except:
                    duration_sec = 0

                print(f"[WEBHOOK] Duração da chamada: {duration_sec}s")

                if matched_number in CALLS_ANSWERED or duration_sec > 10:
                    CAMPAIGN_STATUS[matched_number] = "atendeu"
                    print(f"[WEBHOOK] Marcado como ATENDEU (duração: {duration_sec}s)")
                else:
                    CAMPAIGN_STATUS[matched_number] = "nao_atendeu"
                save_state()

    # Decrementar chamadas ativas quando encerrar
    if call_status in ("completed", "no-answer", "busy", "failed", "canceled"):
        global ACTIVE_CALLS
        ACTIVE_CALLS = max(0, ACTIVE_CALLS - 1)
        save_state()

    return JSONResponse({"ok": True})


async def dialer_report(request: Request):
    """Relatório final da campanha."""
    from starlette.responses import HTMLResponse

    total = len(CONTATOS_DIALER)
    if total == 0:
        return HTMLResponse("<h2 style='font-family:sans-serif;color:white;background:#0f172a;padding:40px'>Nenhuma campanha rodou ainda.</h2>")

    qualificados = [c for c in CONTATOS_DIALER if "qualificado" in CAMPAIGN_STATUS.get(c["numero"], "")]
    sem_interesse = [c for c in CONTATOS_DIALER if CAMPAIGN_STATUS.get(c["numero"]) == "sem_interesse"]
    nao_atendeu = [c for c in CONTATOS_DIALER if CAMPAIGN_STATUS.get(c["numero"]) in ("nao_atendeu", "esgotado")]
    caixa_postal = [c for c in CONTATOS_DIALER if CAMPAIGN_STATUS.get(c["numero"]) == "caixa_postal"]
    em_andamento = [c for c in CONTATOS_DIALER if CAMPAIGN_STATUS.get(c["numero"], "aguardando") not in ("sem_interesse", "nao_atendeu", "caixa_postal") and "qualificado" not in CAMPAIGN_STATUS.get(c["numero"], "") and "esgotado" not in CAMPAIGN_STATUS.get(c["numero"], "")]

    taxa_contato = round(len(qualificados + sem_interesse) / total * 100) if total else 0
    taxa_conv = round(len(qualificados) / total * 100) if total else 0

    # Leads qualificados da lista de leads.json
    try:
        with open(LEADS_FILE) as f:
            leads = json.load(f)
        leads_qual = [l for l in leads if l.get("status") == "interesse_confirmado"]
    except:
        leads_qual = []

    leads_rows = ""
    for l in leads_qual:
        leads_rows += f"""<tr>
            <td>{l.get('nome_investidor','—')}</td>
            <td style="color:#86efac">{l.get('produto_interesse','—')}</td>
            <td>{l.get('horario_contato','—')}</td>
            <td style="color:#64748b;font-size:12px">{l.get('registrado_em','')[:19].replace('T',' ')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <title>GCB — Relatório da Campanha</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,sans-serif; background:#0f172a; color:#e2e8f0; padding:40px; }}
    h1 {{ font-size:24px; font-weight:700; margin-bottom:4px; }}
    .sub {{ color:#64748b; font-size:14px; margin-bottom:32px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }}
    .card {{ background:#1e293b; border-radius:12px; padding:20px 24px; }}
    .val {{ font-size:36px; font-weight:700; }}
    .label {{ color:#64748b; font-size:13px; margin-top:4px; }}
    .green {{ color:#22c55e; }}
    .red {{ color:#ef4444; }}
    .yellow {{ color:#f59e0b; }}
    .blue {{ color:#60a5fa; }}
    table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:12px; overflow:hidden; }}
    th {{ color:#64748b; font-size:12px; text-transform:uppercase; padding:12px 16px; text-align:left; border-bottom:1px solid #334155; }}
    td {{ padding:14px 16px; font-size:14px; border-bottom:1px solid #0f172a; }}
    .section-title {{ font-size:16px; font-weight:600; margin:24px 0 12px; }}
    .back {{ display:inline-block; margin-bottom:24px; color:#60a5fa; text-decoration:none; font-size:14px; }}
    .bar-wrap {{ background:#334155; border-radius:99px; height:8px; margin-top:8px; }}
    .bar {{ height:8px; border-radius:99px; background:#22c55e; }}
  </style>
</head>
<body>
  <a href="/dialer" class="back">← Voltar ao discador</a>
  <h1>📊 Relatório da Campanha</h1>
  <p class="sub">GCB Investimentos · {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>

  <div class="grid">
    <div class="card">
      <div class="val">{total}</div>
      <div class="label">Total de contatos</div>
    </div>
    <div class="card">
      <div class="val green">{len(qualificados)}</div>
      <div class="label">Leads qualificados</div>
      <div class="bar-wrap"><div class="bar" style="width:{taxa_conv}%"></div></div>
      <div style="color:#64748b;font-size:12px;margin-top:4px">{taxa_conv}% de conversão</div>
    </div>
    <div class="card">
      <div class="val blue">{taxa_contato}%</div>
      <div class="label">Taxa de contato</div>
    </div>
    <div class="card">
      <div class="val yellow">{len(nao_atendeu) + len(caixa_postal)}</div>
      <div class="label">Não contatados</div>
    </div>
  </div>

  <div class="section-title">🏆 Leads Qualificados</div>
  <table>
    <thead><tr><th>Nome</th><th>Produto</th><th>Horário preferido</th><th>Registrado em</th></tr></thead>
    <tbody>{leads_rows if leads_rows else '<tr><td colspan="4" style="text-align:center;color:#475569;padding:24px">Nenhum lead qualificado ainda</td></tr>'}</tbody>
  </table>

  <div class="section-title">📋 Resumo por status</div>
  <table>
    <thead><tr><th>Status</th><th>Quantidade</th><th>%</th></tr></thead>
    <tbody>
      <tr><td>🏆 Qualificados</td><td>{len(qualificados)}</td><td>{round(len(qualificados)/total*100)}%</td></tr>
      <tr><td>👋 Sem interesse</td><td>{len(sem_interesse)}</td><td>{round(len(sem_interesse)/total*100)}%</td></tr>
      <tr><td>📵 Não atendeu</td><td>{len(nao_atendeu)}</td><td>{round(len(nao_atendeu)/total*100)}%</td></tr>
      <tr><td>📱 Caixa postal</td><td>{len(caixa_postal)}</td><td>{round(len(caixa_postal)/total*100)}%</td></tr>
      <tr><td>⏳ Em andamento</td><td>{len(em_andamento)}</td><td>{round(len(em_andamento)/total*100)}%</td></tr>
    </tbody>
  </table>
</body>
</html>"""
    return HTMLResponse(html)


async def dialer_status(request: Request):
    """Retorna status atual em JSON para atualização parcial da página."""
    rows_html = ""
    for c in CONTATOS_DIALER:
        status = CAMPAIGN_STATUS.get(c["numero"], "aguardando")
        if status == "aguardando":
            badge = '<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">⏳ Aguardando</span>'
        elif status == "discando":
            badge = '<span style="background:#1d4ed8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📞 Discando...</span>'
        elif status == "atendeu":
            badge = '<span style="background:#15803d;color:white;padding:3px 12px;border-radius:12px;font-size:13px">✅ Atendeu</span>'
        elif "qualificado" in status:
            badge = '<span style="background:#15803d;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🏆 Qualificado</span>'
        elif status == "caixa_postal":
            badge = '<span style="background:#78350f;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📱 Caixa postal</span>'
        elif status == "nao_atendeu":
            badge = '<span style="background:#92400e;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📵 Não atendeu</span>'
        elif status == "sem_interesse":
            badge = '<span style="background:#6b21a8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">👋 Sem interesse</span>'
        elif status.startswith("discando"):
            badge = f'<span style="background:#1d4ed8;color:white;padding:3px 12px;border-radius:12px;font-size:13px">📞 {status.capitalize()}</span>'
        elif status.startswith("esgotado"):
            badge = f'<span style="background:#4b5563;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🚫 {status.capitalize()}</span>'
        elif status.startswith("cooldown"):
            badge = f'<span style="background:#7c3aed;color:white;padding:3px 12px;border-radius:12px;font-size:13px">⏱ {status.capitalize()}</span>'
        elif "horário" in status:
            badge = f'<span style="background:#0369a1;color:white;padding:3px 12px;border-radius:12px;font-size:13px">🕘 {status.capitalize()}</span>'
        else:
            badge = f'<span style="background:#334155;color:#94a3b8;padding:3px 12px;border-radius:12px;font-size:13px">{status}</span>'

        rows_html += f'<tr><td style="font-weight:500">{c["nome"]}</td><td style="color:#64748b">{c["numero"]}</td><td>{badge}</td></tr>'

    if not rows_html:
        rows_html = '<tr><td colspan="3" style="text-align:center;color:#475569;padding:32px">Faça upload de um CSV para começar</td></tr>'

    return JSONResponse({
        "total": len(CONTATOS_DIALER),
        "atendidas": sum(1 for s in CAMPAIGN_STATUS.values() if "qualificado" in s),
        "ligando": ACTIVE_CALLS,
        "max_simult": CAMPAIGN_CONFIG["max_simultaneas"],
        "rows_html": rows_html,
    })


async def dialer_notifications(request: Request):
    """Retorna notificações pendentes e limpa a fila."""
    notifs = list(NOTIFICATIONS)
    NOTIFICATIONS.clear()
    return JSONResponse({"notifications": notifs})


async def dialer_config(request: Request):
    """Salva configurações da campanha."""
    from starlette.responses import RedirectResponse
    form = await request.form()
    try:
        CAMPAIGN_CONFIG["max_retries"] = int(form.get("max_retries", 3))
        CAMPAIGN_CONFIG["retry_interval"] = int(form.get("retry_interval", 120))
        CAMPAIGN_CONFIG["intervalo_chamadas"] = int(form.get("intervalo_chamadas", 8))
        CAMPAIGN_CONFIG["max_simultaneas"] = int(form.get("max_simultaneas", 3))
        CAMPAIGN_CONFIG["cooldown_dias"] = int(form.get("cooldown_dias", 7))
        CAMPAIGN_CONFIG["horario_inicio"] = form.get("horario_inicio", "09:00")
        CAMPAIGN_CONFIG["horario_fim"] = form.get("horario_fim", "20:00")
    except ValueError:
        pass
    return RedirectResponse("/dialer", status_code=303)


async def dialer_pause(request: Request):
    """Pausa ou retoma a campanha."""
    global CAMPAIGN_PAUSED
    from starlette.responses import RedirectResponse
    CAMPAIGN_PAUSED = not CAMPAIGN_PAUSED
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

    # Atualizar status no discador pelo nome (match parcial)
    nome_lower = nome.lower()
    for c in CONTATOS_DIALER:
        if nome_lower in c["nome"].lower() or c["nome"].lower() in nome_lower:
            if status == "interesse_confirmado":
                CAMPAIGN_STATUS[c["numero"]] = "qualificado ✅"
                # Adicionar notificação de lead quente
                NOTIFICATIONS.append({
                    "tipo": "qualificado",
                    "nome": nome,
                    "produto": produto,
                    "horario": body.get("horario_contato", ""),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                })
                print(f"[DIALER] {c['nome']} marcado como qualificado — não será chamado novamente")
            elif status == "sem_interesse":
                CAMPAIGN_STATUS[c["numero"]] = "sem_interesse"
                # Aplicar cooldown
                import time as _t
                dias = CAMPAIGN_CONFIG["cooldown_dias"]
                COOLDOWN_UNTIL[c["numero"]] = _t.time() + (dias * 86400)
                print(f"[DIALER] {c['nome']} em cooldown por {dias} dias")
            break

    # Disparar SMS + HubSpot se interesse confirmado
    sms_ok = False
    hubspot_ok = False
    if status == "interesse_confirmado" and produto:
        telefone_lead = "+5511991986241"
        for c in CONTATOS_DIALER:
            if nome_lower in c["nome"].lower() or c["nome"].lower() in nome_lower:
                telefone_lead = c["numero"]
                break
        sms_ok = enviar_sms(telefone_lead, nome, produto)
        print(f"[SMS] Enviado para {telefone_lead}: {sms_ok}")
        hubspot_ok = criar_lead_hubspot(nome, telefone_lead, produto, horario)
        print(f"[HUBSPOT] Lead criado: {hubspot_ok}")

    return JSONResponse({
        "sucesso": True,
        "mensagem": f"Lead {nome} registrado.",
        "sms_enviado": sms_ok,
        "hubspot": hubspot_ok if status == "interesse_confirmado" else "n/a"
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

    # Carregar estado salvo ao iniciar
    load_state()

    if transport == "sse":
        mcp._custom_starlette_routes = [
            Route("/sms", sms_endpoint, methods=["POST"]),
            Route("/lead", lead_endpoint, methods=["POST"]),
            Route("/dashboard", dashboard_endpoint, methods=["GET"]),
            Route("/dialer", dialer_endpoint, methods=["GET"]),
            Route("/dialer/start", dialer_start, methods=["GET"]),
            Route("/dialer/pause", dialer_pause, methods=["GET"]),
            Route("/dialer/config", dialer_config, methods=["POST"]),
            Route("/dialer/notifications", dialer_notifications, methods=["GET"]),
            Route("/dialer/status", dialer_status, methods=["GET"]),
            Route("/dialer/report", dialer_report, methods=["GET"]),
            Route("/dialer/webhook", dialer_webhook, methods=["POST"]),
            Route("/dialer/upload", dialer_upload, methods=["POST"]),
            Route("/dialer/paste", dialer_paste, methods=["POST"]),
        ]
        # Build the Starlette app and run with uvicorn on 0.0.0.0
        starlette_app = mcp.sse_app()
        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=8000)
    else:
        mcp.run(transport=transport)

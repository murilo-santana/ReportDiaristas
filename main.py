import os
import logging
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime
from pytz import timezone

# --- CONFIGURAÇÕES DE ESCALA ---
FUSO_HORARIO_SP = timezone('America/Sao_Paulo')

TURNO_PARA_IDS = {
    "Turno 1": ["1491699724", "1461929762", "1449480651", "9465967606", "1268695707"],
    "Turno 2": ["1458031670", "1298055860", "1281984509", "1432898616"],
    "Turno 3": ["1277449046", "1436962469", "9474534910", "9491699714", "1499919880"]
}

DIAS_DE_FOLGA = {
    "1491699724": [6], "1461929762": [5, 6], "1449480651": [5, 6], "9465967606": [5, 6], "1268695707": [6],
    "1458031670": [6, 0], "1298055860": [6], "1281984509": [6], "1432898616": [4, 5],
    "1277449046": [6, 0], "1436962469": [6, 0], "9474534910": [6, 0], "9491699714": [6], "1499919880": [6]
}

def definir_turno_por_horario_fim(horario_str):
    """Define o turno baseado no horário de término (T1, T2 ou T3)."""
    try:
        horario_fim = horario_str.split(' - ')[1].strip()
        h, m = map(int, horario_fim.split(':'))
        minutos_totais = h * 60 + m
        
        if 391 <= minutos_totais <= 810:   # 06:31 - 13:30
            return "Turno 1"
        elif 811 <= minutos_totais <= 1350: # 13:31 - 22:30
            return "Turno 2"
        else:                               # 22:31 - 06:30
            return "Turno 3"
    except:
        return None

def filtrar_responsaveis(turno, agora):
    ids_brutos = TURNO_PARA_IDS.get(turno, [])
    dia_semana = agora.weekday()
    return [uid for uid in ids_brutos if dia_semana not in DIAS_DE_FOLGA.get(uid, [])]

def enviar_reporte_seatalk(mensagem, ids_urgentes=[]):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url: return
    
    payload = {
        "tag": "text",
        "text": {
            "content": mensagem,
            "mentioned_list": ids_urgentes  # Marca APENAS os IDs de atraso
        }
    }
    requests.post(webhook_url, json=payload, timeout=10)

def automacao_dw_management():
    logging.info("Iniciando Robô com marcação seletiva (Atrasos)...")
    agora = datetime.now(FUSO_HORARIO_SP)
    email, senha = os.getenv("EMAIL_LOGIN"), os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)
            page.get_by_role("button", name="Login", exact=True).click()
            
            page.wait_for_timeout(5000)
            page.get_by_text("Controle de presença").last.click()
            page.wait_for_load_state("networkidle")

            total_producao, total_atraso = 0, 0
            blocos_atraso, blocos_producao = [], []
            ids_para_marcar = set() # Usaremos apenas para ATRASOS
            encontrou_finalizado = False

            while not encontrou_finalizado:
                page.wait_for_timeout(3000)
                linhas = page.locator("table tbody tr").all()
                
                for linha in linhas:
                    colunas = [td.inner_text().strip() for td in linha.locator("td").all()]
                    if len(colunas) < 12: continue

                    status = colunas[11]
                    if "Finalizado" in status:
                        encontrou_finalizado = True
                        break 

                    if "SOC" not in colunas[6] or "Operação" not in colunas[9]:
                        continue

                    horario_texto = colunas[8]
                    turno_da_tarefa = definir_turno_por_horario_fim(horario_texto)

                    if status == "Em atraso":
                        total_atraso += 1
                        blocos_atraso.append(f"🏢 BPO: {colunas[2]}\n📅 Data: {colunas[7]}\n⏱️ Horário: {horario_texto}")
                        # BUSCA RESPONSÁVEIS APENAS SE ESTIVER EM ATRASO
                        responsaveis = filtrar_responsaveis(turno_da_tarefa, agora)
                        ids_para_marcar.update(responsaveis)

                    elif status == "Em produção":
                        total_producao += 1
                        blocos_producao.append(f"📅 Data: {colunas[7]}\n⏱️ Horário: {horario_texto}\n🏢 BPO: {colunas[2]}")

                if encontrou_finalizado: break
                btn = page.locator("button[aria-label='Próxima']").first
                if btn.is_visible() and btn.is_enabled(): btn.click()
                else: break

            if total_atraso > 0 or total_producao > 0:
                header = f"📊 Relatório de pedidos DW em aberto\n\nAtrasos: {total_atraso} | Produção: {total_producao}\n\n"
                
                atrasos = ""
                if total_atraso > 0:
                    atrasos = "🚨 *URGENTE: PEDIDOS EM ATRASO*\n\n" + "\n\n".join(blocos_atraso) + "\n\n\n"

                producao = ""
                if total_producao > 0:
                    producao = "⚠️ *PEDIDOS EM PRODUÇÃO*\n\nLembrete, não se esqueça de finalizar essas tarefas.\n\n"
                    producao += "\n---------------------------------------\n".join(blocos_producao)
                
                # Envia a lista de IDs APENAS se houver atrasos
                enviar_reporte_seatalk(header + atrasos + producao, list(ids_para_marcar))

        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

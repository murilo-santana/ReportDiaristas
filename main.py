import os
import logging
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime
from pytz import timezone

# --- CONFIGURAÇÕES DE ESCALA E ALERTAS ---
FUSO_HORARIO_SP = timezone('America/Sao_Paulo')

# LIGA/DESLIGA: Altere para False para não receber alertas de tarefas "Em produção"
ATIVAR_ALERTA_PRODUCAO = False  # Para desligar, trocar o "True" por "False"

# Lista de IDs por Turno
TURNO_PARA_IDS = {
    "Turno 1": [
        "1508081817",  # Tiberio
        "1298480767",  # Barbara
        "9465967606",  # Fidel Lúcio
    ],
    "Turno 2": [
        "1386559133",  # Murilo Santana
        "1458031670",  # Beatriz
    ],
    "Turno 3": [
        "1193572348",  # Carlos
        "9382243574",  # João
        "9474534910",  # Kaio Baldo
    ]
}

# Configuração de Folgas (0=Segunda, 5=Sábado, 6=Domingo)
DIAS_DE_FOLGA = {
    # --- Turno 1 ---
    "1508081817": [],          # Tiberio (Não tem folga no script)
    "1298480767": [6, 0],      # Barbara (Domingo e Segunda)
    "9465967606": [5, 6],      # Fidel Lúcio (Sábado e Domingo)

    # --- Turno 2 ---
    "1386559133": [],          # Murilo Santana (Não tem folga no script)
    "1458031670": [6, 0],      # Beatriz (Domingo e Segunda)

    # --- Turno 3 ---
    "1193572348": [],          # Carlos (Não tem folga no script)
    "9382243574": [6, 0],      # João (Domingo e Segunda)
    "9474534910": [5, 6],      # Kaio Baldo (Sábado e Domingo)
}

def definir_turno_por_horario_fim(horario_str):
    """
    T1: 06:31 - 13:30 | T2: 13:31 - 22:30 | T3: 22:31 - 06:30
    """
    try:
        horario_fim = horario_str.split(' - ')[1].strip()
        h, m = map(int, horario_fim.split(':'))
        minutos_totais = h * 60 + m
        
        if 391 <= minutos_totais <= 810:   # T1
            return "Turno 1"
        elif 811 <= minutos_totais <= 1350: # T2
            return "Turno 2"
        else:                               # T3
            return "Turno 3"
    except:
        return None

def filtrar_responsaveis(turno, agora):
    """Retorna apenas os IDs do turno que não estão de folga hoje."""
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
            "mentioned_list": ids_urgentes
        }
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Erro no envio SeaTalk: {e}")

def automacao_dw_management():
    logging.info("Iniciando Robô SOC SP5 - Regras de Folga Atualizadas...")
    agora = datetime.now(FUSO_HORARIO_SP)
    email, senha = os.getenv("EMAIL_LOGIN"), os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            # Login e Navegação
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)
            page.get_by_role("button", name="Login", exact=True).click()
            
            page.wait_for_timeout(5000)
            page.get_by_text("Controle de presença").last.click()
            page.wait_for_load_state("networkidle")

            total_producao, total_atraso = 0, 0
            blocos_atraso, blocos_producao = [], []
            ids_para_marcar = set()
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
                        # Notificação sonora apenas para ATRASOS
                        responsaveis = filtrar_responsaveis(turno_da_tarefa, agora)
                        ids_para_marcar.update(responsaveis)

                    elif status == "Em produção":
                        total_producao += 1
                        blocos_producao.append(f"📅 Data: {colunas[7]}\n⏱️ Horário: {horario_texto}\n🏢 BPO: {colunas[2]}")

                if encontrou_finalizado: break
                btn = page.locator("button[aria-label='Próxima']").first
                if btn.is_visible() and btn.is_enabled(): btn.click()
                else: break

            # --- NOVA LÓGICA DE ENVIO APLICADA AQUI ---
            # Só continua se tiver atrasos, OU se tiver produção e o alerta não urgente estiver ativado
            if total_atraso > 0 or (total_producao > 0 and ATIVAR_ALERTA_PRODUCAO):
                
                # Monta os totais do cabeçalho dinamicamente
                totais = []
                if total_atraso > 0:
                    totais.append(f"Atrasos: {total_atraso}")
                if total_producao > 0 and ATIVAR_ALERTA_PRODUCAO:
                    totais.append(f"Produção: {total_producao}")
                
                header_info = " | ".join(totais)
                header = f"📊 Relatório de pedidos DW em aberto\n\n{header_info}\n\n"
                
                atrasos = ""
                if total_atraso > 0:
                    atrasos = "🚨 *URGENTE: PEDIDOS EM ATRASO*\n\n" + "\n\n".join(blocos_atraso) + "\n\n\n"

                producao = ""
                # Só adiciona o bloco de produção se o alerta estiver ativado
                if total_producao > 0 and ATIVAR_ALERTA_PRODUCAO:
                    producao = "⚠️ *PEDIDOS EM PRODUÇÃO*\n\nLembrete, não se esqueça de finalizar essas tarefas.\n\n"
                    producao += "\n---------------------------------------\n".join(blocos_producao)
                
                enviar_reporte_seatalk(header + atrasos + producao, list(ids_para_marcar))

        except Exception as e:
            logging.error(f"Erro na execução: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

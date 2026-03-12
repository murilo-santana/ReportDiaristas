import os
import logging
import requests
from playwright.sync_api import sync_playwright

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def enviar_reporte_seatalk(mensagem):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url: return
    payload = {"tag": "text", "text": {"content": mensagem}}
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Erro SeaTalk: {e}")

def automacao_dw_management():
    logging.info("Iniciando Robô com filtros rigorosos...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            # 1. Login e Navegação
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)
            page.get_by_role("button", name="Login", exact=True).click()
            
            page.wait_for_timeout(5000)
            page.get_by_text("Controle de presença").last.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

            # 2. Processamento de dados
            linhas = page.locator("table tbody tr").all()
            total_producao = 0
            total_atraso = 0
            blocos_atraso = []
            blocos_producao = []

            for linha in linhas:
                # Pegamos o texto de cada célula e limpamos espaços (strip)
                colunas = [td.inner_text().strip() for td in linha.locator("td").all()]
                
                if len(colunas) < 12: continue

                # Extração baseada nos índices confirmados
                bpo        = colunas[2]   # BPO
                tipo_op    = colunas[6]   # Tipo de operação
                data_trab  = colunas[7]   # Data de trabalho
                horario    = colunas[8]   # Horario
                area       = colunas[9]   # Area
                status     = colunas[11]  # Status

                # --- FILTROS RÍGIDOS ---
                # Só prossegue se for exatamente SOC e Operação
                if tipo_op != "SOC" or area != "Operação":
                    continue

                # --- FORMATAÇÃO POR STATUS ---
                # Usamos comparação exata para não pegar o texto de outros botões
                if status == "Em atraso":
                    total_atraso += 1
                    bloco = (f"🏢 BPO: {bpo}\n"
                             f"📅 Data: {data_trab}\n"
                             f"⏱️ Horário: {horario}")
                    blocos_atraso.append(bloco)
                
                elif status == "Em produção":
                    total_producao += 1
                    bloco = (f"📅 Data: {data_trab}\n"
                             f"⏱️ Horário: {horario}\n"
                             f"🏢 BPO: {bpo}")
                    blocos_producao.append(bloco)

            # 3. CONSTRUÇÃO DA MENSAGEM
            if total_atraso > 0 or total_producao > 0:
                msg_final = f"📊 Relatório de pedidos DW em aberto\n\nAtrasos: {total_atraso} | Produção: {total_producao}\n\n"
                
                if total_atraso > 0:
                    msg_final += "🚨 *URGENTE: PEDIDOS EM ATRASO*\n\n"
                    msg_final += "\n\n".join(blocos_atraso)
                    msg_final += "\n\n\n"

                if total_producao > 0:
                    msg_final += "⚠️ *PEDIDOS EM PRODUÇÃO*\n\n"
                    msg_final += "Lembrete, não se esqueça de finalizar essas tarefas.\n\n"
                    msg_final += "\n---------------------------------------\n".join(blocos_producao)
            else:
                msg_final = "✅ Relatório DW: Tudo em dia! Nenhum pedido SOC Operação pendente."

            enviar_reporte_seatalk(msg_final)
            logging.info(f"Reporte enviado. Produção: {total_producao}, Atrasos: {total_atraso}")

        except Exception as e:
            enviar_reporte_seatalk(f"❌ Erro: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

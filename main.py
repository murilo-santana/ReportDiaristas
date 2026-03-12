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
    logging.info("Ajustando layout final do reporte...")
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
            page.wait_for_timeout(2000)

            # 2. Processamento de dados
            linhas = page.locator("table tbody tr").all()
            total_producao = 0
            total_atraso = 0
            blocos_atraso = []
            blocos_producao = []

            for linha in linhas:
                colunas = linha.locator("td").all_text_contents()
                if len(colunas) < 12: continue

                bpo = colunas[2].strip()
                tipo_op = colunas[6].strip()
                data_trab = colunas[7].strip()
                horario = colunas[8].strip()
                area = colunas[9].strip()
                status = colunas[11].strip()

                if tipo_op != "SOC" or area != "Operação":
                    continue

                # --- FORMATAÇÃO PERSONALIZADA ---
                if "Em atraso" in status:
                    total_atraso += 1
                    # Atraso: BPO primeiro (Multiline)
                    bloco = (f"🏢 BPO: {bpo}\n"
                             f"📅 Data: {data_trab}\n"
                             f"⏱️ Horário: {horario}")
                    blocos_atraso.append(bloco)
                
                elif "Em produção" in status:
                    total_producao += 1
                    # Produção: Data/Horário primeiro e depois BPO
                    bloco = (f"📅 Data: {data_trab}\n"
                             f"⏱️ Horário: {horario}\n"
                             f"🏢 BPO: {bpo}")
                    blocos_producao.append(bloco)

            # 3. CONSTRUÇÃO DA MENSAGEM (EXATAMENTE COMO SOLICITADO)
            if total_atraso > 0 or total_producao > 0:
                msg_final = f"📊 Relatório de pedidos DW em aberto\n\nAtrasos: {total_atraso} | Produção: {total_producao}\n\n"
                
                # SEÇÃO URGENTE
                if total_atraso > 0:
                    msg_final += "🚨 *URGENTE: PEDIDOS EM ATRASO*\n\n"
                    msg_final += "\n\n".join(blocos_atraso)
                    msg_final += "\n\n\n" # Espaço maior entre seções

                # SEÇÃO PRODUÇÃO
                if total_producao > 0:
                    msg_final += "⚠️ *PEDIDOS EM PRODUÇÃO*\n\n"
                    msg_final += "Lembrete, não se esqueça de finalizar essas tarefas.\n\n"
                    # Separador tracejado específico para produção
                    msg_final += "\n---------------------------------------\n".join(blocos_producao)
            else:
                msg_final = "✅ Relatório DW: Tudo em dia! Nenhum pedido SOC Operação em aberto."

            enviar_reporte_seatalk(msg_final)
            logging.info("Reporte com layout final enviado.")

        except Exception as e:
            enviar_reporte_seatalk(f"❌ Erro de Layout: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

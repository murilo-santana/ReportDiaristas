import os
import logging
import requests
from playwright.sync_api import sync_playwright

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
    logging.info("Iniciando Robô com filtros e parada por 'Finalizado'...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

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

            total_producao = 0
            total_atraso = 0
            blocos_atraso = []
            blocos_producao = []
            encontrou_finalizado = False
            pagina_atual = 1

            while not encontrou_finalizado:
                logging.info(f"Lendo página {pagina_atual}...")
                page.wait_for_timeout(3000) 
                
                linhas = page.locator("table tbody tr").all()
                
                for linha in linhas:
                    # Extração rigorosa de texto de cada coluna
                    celulas = linha.locator("td").all()
                    colunas = [c.inner_text().strip() for c in celulas]
                    
                    if len(colunas) < 12: continue

                    status = colunas[11]

                    # --- REGRA DE PARADA (Deve ser a primeira coisa) ---
                    if "Finalizado" in status:
                        logging.info(f"Status 'Finalizado' detectado. Encerrando capturas.")
                        encontrou_finalizado = True
                        break 

                    # --- FILTROS DE SEGURANÇA ---
                    bpo = colunas[2]
                    tipo_op = colunas[6]
                    data_trab = colunas[7]
                    horario = colunas[8]
                    area = colunas[9]

                    # Filtro SOC e Operação (usando 'in' para evitar erro com espaços invisíveis)
                    if "SOC" not in tipo_op or "Operação" not in area:
                        continue

                    # --- SEPARAÇÃO POR STATUS ---
                    if "Em atraso" in status:
                        total_atraso += 1
                        blocos_atraso.append(f"🏢 BPO: {bpo}\n📅 Data: {data_trab}\n⏱️ Horário: {horario}")
                    
                    elif "Em produção" in status:
                        total_producao += 1
                        blocos_producao.append(f"📅 Data: {data_trab}\n⏱️ Horário: {horario}\n🏢 BPO: {bpo}")

                if encontrou_finalizado: break

                # Paginação
                botao_proximo = page.locator("button[aria-label='Próxima'], button:has([class*='chevron-right'])").first
                if botao_proximo.is_visible() and botao_proximo.is_enabled():
                    botao_proximo.click()
                    pagina_atual += 1
                else:
                    break

            # 3. CONSTRUÇÃO DA MENSAGEM
            if total_atraso > 0 or total_producao > 0:
                msg_final = f"📊 Relatório de pedidos DW em aberto\n\nAtrasos: {total_atraso} | Produção: {total_producao}\n\n"
                
                if total_atraso > 0:
                    msg_final += "🚨 *URGENTE: PEDIDOS EM ATRASO*\n\n"
                    msg_final += "\n\n".join(blocos_atraso)
                    msg_final += "\n\n\n"

                if total_producao > 0:
                    msg_final += "⚠️ *PEDIDOS EM PRODUÇÃO*\n\nLembrete, não se esqueça de finalizar essas tarefas.\n\n"
                    msg_final += "\n---------------------------------------\n".join(blocos_producao)
                
                enviar_reporte_seatalk(msg_final)
            else:
                logging.info("Nada pendente para reportar.")

        except Exception as e:
            enviar_reporte_seatalk(f"❌ Erro no Script: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

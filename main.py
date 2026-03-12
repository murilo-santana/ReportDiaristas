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
    logging.info("Iniciando Robô com Filtros de Operação...")
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

            # 2. Processamento com Filtros Específicos
            linhas = page.locator("table tbody tr").all()
            total_producao = 0
            total_atraso = 0
            blocos_mensagem = []

            for linha in linhas:
                colunas = linha.locator("td").all_text_contents()
                if len(colunas) < 12: continue

                # Captura de dados brutos
                bpo = colunas[2].strip()
                tipo_op = colunas[6].strip()
                data_trab = colunas[7].strip()
                horario = colunas[8].strip()
                area = colunas[9].strip()
                status = colunas[11].strip()

                # --- APLICAÇÃO DOS FILTROS ---
                # 1. Filtro de Tipo de Operação (Apenas SOC)
                if tipo_op != "SOC":
                    continue
                
                # 2. Filtro de Área (Apenas Operação)
                if area != "Operação":
                    continue

                # 3. Filtro de Status (Apenas "Em produção" ou "Em atraso")
                icone_status = ""
                if "Em atraso" in status:
                    icone_status = "🚨 *ALERTA MÁXIMO*"
                    total_atraso += 1
                elif "Em produção" in status:
                    icone_status = "⚠️ Lembrete"
                    total_producao += 1
                else:
                    continue # Descarta qualquer outro status

                # Montagem do bloco de texto (Tipo de Operação não entra no reporte)
                item = (f"{icone_status}\n"
                        f"🏢 *BPO:* {bpo} | *Área:* {area}\n"
                        f"📅 *Data:* {data_trab} | *Horário:* {horario}\n"
                        f"----------------------------------")
                
                # Prioriza os atrasos no topo da lista
                if "Em atraso" in status:
                    blocos_mensagem.insert(0, item)
                else:
                    blocos_mensagem.append(item)

            # 3. Construção do Reporte
            if total_atraso > 0 or total_producao > 0:
                header = f"📊 *Relatório de Status SOC*\n"
                resumo_counts = f"Atrasos: {total_atraso} | Produção: {total_producao}\n\n"
                corpo = "\n".join(blocos_mensagem[:8]) # Mostra até 8 registros
                
                msg_final = header + resumo_counts + corpo
                if len(blocos_mensagem) > 8:
                    msg_final += f"\n... e outros {len(blocos_mensagem) - 8} itens pendentes."
            else:
                msg_final = "✅ *Status:* Tudo limpo! Nenhum 'SOC - Operação' pendente no momento."

            enviar_reporte_seatalk(msg_final)
            logging.info("Reporte filtrado enviado.")

        except Exception as e:
            enviar_reporte_seatalk(f"❌ Erro nos filtros: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    automacao_dw_management()

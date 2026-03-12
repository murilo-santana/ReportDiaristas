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

    payload = {
        "tag": "text",
        "text": {"content": mensagem}
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
        logging.info("Reporte enviado ao SeaTalk.")
    except Exception as e:
        logging.error(f"Erro SeaTalk: {e}")

def fazer_login_e_navegar():
    logging.info("Iniciando Robô...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Realiza o Login
            logging.info("Acessando tela de login...")
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)
            page.get_by_role("button", name="Login", exact=True).click()

            # Aguarda a dashboard aparecer
            page.wait_for_timeout(5000)
            
            if "login" in page.url:
                logging.error("Falha ao passar da tela de login.")
                enviar_reporte_seatalk("❌ Erro: O robô não conseguiu passar da tela de login.")
                return

            # 2. Navega para Controle de Presença (O de baixo)
            logging.info("Clicando no segundo 'Controle de presença' no menu...")
            
            # .last() garante que ele pegue a última ocorrência encontrada na página
            # que é justamente o link dentro do grupo, como você mostrou na imagem.
            page.get_by_text("Controle de presença").last.click()

            # Aguarda a página de presença carregar
            page.wait_for_timeout(3000)
            
            logging.info(f"Página de presença acessada: {page.url}")
            enviar_reporte_seatalk(f"✅ Sucesso! O robô clicou no item correto.\n📍 Agora estou em: Controle de Presença")

        except Exception as e:
            msg_erro = f"❌ Erro na automação: {str(e)[:150]}"
            logging.error(msg_erro)
            enviar_reporte_seatalk(msg_erro)
        finally:
            browser.close()
            logging.info("Sessão encerrada.")

if __name__ == "__main__":
    fazer_login_e_navegar()

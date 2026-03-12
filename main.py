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
    if not webhook_url:
        return

    payload = {
        "tag": "text",
        "text": {"content": mensagem}
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
        logging.info("Reporte enviado ao SeaTalk.")
    except Exception as e:
        logging.error(f"Erro SeaTalk: {e}")

def fazer_login():
    logging.info("Iniciando Robô de Login...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("Acessando SPX DW Management...")
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)

            logging.info("Preenchendo credenciais...")
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)

            logging.info("Clicando no botão de Login (fundo amarelo)...")
            # get_by_role garante que é um botão
            # exact=True garante que ele ignore o "Faça login" do cabeçalho
            page.get_by_role("button", name="Login", exact=True).click()

            # Aguarda o processamento do login
            page.wait_for_timeout(5000)

            if "login" not in page.url:
                logging.info("Login efetuado com sucesso!")
                enviar_reporte_seatalk(f"✅ Login realizado com sucesso!\nURL: {page.url}")
            else:
                logging.warning("Login falhou ou a página não carregou a tempo.")
                enviar_reporte_seatalk("❌ Falha no login: O robô clicou, mas ainda estamos na tela de acesso.")

        except Exception as e:
            msg_erro = f"❌ Erro: {str(e)[:150]}"
            logging.error(msg_erro)
            enviar_reporte_seatalk(msg_erro)
        finally:
            browser.close()
            logging.info("Sessão encerrada.")

if __name__ == "__main__":
    fazer_login()

import os
import logging
import requests
from playwright.sync_api import sync_playwright

# Configuração de Logs para o console do GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def enviar_reporte_seatalk(mensagem):
    """Envia a mensagem para o SeaTalk usando o padrão de tag:text."""
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logging.error("WEBHOOK_URL não encontrada nos Secrets.")
        return

    payload = {
        "tag": "text",
        "text": {"content": mensagem}
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info(f"Relatório enviado ao SeaTalk: {mensagem}")
        else:
            logging.error(f"Erro no SeaTalk: {response.status_code}")
    except Exception as e:
        logging.error(f"Falha ao conectar no SeaTalk: {e}")

def fazer_login():
    logging.info("Iniciando Robô de Login...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    if not email or not senha:
        logging.error("EMAIL_LOGIN ou SENHA_LOGIN não configurados.")
        return

    with sync_playwright() as p:
        # headless=True é obrigatório para rodar no servidor do GitHub
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("Acessando SPX DW Management...")
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)

            logging.info("Preenchendo credenciais...")
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)

            logging.info("Clicando no botão de entrar...")
            page.locator("button.filament-button").click()

            # Espera 5 segundos para a página carregar após o login
            page.wait_for_timeout(5000)

            # Verifica se o login teve sucesso (se a URL mudou)
            if "login" not in page.url:
                enviar_reporte_seatalk(f"✅ Login realizado com sucesso!\nURL: {page.url}")
                logging.info("Login efetuado com sucesso.")
            else:
                enviar_reporte_seatalk("❌ Falha no login: A página permaneceu na tela de acesso.")
                logging.warning("Falha no login.")

        except Exception as e:
            msg_erro = f"❌ Erro na execução: {str(e)[:150]}"
            logging.error(msg_erro)
            enviar_reporte_seatalk(msg_erro)
        finally:
            browser.close()
            logging.info("Navegador fechado.")

if __name__ == "__main__":
    fazer_login()

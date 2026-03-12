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
    """Envia reporte no padrão SeaTalk do grupo."""
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
            logging.info(f"Reporte SeaTalk enviado: {mensagem}")
    except Exception as e:
        logging.error(f"Erro ao conectar no SeaTalk: {e}")

def fazer_login():
    logging.info("Iniciando Robô de Login...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    if not email or not senha:
        logging.error("Credenciais ausentes.")
        return

    with sync_playwright() as p:
        # headless=True é obrigatório para o GitHub Actions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("Acessando SPX DW Management...")
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)

            logging.info("Preenchendo credenciais...")
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)

            logging.info("Clicando no botão de Login usando o XPath fornecido...")
            # Usando o XPath exato que você extraiu do HTML
            xpath_botao = "/html[1]/body[1]/div[1]/div[1]/main[1]/div[1]/section[1]/form[1]/div[2]/div[1]/button[1]"
            page.locator(xpath_botao).click()

            # Aguarda o processamento do login
            page.wait_for_timeout(5000)

            # Validação de sucesso
            if "login" not in page.url:
                logging.info("Login efetuado com sucesso.")
                enviar_reporte_seatalk(f"✅ Login realizado com sucesso no DW!\nURL Atual: {page.url}")
            else:
                logging.warning("O login parece ter falhado (ainda na tela de login).")
                enviar_reporte_seatalk("❌ Falha no login: O sistema não avançou após o clique.")

        except Exception as e:
            msg_erro = f"❌ Erro na automação: {str(e)[:150]}"
            logging.error(msg_erro)
            enviar_reporte_seatalk(msg_erro)
        finally:
            browser.close()
            logging.info("Sessão encerrada.")

if __name__ == "__main__":
    fazer_login()

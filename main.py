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
    if not webhook_url:
        return

    payload = {
        "tag": "text",
        "text": {"content": mensagem}
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Erro SeaTalk: {e}")

def fazer_login():
    logging.info("Iniciando Robô...")
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            page.locator("[id='data.email']").fill(email)
            page.locator("[id='data.password']").fill(senha)
            page.locator("button.filament-button").click()

            page.wait_for_timeout(5000)
            enviar_reporte_seatalk(f"✅ Login realizado! URL atual: {page.url}")

        except Exception as e:
            enviar_reporte_seatalk(f"❌ Erro: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    fazer_login()

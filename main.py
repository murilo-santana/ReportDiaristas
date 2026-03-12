import os
import logging
import requests
from playwright.sync_api import sync_playwright

# Configuração de logs para o console do GitHub
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def enviar_reporte_seatalk(mensagem):
    """Envia mensagem seguindo o padrão exato do seu script SeaTalk funcional."""
    webhook_url = os.getenv("WEBHOOK_URL")
    
    if not webhook_url:
        logging.error("WEBHOOK_URL não configurada nos Secrets.")
        return

    # Estrutura exata da sua imagem: {"tag": "text", "text": {"content": "..."}}
    payload = {
        "tag": "text",
        "text": {
            "content": mensagem
        }
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logging.info(f"Reporte enviado: {mensagem}")
        else:
            logging.error(f"Falha SeaTalk: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao conectar com SeaTalk: {e}")

def fazer_login():
    logging.info("Iniciando Robô de Login...")
    
    email = os.getenv("EMAIL_LOGIN")
    senha = os.getenv("SENHA_LOGIN")

    if not email or not senha:
        msg = "⚠️ Falha: Credenciais EMAIL_LOGIN ou SENHA_LOGIN não encontradas."
        logging.error(msg)
        enviar_reporte_seatalk(msg)
        return

    with sync_playwright() as p:
        # headless=True é obrigatório para o GitHub Actions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("Acessando SPX DW Management...")
            page.goto("https://dwmanagement.spx.com.br/admin/login", timeout=60000)
            
            logging.info("Preenchendo e-mail...")
            page.locator("[id='data.email']").fill(email)
            
            logging.info("Preenchendo senha...")
            page.locator("[id='data.password']").fill(senha)
            
            logging.info("Clicando no botão de login...")
            # Usando a classe filament-button que vimos no seu HTML
            page.locator("button.filament-button").click()

            # Espera 5 segundos para a dashboard carregar
            page.wait_for_timeout(5000)
            
            # Validação simples: se a URL mudar ou não houver erro, logou
            url_atual = page.url
            logging.info(f"URL após tentativa de login: {url_atual}")
            
            enviar_reporte_seatalk(f"✅ Robô Logado com Sucesso!\nURL Atual: {url_atual}")

        except Exception as e:
            msg_erro = f"❌ Erro na Automação: {str(e)[:150]}"
            logging.error(msg_erro)
            enviar_reporte_seatalk(msg_erro)
            
        finally:
            browser.close()
            logging.info("Navegador fechado.")

if __name__ == "__main__":
    fazer_login()

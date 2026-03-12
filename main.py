import os
import logging
import requests
from playwright.sync_api import sync_playwright

# Configuração do sistema de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def enviar_mensagem_webhook(mensagem):
    """Envia uma notificação para o Webhook configurado."""
    url = os.getenv("WEBHOOK_URL")
    
    if not url:
        logging.warning("URL do Webhook não configurada. A mensagem não será enviada.")
        return

    dados = {"text": mensagem}

    try:
        resposta = requests.post(url, json=dados)
        if 200 <= resposta.status_code < 300:
            logging.info("Mensagem enviada para o webhook com sucesso!")
        else:
            logging.error(f"Falha ao enviar mensagem para o webhook. Código: {resposta.status_code}")
    except Exception as e:
        logging.error(f"Erro ao tentar conectar com o webhook: {e}")

def fazer_login():
    logging.info("Iniciando o script de automação.")
    
    # Puxando as credenciais protegidas
    meu_email = os.getenv("EMAIL_LOGIN")
    minha_senha = os.getenv("SENHA_LOGIN")

    if not meu_email or not minha_senha:
        mensagem_erro = "As credenciais não foram encontradas nas variáveis de ambiente."
        logging.error(mensagem_erro)
        enviar_mensagem_webhook(f"⚠️ Alerta: {mensagem_erro}")
        return

    with sync_playwright() as p:
        logging.info("Iniciando o navegador Chromium (modo headless).")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            url = "https://dwmanagement.spx.com.br/admin/login"
            logging.info(f"Acessando a URL: {url}")
            page.goto(url)
            
            logging.info("Preenchendo e-mail...")
            page.locator("[id='data.email']").fill(meu_email)
            
            logging.info("Preenchendo senha...")
            page.locator("[id='data.password']").fill(minha_senha)
            
            logging.info("Clicando no botão de Login...")
            page.locator('button:has-text("Login")').click()

            logging.info("Aguardando carregamento da página pós-login...")
            page.wait_for_timeout(5000) 
            
            logging.info("Processo de login finalizado!")
            enviar_mensagem_webhook("✅ Automação finalizada: Login realizado com sucesso no DW Management!")

        except Exception as e:
            erro_msg = f"Ocorreu um erro inesperado durante a execução: {e}"
            logging.error(erro_msg)
            enviar_mensagem_webhook(f"❌ Erro na automação: Falha ao executar o script. Detalhe: {e}")
            
        finally:
            logging.info("Fechando o navegador.")
            browser.close()

if __name__ == "__main__":
    fazer_login()

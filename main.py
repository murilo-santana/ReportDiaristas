import os
import logging
from playwright.sync_api import sync_playwright

# Configuração do sistema de logs (formato: DATA HORA - NÍVEL - MENSAGEM)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def fazer_login():
    logging.info("Iniciando o script de automação.")
    
    # Puxando as credenciais protegidas das variáveis de ambiente
    meu_email = os.getenv("EMAIL_LOGIN")
    minha_senha = os.getenv("SENHA_LOGIN")

    if not meu_email or not minha_senha:
        logging.error("As credenciais não foram encontradas. Verifique os GitHub Secrets.")
        return

    with sync_playwright() as p:
        logging.info("Iniciando o navegador Chromium (modo headless).")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            url = "https://dwmanagement.spx.com.br/admin/login"
            logging.info(f"Acessando a URL: {url}")
            page.goto(url)
            logging.info("Página de login carregada.")

            logging.info("Localizando o campo de e-mail e inserindo dados...")
            page.locator("[id='data.email']").fill(meu_email)
            logging.info("E-mail preenchido com sucesso.")

            logging.info("Localizando o campo de senha e inserindo dados...")
            page.locator("[id='data.password']").fill(minha_senha)
            logging.info("Senha preenchida com sucesso.")

            logging.info("Procurando o botão de Login e clicando...")
            page.locator('button:has-text("Login")').click()
            logging.info("Clique no botão 'Login' realizado.")

            # Pausa para garantir que a página de destino carregue após o clique
            logging.info("Aguardando 5 segundos para o processamento do login...")
            page.wait_for_timeout(5000) 
            
            logging.info("Processo de login finalizado sem erros críticos!")

        except Exception as e:
            logging.error(f"Ocorreu um erro inesperado durante a execução: {e}")
            
        finally:
            logging.info("Fechando o navegador e encerrando a sessão do Playwright.")
            browser.close()
            logging.info("Script encerrado.")

if __name__ == "__main__":
    fazer_login()

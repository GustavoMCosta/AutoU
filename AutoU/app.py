import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import pdfplumber

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configura a API do Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("A chave da API do Google não foi encontrada. Verifique seu arquivo .env.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# Inicializa o Flask
app = Flask(__name__)

def process_email_content(email_content):
    """
    Função que processa o conteúdo do e-mail com a API do Gemini.
    Retorna a categoria e a resposta sugerida.
    """
    prompt = f"""

    Esses emails podem ser mensagens solicitando um status atual sobre uma requisição em andamento, 
    compartilhando algum arquivo ou até mesmo mensagens improdutivas, como desejo de feliz natal ou perguntas não relevantes. 

    Nosso objetivo é automatizar a leitura e classificação desses emails e sugerir classificações e respostas automáticas de acordo com o teor de cada email recebido, 
    liberando tempo da equipe para que não seja mais necessário ter uma pessoa fazendo esse trabalho manualmente.

    Objetivo Simplificado
    Classificar emails em categorias predefinidas.
    Sugerir respostas automáticas baseadas na classificação realizada.

    Categorias de Classificação
    Produtivo: Emails que requerem uma ação ou resposta específica (ex.: solicitações de suporte técnico, atualização sobre casos em aberto, dúvidas sobre o sistema).
    Improdutivo: Emails que não necessitam de uma ação imediata (ex.: mensagens de felicitações, agradecimentos).
    
    Siga o seguinte formato para a resposta. Não inclua mais nada além do formato:
    CATEGORIA: [Categoria do e-mail]
    RESPOSTA_SUGERIDA: [Resposta automática adequada para a categoria]
    ---
    E-mail para análise:
    "{email_content}"
    """

    try:
        response = model.generate_content(prompt)
        text_result = response.text
        
        # Extrai a categoria e a resposta do texto gerado
        lines = text_result.strip().split('\n')
        category = lines[0].replace('CATEGORIA: ', '').strip()
        suggested_response = lines[1].replace('RESPOSTA_SUGERIDA: ', '').strip()
        
        return category, suggested_response

    except Exception as e:
        print(f"Erro ao processar a requisição: {e}")
        return "Erro", "Não foi possível processar a sua solicitação. Tente novamente mais tarde."


@app.route('/')
def index():
    """
    Renderiza a página inicial.
    """
    return render_template('index.html')

@app.route('/processar', methods=['POST'])
def processar():
    """
    Recebe os dados do formulário (texto ou arquivo) e processa com o Gemini.
    """
    # Verifica se foi enviado um arquivo
    if 'email_file' in request.files and request.files['email_file'].filename != '':
        email_file = request.files['email_file']
        file_extension = os.path.splitext(email_file.filename)[1].lower()
        
        email_content = ""
        
        if file_extension == '.txt':
            email_content = email_file.read().decode('utf-8')
        elif file_extension == '.pdf':
            try:
                # Usa pdfplumber para extrair texto de PDFs
                with pdfplumber.open(email_file) as pdf:
                    for page in pdf.pages:
                        email_content += page.extract_text() or ""
            except Exception as e:
                return render_template('index.html', error=f"Erro ao ler o arquivo PDF: {e}")
        else:
            return render_template('index.html', error="Formato de arquivo não suportado. Use .txt ou .pdf.")

    # Se não houver arquivo, verifica se há texto direto
    elif 'email_text' in request.form and request.form['email_text'] != '':
        email_content = request.form['email_text']
    
    else:
        return render_template('index.html', error="Por favor, insira o texto ou faça o upload de um arquivo.")

    # Processa o conteúdo do e-mail com a função
    category, suggested_response = process_email_content(email_content)

    # Renderiza a página com os resultados
    return render_template('index.html', 
                           category=category, 
                           suggested_response=suggested_response)

if __name__ == '__main__':
    # Em produção, use um servidor como Gunicorn. Para desenvolvimento:
    app.run(debug=True)
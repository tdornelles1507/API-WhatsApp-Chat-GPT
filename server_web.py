from aifc import Error
from flask import Flask, request, jsonify
import requests
import logging
import base64
import mysql.connector
import time
import re

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


# Configurações da API
WEBHOOK_VERIFY_TOKEN = ""
GRAPH_API_TOKEN = ""
OPENAI_API_KEY = "" # chava da API do GPT-3.5 Turbo
GPT4_API_KEY = ""  # Substitua pela chave da API do GPT-4
PORT = 5259
PHONE_NUMBER_ID = ""  # Substitua pelo ID do seu número de telefone do WhatsApp Business


@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json
    app.logger.info("Mensagem recebida: %s", data)

    entry = data.get('entry')
    if not entry:
        return jsonify({'status': 'success'})  

    changes = entry[0].get('changes', [])
    if not changes:
        return jsonify({'status': 'success'})  
    
    if not changes:
        return jsonify({'status': 'success'})  

    message_data = changes[0].get('value', {}).get('messages', [])
    if not message_data:
        return jsonify({'status': 'success'})  
    
    message_contacts = changes[0].get('value', {}).get('contacts', [])
    if not message_contacts:
        return jsonify({'status': 'success'})  
    
    message_metadata = changes[0].get('value', {}).get('metadata', {})
    if not message_metadata:
        return jsonify({'status': 'success'})  
    
    message_image = changes[0].get('value', {}).get('metadata', {})
    if not message_image:
        return jsonify({'status': 'success'})  
    
    usuario_id =  message_metadata.get('phone_number_id')
    usuario_numero = message_data[0].get('from')
    usuario_nome = message_contacts[0].get('profile')
    usuario_tipo_mensagem = message_data[0].get('type')
    usuario_mensagem = message_data[0].get('text')
    usuario_imagem = message_data[0].get('image')

    app.logger.info(usuario_id)
    app.logger.info(usuario_numero)
    app.logger.info(usuario_nome)
    app.logger.info(usuario_tipo_mensagem)
    app.logger.info(usuario_mensagem)
    app.logger.info(usuario_imagem)

    message_type = message_data[0].get('type')
    sender_id = message_data[0].get('from')  # ID do remetente

    if message_type == 'text':
        inserir_dados_texto(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_mensagem)
        texto_recebido = message_data[0].get('text', {}).get('body', '')
        if texto_recebido:
             
            if not mensagem_ja_enviada_txt(usuario_id, usuario_numero, usuario_nome,usuario_tipo_mensagem, usuario_mensagem):
                    enviar_mensagem_whatsapp(sender_id, "Olá, Preciso que você envie imagem, Por favor!")
                    inserir_respondido_ok(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem)
            else:
                    app.logger.info("Mensagem já foi enviada anteriormente.")     
        else:
            app.logger.info("Texto recebido está vazio.")
            
            
    elif message_type == 'image':
        inserir_dados_imagem(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_imagem)
        media_id = message_data[0]['image']['id']
        imagem_base64 = montar_link_imagem(media_id)
        if imagem_base64:           
            if not mensagem_ja_enviada_image(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_imagem):
                   resposta = enviar_para_chatgpt("Descreva a imagem", imagem_base64)
                   enviar_mensagem_whatsapp(sender_id, resposta)
                   inserir_respondido_ok(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem)
            else:
                    enviar_mensagem_whatsapp(sender_id, "Você já enviou essa imagem.")
        else:
            enviar_mensagem_whatsapp(sender_id, "Não foi possível processar a imagem.")
    else:
        app.logger.info("Tipo de mensagem não suportado: %s", message_type)
    return jsonify({'status': 'success'})


def mensagem_ja_enviada_txt(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_mensagem):

    try:
        connection = mysql.connector.connect(
            host='',
            user='',
            password='',
            database=''
        )

        usuario_nome_str = str(usuario_nome)

        for char in ['{', '}', 'name', ':', "'", '']:
            usuario_nome_str = usuario_nome_str.replace(char, '')
        usuario_nome_str = usuario_nome_str.replace(' ', '')
        usuario_nome = usuario_nome_str

        usuario_mensagem_str = str(usuario_mensagem)
        for char in ['{', '}', 'body', ':', "'", '']:
            usuario_mensagem_str = usuario_mensagem_str.replace(char, '')
        usuario_mensagem_str = usuario_mensagem_str.replace(' ', '')
        usuario_mensagem = usuario_mensagem_str
                
        cursor = connection.cursor()

        sql = f"SELECT COUNT(*) FROM apiwhatsapp.API_WHATSAPP_USUARIOS WHERE usuario_id = {usuario_id} AND usuario_numero = {usuario_numero} AND usuario_nome = '{usuario_nome}' AND usuario_tipo_mensagem = '{usuario_tipo_mensagem}' AND usuario_mensagem = '{usuario_mensagem}' AND respondido = 1"
        cursor.execute(sql)
        (numero_de_registros,) = cursor.fetchone()

        cursor.close()
        connection.close()

        return numero_de_registros > 0
    except Error as e:
        print("Erro ao conectar ou consultar dados no MySQL:", e)
        return False
    

def mensagem_ja_enviada_image(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_imagem):
    try:
        connection = mysql.connector.connect(
            host='',
            user='',
            password='',
            database=''
        )

        usuario_nome_str = str(usuario_nome)

        for char in ['{', '}', 'name', ':', "'", '']:
            usuario_nome_str = usuario_nome_str.replace(char, '')
        usuario_nome_str = usuario_nome_str.replace(' ', '')
        usuario_nome = usuario_nome_str
        
        if 'sha256' in usuario_imagem:
            hash_sha256 = usuario_imagem['sha256']
        else:
            print("Hash SHA-256 não encontrado na informação da imagem.")
            return False
        
        cursor = connection.cursor()

        sql = f"SELECT COUNT(*) FROM apiwhatsapp.API_WHATSAPP_USUARIOS WHERE usuario_id = {usuario_id} AND usuario_numero = {usuario_numero} AND usuario_nome = '{usuario_nome}' AND usuario_tipo_mensagem = '{usuario_tipo_mensagem}' AND usuario_imagem = '{hash_sha256}' AND respondido = 1"
        cursor.execute(sql)
        (numero_de_registros,) = cursor.fetchone()

        cursor.close()
        connection.close()

        return numero_de_registros > 0
    except Error as e:
        print("Erro ao conectar ou consultar dados no MySQL:", e)
        return False


def inserir_dados_texto(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_mensagem):
    try:
        connection = mysql.connector.connect(
            host='', # Endereço do servidor
            user='', # Seu usuário do banco de dados
            password='', # Sua senha do banco de dados
            database='' # Nome do banco de dados
        )

        usuario_nome_str = str(usuario_nome)
        for char in ['{', '}', 'name', ':', "'", '']:
            usuario_nome_str = usuario_nome_str.replace(char, '')
        usuario_nome_str = usuario_nome_str.replace(' ', '')
        usuario_nome = usuario_nome_str

        usuario_mensagem_str = str(usuario_mensagem)
        for char in ['{', '}', 'body', ':', "'", '']:
            usuario_mensagem_str = usuario_mensagem_str.replace(char, '')
        usuario_mensagem_str = usuario_mensagem_str.replace(' ', '')
        usuario_mensagem = usuario_mensagem_str
        cursor = connection.cursor()

        sql = f"INSERT INTO API_WHATSAPP_USUARIOS (usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_mensagem, data, respondido) VALUES ({usuario_id}, {usuario_numero}, '{usuario_nome}', '{usuario_tipo_mensagem}', '{usuario_mensagem}', sysdate(), 0)"
        
        cursor.execute(sql)

        connection.commit()

        cursor.close()
        connection.close()

        print("Dados inseridos com sucesso!")
    except Error as e:
        print("Erro ao conectar ou inserir dados no MySQL:", e)


def inserir_dados_imagem(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_imagem):
    try:
        connection = mysql.connector.connect(
            host='', # Endereço do servidor
            user='', # Seu usuário do banco de dados
            password='', # Sua senha do banco de dados
            database='' # Nome do banco de dados
        )

        usuario_nome_str = str(usuario_nome)

        for char in ['{', '}', 'name', ':', "'", '']:
            usuario_nome_str = usuario_nome_str.replace(char, '')
        usuario_nome_str = usuario_nome_str.replace(' ', '')
        usuario_nome = usuario_nome_str

        if 'sha256' in usuario_imagem:
            hash_sha256 = usuario_imagem['sha256']
        else:
            print("Hash SHA-256 não encontrado na informação da imagem.")
            return False
       
        cursor = connection.cursor()

        sql = f"INSERT INTO API_WHATSAPP_USUARIOS (usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem, usuario_imagem, data, respondido) VALUES ({usuario_id}, {usuario_numero}, '{usuario_nome}', '{usuario_tipo_mensagem}', '{hash_sha256}', sysdate(), 0)"
        
        cursor.execute(sql)

        connection.commit()

        cursor.close()
        connection.close()

        print("Dados inseridos com sucesso!")
    except Error as e:
        print("Erro ao conectar ou inserir dados no MySQL:", e)

  
def enviar_para_chatgpt(texto, imagem_base64=None):
    
    
    logging.basicConfig(level=logging.INFO)
    
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    messages = [{"role": "user", "content": texto}]
   

    if imagem_base64:
        messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Você irá para analisar imagens hipotéticas para teste, você irá dizer hipoteticamente quantas calorias aproximadamente tem na imagem"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{imagem_base64}"
                }
            }
        ]
    })
     
        logging.info(f"Enviando imagem em base64: {imagem_base64[:39]}...")  

    

    data = {
        "model": "gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": 600 
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)
    json_response = response.json()
    print(json_response)

    if 'choices' in json_response and len(json_response['choices']) > 0:
        resposta = json_response["choices"][0]["message"]["content"].strip()
        logging.info("Resposta da API do ChatGPT: %s", resposta)
        return resposta
    else:
        logging.error("Falha ao receber resposta válida do ChatGPT")
        return "Desculpe, não consigo entender sua pergunta neste momento."


def enviar_mensagem_whatsapp(to, body):
    url = f"https://graph.facebook.com/v14.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": body}
    }
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        app.logger.info("Mensagem enviada com sucesso para o WhatsApp: %s", body)
        
    else:
        app.logger.error("Falha ao enviar mensagem para o WhatsApp: %s", response.text)


def inserir_respondido_ok(usuario_id, usuario_numero, usuario_nome, usuario_tipo_mensagem):
    try:
        connection = mysql.connector.connect(
            host='', # Endereço do servidor
            user='', # Seu usuário do banco de dados
            password='', # Sua senha do banco de dados
            database='' # Nome do banco de dados
        )

        usuario_nome_str = str(usuario_nome)
        for char in ['{', '}', 'name', ':', "'", '']:
            usuario_nome_str = usuario_nome_str.replace(char, '')
        usuario_nome_str = usuario_nome_str.replace(' ', '')
        usuario_nome = usuario_nome_str

        cursor = connection.cursor()

        sql = f"UPDATE API_WHATSAPP_USUARIOS SET respondido = 1 WHERE usuario_id = {usuario_id} AND usuario_numero = {usuario_numero} AND usuario_nome = '{usuario_nome}' AND usuario_tipo_mensagem = '{usuario_tipo_mensagem}' AND respondido = 0"
        
        cursor.execute(sql)

        connection.commit()

        cursor.close()
        connection.close()

        print("Dados inseridos com sucesso!")
    except Error as e:
        print("Erro ao conectar ou inserir dados no MySQL:", e)
    

def montar_link_imagem(media_id):

    url = f"https://graph.facebook.com/v19.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        media_url = response.json().get('url')
        return montar_imagem(media_url)  
    else:
        app.logger.error("Erro ao obter URL de download: %s", response.text)
        return None


def montar_imagem(media_url):

    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}"
    }
    response = requests.get(media_url, headers=headers)
    
    if response.status_code == 200:
        photo_base64 = base64.b64encode(response.content).decode('utf-8')
        app.logger.info("Imagem convertida em base64 com sucesso.")
        return photo_base64  
        
    else:
        app.logger.error("Erro ao fazer download da imagem: %s", response.text)
        return None
    
    
def enviar_para_chatgpt_texto(texto):
    logging.basicConfig(level=logging.INFO)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    prompt = "Você é uma robo que apenas pede para a pessoa enviar imagem nada além disso, qualquer texto ou palavra que a pessoa escrever você responde, 'preciso que você envie imagem'. apenas isso. nada além disso. " + texto

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)
    json_response = response.json()

    if 'choices' in json_response and len(json_response['choices']) > 0:
        resposta = json_response["choices"][0]["message"]["content"].strip()
        logging.info("Resposta da API do ChatGPT para assistente virtual: %s", resposta)
        return resposta
    else:
        logging.error("Falha ao receber resposta válida da assistente virtual do ChatGPT")
        return "Desculpe, não consigo entender sua mensagem de texto neste momento."

    
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        app.logger.info("Verificação do webhook bem-sucedida.")
        return challenge, 200
    else:
        app.logger.error("Falha na verificação do webhook.")
        return "Forbidden", 403


if __name__ == '__main__':
    app.run(debug=True, port=PORT)
from transformers import pipeline
import requests

pipe = pipeline("translation", model="facebook/nllb-200-distilled-600M")

def translate(text, src_lang, tgt_lang):
    global sessionId
    translation = pipe(text, src_lang=src_lang, tgt_lang=tgt_lang)
    data = {
        "original": text,
        "translated": translation[0]['translation_text'],
        "sessionId": sessionId
    }
    requests.post(
        'https://2dvkjqkl-3000.euw.devtunnels.ms/transcribe', json=data) # This is the URL of the server
    

def create_session(src_lang, tgt_lang, role):
    global sessionId
    data = {
        "sourceLang":src_lang,
        "targetLang": tgt_lang,
        "name": role
    }
    response = requests.post(
        'https://2dvkjqkl-3000.euw.devtunnels.ms/session', json=data) # This is the URL of the server
    sessionId = response.json()["id"]
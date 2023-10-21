from transformers import pipeline
import requests

pipe = pipeline("translation", model="facebook/nllb-200-distilled-600M")

def translate(text, src_lang, tgt_lang):
    translation = pipe(text, src_lang=src_lang, tgt_lang=tgt_lang)
    data = {
        "original": text,
        "translated": translation[0]['translation_text']
    }
    print(data)
    requests.post(
        'https://2dvkjqkl-3000.euw.devtunnels.ms/transcribe', json=data)
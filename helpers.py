import io
import os
import speech_recognition as sr
import whisper
import torch
import requests
from languages import lang_codes
from translate import translate

from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from time import sleep
from sys import platform


def setup_recorder():
    recorder = sr.Recognizer()
    recorder.energy_threshold = 1000
    recorder.dynamic_energy_threshold = False

    source = sr.Microphone(sample_rate=16000)
    with source:
        recorder.adjust_for_ambient_noise(source)
    return recorder, source


def toggle_listening_state(recorder, source, record_callback, record_timeout, data_queue, isSessionUp):
    global stop_listening
    if isSessionUp.get():
        # If the session is up, we want to start listening
        stop_listening = recorder.listen_in_background(
            source, record_callback(data_queue), phrase_time_limit=record_timeout)
    else:
        # If the session is not up, we want to stop listening
        if stop_listening:
            stop_listening()


def record_callback(data_queue):
    def wrapper(_, audio: sr.AudioData) -> None:
        """
        Threaded callback function to receive audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)
    return wrapper


def prepare_model(source, enable_start_button, data_queue, src_lang_var, dest_lang_var):

    phrase_time = None
    last_sample = bytes()

    audio_model = whisper.load_model("large")

    url = "http://127.0.0.1:5000/translate"
    headers = {"Content-Type": "application/json"}

    phrase_timeout = 3

    temp_file = NamedTemporaryFile().name
    transcription = ['']

    print("Model loaded.\n")

    enable_start_button()

    while True:
        try:
            now = datetime.utcnow()
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Concatenate our current audio data with the latest audio data.
                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data

                # Use AudioData to convert the raw data to wav data.
                audio_data = sr.AudioData(
                    last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                wav_data = io.BytesIO(audio_data.get_wav_data())

                # Write wav data to the temporary file as bytes.
                with open(temp_file, 'w+b') as f:
                    f.write(wav_data.read())

                # Set the language to the source language.
                language = src_lang_var.get()

                # Read the transcription.
                result = audio_model.transcribe(
                    temp_file, language=language, fp16=torch.cuda.is_available())
                text = result['text'].strip()
                translate(text, lang_codes[language],
                          lang_codes[dest_lang_var.get()])

                # If we detected a pause between recordings, add a new item to our transcription.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text

                # Infinite loops are bad for processors, must sleep.
                sleep(0.1)
        except KeyboardInterrupt:
            break

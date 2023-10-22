import tkinter as tk
import socketio


from tkinter import messagebox
from threading import Thread
from queue import Queue

from helpers import prepare_model, record_callback, setup_recorder, toggle_listening_state
import os

from translate import create_session
from roles import roles
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def run_main(source, enable_start_button, data_queue, src_lang_var, dest_lang_var):
    try:
        prepare_model(source, enable_start_button,
                      data_queue, src_lang_var, dest_lang_var)
    except Exception as e:
        messagebox.showerror("Error", str(e))


def setup_ui(window, recorder, source, record_timeout, data_queue):
    def enable_start_button():
        start_button.config(state='normal')

    isSessionUp = tk.BooleanVar()
    isSessionUp.set(False)

    src_lang_var = tk.StringVar(window)
    src_lang_var.set("pl")  # default value
    src_lang_label = tk.Label(window, text="Język źródłowy")
    src_lang_dropdown = tk.OptionMenu(window, src_lang_var, "en", "uk", "pl")

    dest_lang_var = tk.StringVar(window)
    dest_lang_var.set("uk")
    dest_lang_label = tk.Label(window, text="Język docelowy")
    dest_lang_dropdown = tk.OptionMenu(window, dest_lang_var, "en", "uk", "pl")

    role_var = tk.StringVar(window)

    rolesKeys = list(roles.keys())
    role_var.set(rolesKeys[0])
    role_label = tk.Label(window, text="Rola")
    role_dropdown = tk.OptionMenu(
        window, role_var, *rolesKeys)

    def start_button_command():
        if isSessionUp.get():
            isSessionUp.set(False)
            start_button.config(text="Start")
        else:
            isSessionUp.set(True)
            create_session(
                src_lang_var.get(), dest_lang_var.get(), role_var.get())
            start_button.config(text="Stop")
        toggle_listening_state(
            recorder, source, record_callback, record_timeout, data_queue, isSessionUp)

    start_button = tk.Button(
        window, text="Start", state='disabled',
        command=start_button_command)

    ui_elements = [start_button, src_lang_label,
                   src_lang_dropdown, dest_lang_label, dest_lang_dropdown, role_label, role_dropdown]
    for element in ui_elements:
        element.pack(side='top')

    return enable_start_button, src_lang_var, dest_lang_var


def setup_window():
    window = tk.Tk()
    window.geometry("800x600")  # Make the window bigger
    # Center the window
    window_width = window.winfo_reqwidth()
    window_height = window.winfo_reqheight()
    position_right = int(window.winfo_screenwidth()/3 - window_width/2)
    position_down = int(window.winfo_screenheight()/3 - window_height/2)
    window.geometry("+{}+{}".format(position_right, position_down))
    return window


def setup_socketio():
    sio_url = "https://2dvkjqkl-3000.euw.devtunnels.ms"
    sio = socketio.Client()
    sio.connect(sio_url)
    return sio


def setup_updates_frame(window):
    updates_frame = tk.Frame(window)
    updates_frame.pack(side='bottom', fill='both', expand=True)

    updates_content_frame = tk.Frame(updates_frame)
    updates_content_frame.pack(side='left', fill='both', expand=True)
    return updates_content_frame


def create_ui():
    window = setup_window()
    data_queue = Queue()
    window.title("Transcription App")
    record_timeout = 2

    sessionId = None
    stop_listening = None

    recorder, source = setup_recorder()
    enable_start_button, src_lang_var, dest_lang_var = setup_ui(
        window, recorder, source, record_timeout, data_queue)

    # Connect to the socketio server
    sio = setup_socketio()

    updates_content_frame = setup_updates_frame(window)

    @sio.on('update')
    def update_ui(message):
        original_text = message['original']
        translated_text = message['translated']
        name = message['name']
        original_text_formatted = '\n'.join(
            [original_text[i:i+100] for i in range(0, len(original_text), 100)])
        translated_text_formatted = '\n'.join(
            [translated_text[i:i+100] for i in range(0, len(translated_text), 100)])
        update_label = tk.Label(
            updates_content_frame,
            text=f"{name}:\n Orginał: {original_text_formatted}\n Tłumaczenie: {translated_text_formatted}",
            anchor='w',
            justify='left',
            font=("Helvetica", 12, 'bold'),
            fg=roles[name]
        )
        update_label.pack(fill='x')
        # Remove the oldest message if there are more than 10 messages
        if len(updates_content_frame.winfo_children()) > 10:
            updates_content_frame.winfo_children()[0].destroy()

    # Create a thread for the main function and set daemon to True so it will terminate when the UI is closed
    main_thread = Thread(target=lambda: run_main(
        source, enable_start_button, data_queue, src_lang_var, dest_lang_var))
    main_thread.daemon = True
    main_thread.start()

    # Disconnect from the socketio server and close the app when the main thread ends or the window close button is clicked
    def on_close_or_main_thread_end():
        if not main_thread.is_alive():
            sio.disconnect()
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            window.destroy()
    window.protocol("WM_DELETE_WINDOW", on_close_or_main_thread_end)

    window.mainloop()


if __name__ == "__main__":
    create_ui()

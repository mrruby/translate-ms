import tkinter as tk
import socketio


from tkinter import messagebox
from threading import Thread
from queue import Queue

from helpers import prepare_model, record_callback, setup_recorder, toggle_listening_state


def run_main(source, enable_start_button, data_queue, src_lang_var, dest_lang_var):
    try:
        prepare_model(source, enable_start_button,
                      data_queue, src_lang_var, dest_lang_var)
    except Exception as e:
        messagebox.showerror("Error", str(e))


def setup_ui(window, recorder, source, record_timeout, data_queue):
    def enable_start_button():
        start_button.config(state='normal')

    stop_listening = None

    isSessionUp = tk.BooleanVar()
    isSessionUp.set(False)

    def start_button_command():
        if isSessionUp.get():
            isSessionUp.set(False)
            start_button.config(text="Start")
        else:
            isSessionUp.set(True)
            start_button.config(text="Stop")
        toggle_listening_state(
            recorder, source, record_callback, record_timeout, data_queue, isSessionUp)

    start_button = tk.Button(
        window, text="Start", state='disabled',
        command=start_button_command)

    src_lang_var = tk.StringVar(window)
    src_lang_var.set("pl")  # default value
    src_lang_label = tk.Label(window, text="Source Language")
    src_lang_dropdown = tk.OptionMenu(window, src_lang_var, "en", "uk", "pl")

    dest_lang_var = tk.StringVar(window)
    dest_lang_var.set("uk")
    dest_lang_label = tk.Label(window, text="Destination Language")
    dest_lang_dropdown = tk.OptionMenu(window, dest_lang_var, "en", "uk", "pl")

    ui_elements = [start_button, src_lang_label,
                   src_lang_dropdown, dest_lang_label, dest_lang_dropdown]
    for index, element in enumerate(ui_elements):
        element.grid(row=0, column=index)

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
    # sio_url = "https://2dvkjqkl-3000.euw.devtunnels.ms"
    sio = socketio.Client()
    # sio.connect(sio_url)
    return sio


def setup_updates_frame(window):
    updates_frame = tk.Frame(window)
    updates_frame.grid(row=1, column=0, columnspan=5, sticky='nsew')

    updates_canvas = tk.Canvas(updates_frame)
    updates_canvas.grid(row=0, column=0, sticky='nsew')

    updates_scrollbar = tk.Scrollbar(
        updates_frame, orient='vertical', command=updates_canvas.yview)
    updates_scrollbar.grid(row=0, column=1, sticky='ns')

    updates_canvas.configure(yscrollcommand=updates_scrollbar.set)
    updates_canvas.bind('<Configure>', lambda e: updates_canvas.configure(
        scrollregion=updates_canvas.bbox('all')))

    updates_content_frame = tk.Frame(updates_canvas)
    updates_canvas.create_window(
        (0, 0), window=updates_content_frame, anchor='nw')
    return updates_content_frame, updates_canvas


def create_ui():
    window = setup_window()
    data_queue = Queue()
    window.title("Transcription App")
    record_timeout = 2

    recorder, source = setup_recorder()
    enable_start_button, src_lang_var, dest_lang_var = setup_ui(
        window, recorder, source, record_timeout, data_queue)

    # Connect to the socketio server
    sio = setup_socketio()

    # Function to update the UI with the received message
    updates_content_frame, updates_canvas = setup_updates_frame(window)

    @sio.on('update')
    def update_ui(message):
        original_text = message['original']
        translated_text = message['translated']
        update_label = tk.Label(
            updates_content_frame, text=f"Original: {original_text}, Translated: {translated_text}", anchor='w', font=("Helvetica", 20))
        update_label.grid(sticky='ew')  # Changed from pack to grid
        updates_canvas.yview_moveto(1.0)

     # Scroll to the bottom

    # Create a thread for the main function and set daemon to True so it will terminate when the UI is closed
    main_thread = Thread(target=lambda: run_main(
        source, enable_start_button, data_queue, src_lang_var, dest_lang_var))
    main_thread.daemon = True
    main_thread.start()

    # Disconnect from the socketio server when the main thread ends
    def on_main_thread_end():
        if not main_thread.is_alive():
            sio.disconnect()
    window.protocol("WM_DELETE_WINDOW", on_main_thread_end)

    window.mainloop()


if __name__ == "__main__":
    create_ui()

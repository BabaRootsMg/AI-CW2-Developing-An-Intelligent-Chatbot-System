"""
gui.py
-------
This file handles the chatbot's graphical user interface (GUI) using Tkinter.
It manages the user input field, the message display area, and connects to the
chatbot logic to process and respond to user messages.
"""

import tkinter as tk
from tkinter import scrolledtext
from chatbot_logic import get_bot_response  

def send_message():
    user_message = entry_box.get()
    if user_message.strip() == "":
        return
    display_message("You", user_message)
    entry_box.delete(0, tk.END)

    bot_response = get_bot_response(user_message)
    display_message("Bot", bot_response)

def display_message(sender, message):
    chat_area.config(state='normal')
    chat_area.insert(tk.END, f"{sender}: {message}\n\n")
    chat_area.config(state='disabled')
    chat_area.see(tk.END)

# Tkinter Gui 
root = tk.Tk()
root.title("Train checker")
root.geometry("800x800")

chat_area = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD)
chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

entry_box = tk.Entry(root, width=70)
entry_box.pack(padx=10, pady=(0,10), side=tk.LEFT, fill=tk.X, expand=True)

send_button = tk.Button(root, text="Send", command=send_message)
send_button.pack(padx=(0,10), pady=(0,10), side=tk.RIGHT)

#Start gui
root.mainloop()

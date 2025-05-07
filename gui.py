"""
gui.py
-------
This file handles the chatbot's graphical user interface (GUI) using Tkinter.
It manages the user input field, the message display area, and connects to the
chatbot logic to process and respond to user messages.
"""
# gui.py
"""
This file handles the chatbot's graphical user interface (GUI) using Tkinter.
It manages the user input field, the message display area, and connects to the
chatbot logic to process and respond to user messages.
"""

import tkinter as tk
from tkinter import scrolledtext
import webbrowser
import re

from chatbot_logic import Chatbot

# Instantiate a single Chatbot for the session
bot = Chatbot()

def send_message(event=None):
    user_message = entry_var.get().strip()
    if not user_message:
        return

    # Display user text
    display_message("You", user_message)
    entry_var.set("")             # clear entry
    status_label.config(text="")  # clear any previous status

    # Get bot reply
    response = bot.respond(user_message)

    # If it's a slot-filling prompt, show in status bar too
    if response.startswith("(Info needed)"):
        status_label.config(text=response)
    display_message("Bot", response)

def display_message(sender, message):
    chat_area.config(state='normal')
    chat_area.insert(tk.END, f"{sender}: ")

    # Find URLs in the message and make them clickable
    url_pattern = re.compile(r"(https?://\S+)")
    last_end = 0
    for match in url_pattern.finditer(message):
        # Text before URL
        chat_area.insert(tk.END, message[last_end:match.start()])
        url = match.group(1)
        start = chat_area.index(tk.END)
        chat_area.insert(tk.END, url)
        end = chat_area.index(tk.END)
        chat_area.tag_add(url, start, end)
        chat_area.tag_bind(url, "<Button-1>", lambda e, url=url: webbrowser.open(url))
        chat_area.tag_config(url, foreground="blue", underline=True)
        last_end = match.end()

    # Any remaining text after the last URL
    chat_area.insert(tk.END, message[last_end:] + "\n\n")
    chat_area.config(state='disabled')
    chat_area.see(tk.END)

def reset_conversation():
    global bot
    bot = Chatbot()  # reinstantiate to clear state
    chat_area.config(state='normal')
    chat_area.delete("1.0", tk.END)
    chat_area.config(state='disabled')
    status_label.config(text="")
    display_message("Bot", "Hello! How can I help you today?")

# --- Build the Tkinter UI ---
root = tk.Tk()
root.title("Train Checker Chatbot")
root.geometry("800x600")

# Chat display area
chat_area = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD)
chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Status label for slot-filling prompts
status_label = tk.Label(root, text="", fg="darkgreen")
status_label.pack(padx=10, pady=(0,5))

# Entry box and Send button
entry_var = tk.StringVar()
def on_entry_change(*args):
    send_button.config(state=tk.NORMAL if entry_var.get().strip() else tk.DISABLED)
entry_var.trace_add("write", on_entry_change)

entry_box = tk.Entry(root, textvariable=entry_var, width=70)
entry_box.pack(padx=10, pady=(0,10), side=tk.LEFT, fill=tk.X, expand=True)
entry_box.bind("<Return>", send_message)  # Enter key works too

send_button = tk.Button(root, text="Send", command=send_message, state=tk.DISABLED)
send_button.pack(padx=(0,10), pady=(0,10), side=tk.LEFT)

# Reset button
reset_button = tk.Button(root, text="Reset", command=reset_conversation)
reset_button.pack(padx=10, pady=(0,10), side=tk.RIGHT)

# Initial greeting
display_message("Bot", "Hello! How can I help you today?")

root.mainloop()

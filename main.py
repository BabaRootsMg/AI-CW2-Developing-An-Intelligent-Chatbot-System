# main.py
"""
Entry point for the Train-Checker chatbot.
By default runs in the terminal; pass '--gui' to launch the Tkinter GUI.
"""

import sys

def run_cli():
    from chatbot_logic import Chatbot
    bot = Chatbot()
    print("Bot: Hello! How can I help you today?")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user:
            continue
        # Allow exit
        if user.lower() in ("exit", "quit"):
            print("Bot: Goodbye!")
            break

        reply = bot.respond(user)
        print(f"Bot: {reply}")

def run_gui():
    # gui.py already does root.mainloop()
    import gui  # noqa: F401

if __name__ == "__main__":
    if "--gui" in sys.argv:
        run_gui()
    else:
        run_cli()

# chatbot_logic.py

def get_bot_response(user_input):
    user_input = user_input.lower()
    if "ticket" in user_input or "book" in user_input:
        return "Sure, I can help you book a train ticket. Where are you travelling from?"
    elif "delay" in user_input or "late" in user_input:
        return "Okay, let's check your train delay. Which station are you currently at?"
    else:
        return "I'm sorry, I didn't understand that. Can you rephrase?"

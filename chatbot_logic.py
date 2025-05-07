# chatbot_logic.py

from nlp import NLPProcessor
from api_integration import find_cheapest_ticket
from prediction_model import predict_arrival

class Chatbot:
    def __init__(self):
        self.nlp   = NLPProcessor()
        self.state = {"intent": None, "slots": {}}

    def respond(self, user_text):
        parsed = self.nlp.parse(user_text)

        # 1) set intent once
        if self.state["intent"] is None:
            self.state["intent"] = parsed["intent"]

        # 2) merge in any new slots
        self.state["slots"].update(parsed["slots"])

        # 3) check for missing information
        missing = self.nlp.missing_slots(self.state["intent"], self.state["slots"])
        if missing:
            prompts = {
                "departure":   "Where are you travelling from?",
                "destination": "Where would you like to go?",
                "date":        "On what date?",
                "time":        "What time?",
                "trip_type":   "Is it single or return?",
                "train_id":    "Which train number are you on?",
                "delay_minutes":"How many minutes delayed is it?",
                "current_station":"Where are you right now?",
            }
            return prompts[missing[0]]

        # 4) all slots filled → dispatch based on intent
        if self.state["intent"] == "find_ticket":
            ticket = find_cheapest_ticket(**self.state["slots"])
            return (f"The cheapest fare is £{ticket.price:.2f}. "
                    f"You can book here: {ticket.url}")
        else:  # predict_delay
            eta = predict_arrival(**self.state["slots"])
            return f"Your train is now expected at {eta.strftime('%H:%M')}."

# Create one global Chatbot
_bot = Chatbot()

def get_bot_response(message: str) -> str:
    return _bot.respond(message)

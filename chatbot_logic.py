# chatbot_logic.py
from nlp_module           import NLPProcessor
from trainlinescraper     import find_cheapest_ticket
# from delay_predictor      import predict_arrival  # Disabled until Task 2 is implemented

class Chatbot:
    def __init__(self):
        self.nlp   = NLPProcessor()
        self.state = {"intent": None, "slots": {}}

    def respond(self, user_text):
        parsed = self.nlp.parse(user_text)
        if self.state["intent"] is None:
            self.state["intent"] = parsed["intent"]
        self.state["slots"].update(parsed["slots"])

        missing = self.nlp.missing_slots(self.state["intent"], self.state["slots"])
        if missing:
            return {
                "departure":      "(Info needed) Where from?",
                "destination":    "(Info needed) Where to?",
                "date":           "(Info needed) On what date?",
                "time":           "(Info needed) At what time?",
                "trip_type":      "(Info needed) Single or return?",
                # Delay slots are intentionally omitted while stubbed out
            }[missing[0]]

        if self.state["intent"] == "find_ticket":
            s = self.state["slots"]
            ticket = find_cheapest_ticket(
                departure   = s["departure"],
                destination = s["destination"],
                date        = s["date"],
                time_of_day = s.get("time"),
                trip_type   = s.get("trip_type","single")
            )
            self._reset_state()
            return f"The cheapest fare is £{ticket.price:.2f}. Book: {ticket.url}"

        # Delay prediction is temporarily disabled for Task 2
        # elif self.state["intent"] == "predict_delay":
        #     eta = predict_arrival(**self.state["slots"])
        #     self._reset_state()
        #     return f"ETA: {eta.strftime('%H:%M')}"

        # General fallback
        return "Sorry, I don't know that."

    def _reset_state(self):
        self.state = {"intent": None, "slots": {}}

# Singleton instance for GUI/CLI
_bot = Chatbot()

def get_bot_response(msg):
    return _bot.respond(msg)

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from nlp_module import NLPProcessor
from trainlinescraper import find_cheapest_ticket

class Chatbot:
    """
    Chatbot logic handling dialogue state, external calls, and responses.
    Refactored to avoid misclassifying confirmations as unsupported.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nlp = NLPProcessor()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._reset_state()

    def _reset_state(self):
        """Clear dialogue state for a new conversation."""
        self.state = {"intent": None, "slots": {}}
        self.confirm_done = False

    def respond(self, user_text: str) -> str:
        """Generate a response for the user's message."""
        parsed = self.nlp.parse(user_text)
        intent = parsed["intent"]
        confidence = parsed["confidence"]
        slots = parsed["slots"]
        self.logger.debug(f"Parsed intent={intent} (conf={confidence:.2f}), slots={slots}")

        # Determine if this is the first turn of the conversation
        first_turn = self.state["intent"] is None
        if first_turn:
            # On first turn, handle unsupported/low-confidence
            if intent == "unsupported" or confidence < 0.05:
                self.logger.info("Fallback on first turn: unsupported intent or low confidence")
                response = (
                    "Sorry, I can only help with UK train enquiries. "
                    "Could you rephrase or ask about train tickets or delays?"
                )
                self._reset_state()
                return response
            # Else accept intent
            self.state["intent"] = intent

        # Update slots for ongoing dialogue
        self.state["slots"].update(slots)

        # Route based on established intent
        if self.state["intent"] == "find_ticket":
            return self._handle_find_ticket()
        # elif self.state["intent"] == "predict_delay":
        #     return self._handle_predict_delay()

        # Catch-all: reset and apologize
        self._reset_state()
        return "Sorry, I don't know how to help with that."

    def _handle_find_ticket(self) -> str:
        """Carry out slot-filling and call external ticket search."""
        s = self.state["slots"]
        # Confirm stations once
        if not self.confirm_done and all(k in s for k in ("departure", "destination")):
            self.confirm_done = True
            self.logger.info("Asking confirmation of stations")
            return (
                f"Just to confirm: you want to travel from "
                f"{s['departure']} to {s['destination']}, correct?"
            )

        # Prompt for missing slots
        prompts = [
            ("departure",   "(Info needed) Where are you departing from?"),
            ("destination", "(Info needed) Where are you going to?"),
            ("date",        "(Info needed) What date would you like to travel?"),
            ("time",        "(Info needed) What time would you prefer?"),
            ("trip_type",   "(Info needed) Is it single or return?")
        ]
        for key, prompt in prompts:
            if key not in s:
                self.logger.debug(f"Missing slot '{key}', prompting user")
                return prompt

        # All slots present: search tickets
        self.logger.info(f"All slots filled: {s}, initiating ticket search")
        future = self.executor.submit(
            find_cheapest_ticket,
            departure=s['departure'],
            destination=s['destination'],
            date=s['date'],
            time_of_day=s.get('time'),
            trip_type=s['trip_type']
        )
        try:
            ticket = future.result(timeout=15)
        except TimeoutError:
            self.logger.error("Ticket search timed out")
            self._reset_state()
            return "Sorry, searching for tickets is taking too long. Please try again later."
        except Exception:
            self.logger.exception("Error during ticket search")
            self._reset_state()
            return "Oops, something went wrong fetching tickets. Try again later."

        # Present result and reset
        response = (
            f"The cheapest fare is £{ticket.price:.2f}. "
            f"Book here: {ticket.url}"
        )
        self.logger.info("Presented cheapest ticket to user")
        self._reset_state()
        return response

# Singleton instance for GUI/CLI
_bot = Chatbot()

def get_bot_response(msg: str) -> str:
    return _bot.respond(msg)

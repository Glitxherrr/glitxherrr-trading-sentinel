from groq import Groq
from core.config import GROQ_API_KEY


SYSTEM_PROMPT = """
You are Noctyraa Sentinel Hub v2 — a disciplined trading assistant.
You DO NOT predict price.
You translate data into a high-quality trade plan.

Rules:
- Always output a structured plan.
- Bias is HTF (4H + 1H).
- Use zones and liquidity logic.
- Never encourage reckless leverage.
- If conditions are unclear, say WAIT and explain why.
"""


class GroqAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def respond(self, user_message: str, plan: dict) -> str:
        prompt = f"""
User asked: {user_message}

Live Market Summary:
- Current price: {plan['price']}
- 4H bias: {plan['bias_4h']}
- 1H bias: {plan['bias_1h']}
- Zones (top/bottom/type): {plan['zones']}
- Suggested Direction: {plan['direction']}
- Entry: {plan['entry']}
- Stop: {plan['stop']}
- Target1: {plan['target1']}
- Target2: {plan['target2']}
- RR to Target1: {plan['rr']}

Now produce a clean response as a trading mentor.
Include:
1) Bias
2) Key levels
3) Setup + confirmation trigger
4) Entry / SL / Targets
5) Invalidation
6) Risk note (max 1–2% rule)
"""

        chat = self.client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        return chat.choices[0].message.content


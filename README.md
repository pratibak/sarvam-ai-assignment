# GoodFoods Chennai Concierge

A Streamlit-based conversational concierge for GoodFoods’ Chennai destinations. The assistant combines OpenAI’s structured responses with a curated SQLite dataset of cafés, breakfast clubs, Italian trattorias, wine lounges, dessert ateliers, and more. Guests can explore neighbourhood-specific options, view offers, and confirm reservations through a single chat interface.

---

## 📦 Project Structure

```
SarvamAI/
├── app.py                     # Streamlit UI
├── agents/
│   ├── orchestrator.py        # Core LLM orchestrator
│   └── prompts.py             # System prompt & format helpers
├── database/
│   ├── schema.sql             # SQLite schema
│   ├── seed_data.py           # Chennai seed script
│   └── db_manager.py          # CRUD utilities
├── tests/                     # Pytest suites for data/geo utilities
├── requirements.txt           # Python dependencies
└── data/restaurants.db        # Generated SQLite database (after seeding)
```

---

## 🚀 Setup & Local Run

1. **Clone and prepare a virtual environment**
   ```bash
   git clone <repo-url>
   cd SarvamAI
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Fill in your OpenAI key (`OPENAI_API_KEY`) and optional overrides:
     ```env
     OPENAI_API_KEY=sk-...
     DEFAULT_MODEL=gpt-4o-mini      # choose any chat-capable model
     CHAT_HISTORY_TURNS=2           # number of past turns the LLM sees
     DATABASE_PATH=data/restaurants.db
     ```

4. **Seed the Chennai dataset (first run only)**
   ```bash
   python database/seed_data.py
   ```

5. **Launch the concierge**
   ```bash
   streamlit run app.py
   ```

6. **(Optional) Run tests**
   ```bash
   pytest
   ```

---

## 🧠 Prompt Engineering & Tooling

The orchestrator prompt (`agents/prompts.py`) follows the structure recommended in OpenAI’s realtime prompting guide:

1. **Role & Objective** – defines the concierge persona and success conditions.
2. **Personality & Tone** – enforces warm, concise Chennai hospitality.
3. **Tools** – clearly enumerates when to call each function (`find_restaurants`, `make_reservation`, etc.).
4. **Conversation Flow** – guides the LLM through discovery → booking follow-ups.
5. **Critical Notes** – clarifies expectations (no assumptions, highlight availability and offers).
6. **Response Format** – forces a JSON-only output with the schema:
   ```json
   {
     "summary": "Short overview",
     "options": [
       {
         "title": "Option name",
         "subtitle": "Cuisine or highlight",
         "distance_km": 2.5,
         "details": "Two-sentence highlight",
         "attributes": ["Parking", "Outdoor seating"]
       }
     ],
     "next_steps": "Concise CTA"
   }
   ```

The orchestrator parses this JSON payload to render structured cards in `app.py`. Any additional text from the model is stored in `json["summary"]`.

The agent enforces:
- **Short context window** (`CHAT_HISTORY_TURNS`) to reduce latency.
- **Explicit tool usage** (never assume, always confirm).
- **Fallback paths** when no offers or restaurants match.

---

## 💬 Sample Conversations

### 1. Quick Neighbourhood Discovery
```
Guest: Show me dessert spots in Besant Nagar.
Assistant JSON summary:
  summary: "Two dessert ateliers in Besant Nagar for tonight."
  options:
    - title: "GoodFoods Sugar Works Lab – Besant Nagar"
      subtitle: "Dessert tasting room"
      distance_km: 1.2
      details: "Chef-led plated desserts with live cocoa bar."
      attributes: ["Parking", "Outdoor terrace"]
  next_steps: "Would you like me to check availability for Sugar Works Lab?"
```

### 2. Full Booking Flow
```
Guest: Book Italian dinner near Alwarpet tomorrow 8 PM for 3.
Assistant:
  - Calls find_restaurants_by_area("Alwarpet")
  - Suggests "GoodFoods Italian Piazza – Alwarpet"
  - Prompts for confirmation of date, time, party
Guest: Yes, confirm the Italian Piazza.
Assistant JSON summary:
  summary: "Table awaiting at GoodFoods Italian Piazza – Alwarpet."
  options: []
  next_steps: "Reservation locked for 3 guests tomorrow 20:00. Anything else?"
```

### 3. Offers Journey
```
Guest: Any wine offers this weekend?
Assistant:
  - Calls find_restaurants(has_offers=True)
  - Surfaces wine lounges with active promos
Assistant JSON summary:
  summary: "Two wine-forward experiences with weekend offers."
  options:
    - title: "GoodFoods Madras Cellar – ECR"
      subtitle: "Wine & dine lounge"
      details: "Saturday Sangria Sundowner – third glass on the house."
  next_steps: "Shall I hold a slot or share details for another lounge?"
```

---

## 📈 Business Strategy Snapshot

1. **Market Positioning**
   - Highlight GoodFoods as the premium multi-experience brand in Chennai, covering breakfast-to-dessert with consistent service quality.
   - Emphasize neighbourhood coverage (T. Nagar, Besant Nagar, OMR/ECR) to win hyperlocal loyalty.

2. **Guest Acquisition Loop**
   - Use the concierge as a digital front desk: every chat captures intent, top picks, and potential reservations.
   - Bubble up active offers automatically to increase conversion (e.g., “Sangria Sundowner”).

3. **Retention & Insights**
   - Conversation logs (stored via `conversation_logs` table) reveal demand hotspots, frequent complaints, or missing services.
   - Integrate with CRM to trigger loyalty rewards after repeated bookings or positive feedback.

4. **Operational Efficiency**
   - Tool-based orchestration ensures consistent data checks before booking (no overbooked outlets).
   - Modular dataset (`database/seed_data.py`) makes it easy to add new cities or concepts.

5. **Expansion Playbook**
   - Clone the schema and prompt for other metros (Mumbai, Delhi) with localized tone and offers.
   - Extend the JSON schema to include upsell recommendations (chef’s table, premium pairings).

---

## 🛠️ Troubleshooting & Tips

- **Slow responses?** Switch `DEFAULT_MODEL` to `gpt-4o-mini` or lower `CHAT_HISTORY_TURNS`.
- **No data showing?** Rerun `python database/seed_data.py` and restart Streamlit.
- **Invalid JSON from the model?** The UI still falls back to plain text, but retrain the system prompt if it happens frequently.
- **Booking issues?** Inspect `agents/tools.py` for tool output, or check logs in `database/db_manager.py`.

---

## 🤝 Contributions & Next Steps

1. Add admin dashboards for offer management.
2. Integrate SMS/email notifications post-booking.
3. Track conversion metrics in a lightweight analytics table.

Pull requests and prompt-improvement ideas are welcome—short bullet tweaks often have the biggest impact on realtime behavior. Whenever you adjust the prompt, rerun a few sample conversations to verify the JSON schema still holds. Happy concierge-ing!

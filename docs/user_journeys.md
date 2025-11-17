# GoodFoods Concierge – User Journeys & Outputs

This guide showcases how the concierge responds to different guest intents. Each journey lists the guest messages, the tools the orchestrator invokes, and the JSON output the model returns (truncated for clarity). Use these examples to verify UI behaviour or to demo the experience end-to-end.

---

## 1. Neighbourhood Discovery + Booking (Multi-turn)

**Guest Flow**
1. Guest signs in with Besant Nagar as anchor.
2. Guest: “Show me dessert lounges in Besant Nagar.”
3. Assistant recommends options.
4. Guest: “Book Sugar Works Lab for tonight at 9pm for 2.”
5. Assistant confirms booking details.

**Tool Calls**
- `find_restaurants_by_area(area_name="Besant Nagar", has_offers=False)`
- `make_reservation(restaurant_id=62, reservation_date="2025-02-15", reservation_time="21:00", party_size=2)`

**Model JSON Output (recommendation step)**
```json
{
  "summary": "Two dessert-forward GoodFoods concepts waiting for you in Besant Nagar.",
  "options": [
    {
      "title": "GoodFoods Sugar Works Lab – Besant Nagar",
      "subtitle": "Dessert tasting room",
      "distance_km": 0.8,
      "details": "Chef-led plated desserts with cacao bar and mocktail pairings.",
      "attributes": ["Parking", "Outdoor terrace", "Seats open tonight"]
    },
    {
      "title": "GoodFoods Café District – Besant Nagar",
      "subtitle": "Artisan café & brunch",
      "distance_km": 1.3,
      "details": "All-day viennoiserie, late-night affogato flights.",
      "attributes": ["All-day menu", "Pet friendly courtyard"]
    }
  ],
  "next_steps": "Would you like me to hold a table or surface weekend offers for either spot?"
}
```

**Model JSON Output (booking confirmation)**
```json
{
  "summary": "Table secured at GoodFoods Sugar Works Lab – Besant Nagar.",
  "options": [],
  "next_steps": "I’ve locked in 2 seats for 15 Feb at 21:00. Need anything else for dessert tonight?"
}
```

**UI Highlights**
- Cards render with `Book` buttons; confirmation uses summary banner only.
- Payment widget prompts guest to complete the ₹50 reservation fee after confirmation.
- Booking history tab reflects the new reservation without internal IDs.

---

## 2. Business Dinner Planning (Multi-turn with Offer Lookup)

**Guest Flow**
1. Guest: “I need a business dinner venue near Guindy tomorrow evening.”
2. Assistant: suggests venues, asks for time/party details.
3. Guest: “Make it 7pm for 4, needs private seating.”
4. Assistant: confirms details, checks if any lounges have offers.
5. Guest: “Any offers we can leverage?”
6. Assistant: surfaces offer-specific options.

**Tool Calls**
- `find_restaurants_by_area(area_name="Guindy", has_parking=True)`
- `make_reservation(...)` (after confirmation)
- `find_restaurants(has_offers=True)` filtered for Guindy/ECR wine lounges
- `get_daily_offers(restaurant_id=71)`

**Model JSON Output (offer spotlight)**
```json
{
  "summary": "Two wine-forward private dining options near Guindy with live offers.",
  "options": [
    {
      "title": "GoodFoods Madras Cellar – Guindy",
      "subtitle": "Wine & dine lounge",
      "distance_km": 1.4,
      "details": "Weeknight pairing flight with complimentary amuse bouche.",
      "attributes": ["Private dining", "Valid Mon–Thu", "Sommelier on call"]
    }
  ],
  "next_steps": "Tell me if you want this held or need introduction notes for the host."
}
```

---

## 3. Offers Spotlight (Quick Single-turn)

**Guest Flow**
1. Guest: “Any wine lounge offers this weekend?”

**Tool Calls**
- `find_restaurants(has_offers=True)`
- `get_daily_offers(restaurant_id=73)` for each matching outlet

**Model JSON Output**
```json
{
  "summary": "Three wine-forward GoodFoods lounges running weekend specials.",
  "options": [
    {
      "title": "GoodFoods Madras Cellar – ECR",
      "subtitle": "Wine & dine lounge",
      "distance_km": 6.4,
      "details": "Saturday Sangria Sundowner: buy two, third on the house.",
      "attributes": ["Valid Feb 14–16", "Live jazz after 8pm"]
    },
    {
      "title": "GoodFoods Madras Cellar – T. Nagar",
      "subtitle": "Wine & dine lounge",
      "distance_km": 1.1,
      "details": "Sommelier-led pairing flight at introductory pricing.",
      "attributes": ["Friday & Saturday", "Limited seats"]
    }
  ],
  "next_steps": "Want me to hold a slot for the Sundowner or line up alternative lounges?"
}
```

---

## 4. Booking History, Modification & Cancellation (Multi-turn)

**Guest Flow**
1. Guest: “Show my confirmed bookings.”
2. Assistant lists reservations.
3. Guest: “Move the dinner to 9pm instead.”
4. Assistant confirms new time (calls make_reservation for new slot, cancel/adjust previous).
5. Guest: “Actually cancel the brunch booking.”
6. Assistant cancels the specific reservation.

**Tool Calls**
- `get_my_bookings(status="confirmed")`
- `cancel_reservation(reservation_id=128)` (handled internally, ID hidden from UI)
- `make_reservation(...)` for rescheduled dinner

**Model JSON Output (listing step)**
```json
{
  "summary": "Here are your confirmed GoodFoods reservations.",
  "options": [
    {
      "title": "GoodFoods Café District – T. Nagar",
      "subtitle": "Brunch reservation",
      "distance_km": null,
      "details": "20 Feb · 11:00 · Party of 2",
      "attributes": ["Parking available", "Outdoor seating"]
    },
    {
      "title": "GoodFoods Heritage Dinner Studio – Adyar",
      "subtitle": "Dinner reservation",
      "distance_km": null,
      "details": "22 Feb · 20:00 · Party of 4",
      "attributes": ["Coastal tasting menu"]
    }
  ],
  "next_steps": "Which one should I reschedule or cancel?"
}
```

**Model JSON Output (cancellation confirmation)**
```json
{
  "summary": "The Café District brunch on 20 Feb is cancelled.",
  "options": [],
  "next_steps": "Need a fresh brunch slot or any other plans handled?"
}
```

---

## 5. No-Match / Fallback Journey

**Guest Flow**
1. Guest: “Book a rooftop in Avadi tonight.”
2. Assistant finds no branches and suggests alternatives.
3. Guest: “Alright, what about Anna Nagar options instead?”
4. Assistant surfaces Anna Nagar recommendations.

**Tool Calls**
- `find_restaurants_by_area(area_name="Avadi")` → empty
- `find_restaurants_by_area(area_name="Anna Nagar")`

**Model JSON Output (fallback)**
```json
{
  "summary": "GoodFoods hasn’t launched in Avadi yet.",
  "options": [],
  "next_steps": "Would you like to explore Anna Nagar or Porur? Both have rooftops with late-night slots."
}
```

**Follow-up JSON (Anna Nagar suggestions)**
```json
{
  "summary": "Three Anna Nagar venues ready for tonight.",
  "options": [
    {
      "title": "GoodFoods Terrace Atelier – Anna Nagar",
      "subtitle": "Rooftop dinner studio",
      "distance_km": 2.0,
      "details": "Curated chef menu with skyline views.",
      "attributes": ["Outdoor only", "Live grill"]
    }
  ],
  "next_steps": "Shall I reserve the Terrace Atelier or line up coastal options instead?"
}
```

---

## 6. Feedback Collect & Summary

**Guest Flow**
1. Guest: “Record feedback for my Italian Piazza dinner yesterday.”
2. Assistant prompts for rating and comments.
3. Guest: “Give it 5, amazing service.”
4. Assistant confirms submission and surfaces loyalty CTA.

**Tool Calls**
- `submit_feedback(restaurant_id=58, rating=5, comment="Amazing service.")`

**Model JSON Output**
```json
{
  "summary": "Thanks for rating Italian Piazza – your feedback is recorded.",
  "options": [],
  "next_steps": "Would you like to share the same praise with the chef or plan another dinner?"
}
```

---

## 7. Quick Action Journey (One-click prompts)

**Guest Flow**
1. Guest taps quick action “🍷 Pairing suggestions”.
2. Assistant returns a concise JSON entry.

**Tool Calls**
- `find_restaurants(has_offers=False, cuisine="Wine & Dine")`

**Model JSON Output**
```json
{
  "summary": "Two wine-paired dinners worth exploring tonight.",
  "options": [
    {
      "title": "GoodFoods Madras Cellar – Alwarpet",
      "subtitle": "Wine & dine lounge",
      "distance_km": 3.1,
      "details": "Curated seafood pairing flight with sommelier notes.",
      "attributes": ["Sommelier present", "Seats open at 19:30"]
    }
  ],
  "next_steps": "Should I pencil one in for you or share dessert pairings too?"
}
```

---

## Extending Use Cases

- Add corporate event support: extend the schema with `options[].contact_person` and create an event planning tool.
- Integrate transport constraints: include `"attributes": ["Metro accessible"]` when the guest prefers public transit.
- Build a loyalty follow-up journey: after multiple bookings, respond with `"next_steps": "You’ve earned a tasting flight—shall I apply it to your next visit?"`

Keep the system prompt aligned with these flows and update this document whenever you introduce a new intent or tool. The JSON-first approach makes it easy to spot regressions during prompt tuning.***

### Tips for Extending Journeys
- Add new categories to `QUICK_ACTIONS` in `app.py` and ensure the prompt outlines how to respond.
- Update `database/seed_data.py` for new experiences (e.g., chef’s tables) and create matching example journeys here.
- When testing, watch the JSON payload via the console logs to ensure the schema stays consistent after prompt tweaks.

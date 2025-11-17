# Example Conversations – GoodFoods Concierge

This document contains sample console transcripts for the concierge. Each dialogue shows the guest messages, assistant replies (rendered JSON), and notes about the underlying tool calls or business logic. Use these examples for demos, QA, or regression checks after prompt updates.

---

## Legend
- **GUEST** – user message typed into the chat.
- **ASSISTANT** – assistant JSON response (formatted for readability).
- **TOOLS** – functions the orchestrator invoked for that turn.

---

## 1. Quick Discovery & Booking (Dessert)

```
GUEST: Show me dessert lounges in Besant Nagar.

ASSISTANT:
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

TOOLS: find_restaurants_by_area(area_name="Besant Nagar")

GUEST: Book Sugar Works Lab tonight at 9 for 2.

ASSISTANT:
{
  "summary": "Table secured at GoodFoods Sugar Works Lab – Besant Nagar.",
  "options": [],
  "next_steps": "I’ve locked in 2 seats for 15 Feb at 21:00. Need anything else for dessert tonight?"
}

TOOLS: make_reservation(restaurant_id=62, reservation_date="2025-02-15", reservation_time="21:00", party_size=2)
```

---

## 2. Business Dinner with Offers (Multi-turn)

```
GUEST: Need a quiet business dinner near Guindy tomorrow.

ASSISTANT:
{
  "summary": "Two GoodFoods lounges near Guindy that suit business dinners.",
  "options": [
    {
      "title": "GoodFoods Heritage Dinner Studio – Guindy",
      "subtitle": "Coastal & Chettinad Dinner",
      "distance_km": 1.0,
      "details": "Private dining alcoves with customised spice trail tasting.",
      "attributes": ["Private seating", "Parking", "Available 19:00 onwards"]
    }
  ],
  "next_steps": "Tell me your preferred time and party size so I can lock it in."
}

TOOLS: find_restaurants_by_area(area_name="Guindy", has_parking=True)

GUEST: Make it 7pm for 4.

ASSISTANT:
{
  "summary": "Dinner pencilled at Heritage Dinner Studio – Guindy.",
  "options": [],
  "next_steps": "Shall I confirm the reservation or share available offers?"
}

TOOLS: make_reservation(...)

GUEST: Any offers we can use?

ASSISTANT:
{
  "summary": "Two wine-forward GoodFoods lounges running weekday pairing deals.",
  "options": [
    {
      "title": "GoodFoods Madras Cellar – Guindy",
      "subtitle": "Wine & Dine Lounge",
      "distance_km": 1.4,
      "details": "Weeknight pairing flight with complimentary amuse bouche.",
      "attributes": ["Private dining", "Valid Mon–Thu", "Sommelier on call"]
    }
  ],
  "next_steps": "Would you like to switch to Madras Cellar or keep the Heritage dinner?"
}

TOOLS: find_restaurants(has_offers=True) → filtered for Guindy, get_daily_offers()
```

---

## 3. Too Few Options / Fallback Flow

```
GUEST: Book a rooftop in Avadi tonight.

ASSISTANT:
{
  "summary": "GoodFoods hasn’t launched in Avadi yet.",
  "options": [],
  "next_steps": "Want to explore Anna Nagar or Porur? Both have rooftop slots tonight."
}

TOOLS: find_restaurants_by_area(area_name="Avadi")

GUEST: Okay, find Anna Nagar rooftops.

ASSISTANT:
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
  "next_steps": "Shall I reserve the Terrace Atelier or surface coastal options as well?"
}

TOOLS: find_restaurants_by_area(area_name="Anna Nagar")
```

---

## 4. Booking History, Reschedule & Cancel

```
GUEST: Show my upcoming bookings.

ASSISTANT:
{
  "summary": "Here are your confirmed GoodFoods reservations.",
  "options": [
    {
      "title": "GoodFoods Café District – T. Nagar",
      "subtitle": "Brunch reservation",
      "distance_km": null,
      "details": "20 Feb · 11:00 · Party of 2",
      "attributes": ["Parking available", "Outdoor seating"]
    }
  ],
  "next_steps": "Shall I reschedule or cancel any of these?"
}

TOOLS: get_my_bookings(status="confirmed")

GUEST: Cancel that brunch.

ASSISTANT:
{
  "summary": "The Café District brunch on 20 Feb is cancelled.",
  "options": [],
  "next_steps": "Need a new brunch slot or wish to plan another experience?"
}

TOOLS: cancel_reservation(reservation_id=<internal>)
```

---

## 5. Feedback Capture

```
GUEST: Record feedback for Italian Piazza yesterday.

ASSISTANT:
{
  "summary": "Happy to capture your feedback for Italian Piazza. What rating out of 5 and any notes?",
  "options": [],
  "next_steps": "Share your rating and a short comment."
}

GUEST: Give it 5 for amazing service.

ASSISTANT:
{
  "summary": "Thanks for rating Italian Piazza – your feedback is recorded.",
  "options": [],
  "next_steps": "Would you like to plan another dinner or share the praise with the chef?"
}

TOOLS: submit_feedback(restaurant_id=58, rating=5, comment="Amazing service.")
```

---

## 6. Quick Action Shortcut (Pairing Suggestions)

```
GUEST taps quick action “🍷 Pairing suggestions”

ASSISTANT:
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
  "next_steps": "Shall I pencil one in for you or share dessert pairings too?"
}

TOOLS: find_restaurants(cuisine="Wine & Dine")
```

---

## 7. Multi-lingual Greeting (Optional)

If you extend the prompt with a language section:

```
GUEST: வணக்கம்! ப்ரஞ்ச் செய்ய எங்க இருக்குது?

ASSISTANT:
{
  "summary": "Besant Nagar மற்றும் Alwarpet பகுதியில் இரண்டு பிரஞ்ச் அனுபவங்கள் இருக்கின்றன.",
  "options": [
    {
      "title": "GoodFoods Café District – Besant Nagar",
      "subtitle": "All-day brunch café",
      "distance_km": 1.2,
      "details": "Filter coffee tasting board மற்றும் open-air seating.",
      "attributes": ["Parking", "ஜன்ம நாள் டெசர்ட் பரிசு"]
    }
  ],
  "next_steps": "எது பிடித்திருக்கிறது? ஒரு முன்பதிவு செய்யவேண்டுமா?"
}

TOOLS: find_restaurants_by_area(area_name="Besant Nagar")
```

---

### Using These Conversations
- **Demos:** copy/paste JSON into the Streamlit console to simulate flows.
- **QA:** after prompt modifications, re-run these transcripts to ensure the schema and tool usage stay consistent.
- **Prompt tuning:** use the “Variety” and “Tone” sections of the system prompt to adjust phrasing if any dialogue feels off-brand.

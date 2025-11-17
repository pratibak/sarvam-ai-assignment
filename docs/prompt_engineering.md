# Prompt Engineering Strategy – GoodFoods Concierge

This document explains how the GoodFoods Chennai concierge keeps responses consistent, concise, and structured. It covers the system prompt design, JSON output schema, tool orchestration rules, and the mechanisms we use to keep latency low.

---

## 1. Core Principles

1. **JSON-first responses**  
   The orchestrator demand fully structured JSON, making UI rendering deterministic and avoiding markdown parsing. Every message adheres to:
   ```json
   {
     "summary": "Short overview",
     "options": [
       {
         "title": "...",
         "subtitle": "...",
         "distance_km": 2.1,
         "details": "...",
         "attributes": [...]
       }
     ],
     "next_steps": "Actionable CTA"
   }
   ```
   If no data is available, `options` becomes `[]` and `summary/next_steps` guide the guest.

2. **Tool-first mindset**  
   The system prompt always instructs the LLM to call a tool before speculating. For example, neighbourhood queries require `find_restaurants_by_area`, and offers rely on `find_restaurants(...has_offers=True)` followed by `get_daily_offers`.

3. **Short, precise messaging**  
   Responses are capped at ~80 words (enforced via instructions) and emphasise Chennai hospitality—warm, concise, and proactive.

4. **Conversation memory (5+ turns)**  
   `CHAT_HISTORY_TURNS` defaults to **6**, ensuring the LLM always sees at least five previous user–assistant turns (e.g., “Book the Italian place” still references the earlier suggestion).

5. **Pricing transparency**  
   The prompt reminds the assistant to disclose the **₹50 reservation fee** and surface spend hints from tool results.

6. **Latency control**  
   The orchestrator trims chat history to the configured turn count, keeping completions fast while preserving necessary context.

---

## 2. System Prompt Structure (`agents/prompts.py`)

The prompt follows OpenAI’s recommended outline:

| Section | Purpose |
| --- | --- |
| **Role & Objective** | Defines the concierge persona and success criteria. |
| **Personality & Tone** | Enforces Chennai hospitality and short responses. |
| **About GoodFoods** | Lists service styles, neighbourhood coverage, and data cues. |
| **Tools** | Explains when each function should be invoked. |
| **Conversation Flow** | Guides multi-turn behaviour (discover → confirm → book). |
| **Critical Notes** | Addresses availability, offers, and fallback handling. |
| **Response Format** | Dictates the JSON schema above. |

Important highlights:

- **ALWAYS call `find_restaurants_by_area`** before telling a guest a locality isn’t served.
- **DO NOT call `make_reservation`** until the guest has explicitly confirmed restaurant, date, time, and party size.
- **Celebrate offers** by checking `has_offers` searches and detailing results via `get_daily_offers`.
- **Fallback** when no venues exist: offer nearby areas and keep `options` empty.

---

## 3. Tool Orchestration Rules

| User Intent | Required Tool Path |
| --- | --- |
| Neighbourhood discovery | `find_restaurants_by_area(area_name=…)` |
| “nearby” or distance-based | `find_restaurants(max_distance_km=…)` |
| Offers / deals | `find_restaurants(has_offers=True)` then `get_daily_offers` |
| Book table | `make_reservation` (after all parameters confirmed) |
| Cancel booking | `cancel_reservation` |
| List upcoming bookings | `get_my_bookings(status="confirmed")` |
| Submit feedback | `submit_feedback` |

Each tool returns a JSON snippet (status, message, results) that the orchestrator merges into the final assistant JSON.

---

## 4. Safeguards & Edge Cases

1. **Ambiguous locations** – For locality-only prompts (e.g., “Avadi rooftop”), the prompt requires the LLM to call `find_restaurants_by_area("Avadi")`, receive an empty response, and then suggest adjacent areas (Anna Nagar, Porur).
2. **No offers** – When `find_restaurants(has_offers=True)` returns nothing, the assistant still answers with an empty `options` array and a `next_steps` suggestion to expand the search.
3. **Tool errors** – The orchestrator catches exceptions (DB issues, invalid dates) and returns a JSON summary with a failure message in `summary` and a corrective `next_steps`.
4. **Conversation resets** – The “New conversation” button clears stored messages and starts from the system prompt, preventing stale context leaks.

---

## 5. Testing & Iteration Workflow

1. **Modify instructions** in `agents/prompts.py`.
2. **Run scripted conversations** (see `docs/example_conversations.md`) to ensure JSON format and tool usage are consistent.
3. **Check logs** in the Streamlit console for parsing errors and tool invocations.
4. **Adjust `CHAT_HISTORY_TURNS`** in `.env` if the model forgets context or stays too verbose.
5. **Update docs** whenever new tools or journey types are introduced.

---

## 6. Common Pitfalls & Fixes

| Issue | Diagnosis | Fix |
| --- | --- | --- |
| Model returns markdown not JSON | Check instructions section for the “ALWAYS reply with JSON” rule; confirm no contradictory quick messages from developer. |
| Too few options shown | Inspect tool output limits (app currently caps to 5 for proximity searches). Raise limit or adjust prompt to request more. |
| Repetitive phrasing | Add a “Variety” bullet, e.g., “Rotate opening lines, do not repeat the same phrase consecutively.” |
| Missing tool calls | Possibly conflicting instructions; ensure the prompt emphasises “ALWAYS call … before replying.” |

---

## 7. Extending the Prompt

- **Add new experience types** (chef’s tables, tasting menus) by updating the “About GoodFoods” section and seeding data.
- **Introduce premium upsells** by including a “Promo” field in the JSON schema and instructing the model to use it when offers exist.
- **Localisation**: Add sections for multilingual handling, e.g., a “Language” block specifying when to respond in Tamil/English.

Keep prompts short, bullet-driven, and explicit. Even small wording changes matter; compare outputs before and after each edit to ensure consistent structured responses.***

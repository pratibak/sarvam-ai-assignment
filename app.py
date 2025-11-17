"""
GoodFoods Concierge - Streamlit Frontend

A conversation-first experience for discovering and booking GoodFoods destinations.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv

from agents.orchestrator import OrchestratorAgent
from database.db_manager import (
    get_customer_conversations,
    get_customer_reservations,
    get_or_create_customer,
    initialize_database,
)

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Streamlit Configuration
# ---------------------------------------------------------------------------

st.set_page_config(page_title="GoodFoods Concierge", page_icon="🍽️", layout="wide")

CUSTOM_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #002b5b 0%, #001226 100%);
    color: #ecf6ff;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: rgba(2, 22, 48, 0.92);
    color: #ecf6ff;
}
.block-container { padding-top: 2rem; color: #ecf6ff; }
.quick-card {
    background: linear-gradient(135deg, #023e8a 0%, #0353a4 100%);
    border-radius: 16px;
    padding: 18px 16px;
    margin-bottom: 12px;
    box-shadow: 0 12px 28px rgba(0, 35, 82, 0.35);
    border: 1px solid rgba(3, 118, 175, 0.35);
}
.quick-card h4 { margin-bottom: 6px; color: #f1fbff; font-weight: 700; }
.quick-card p { margin-bottom: 0; font-size: 0.9rem; color: rgba(214, 236, 255, 0.9); }
.stButton > button {
    border-radius: 12px;
    border: none;
    background: linear-gradient(135deg, #00b4d8 0%, #0096c7 100%);
    color: #00203a;
    font-weight: 700;
    box-shadow: 0 12px 24px rgba(0, 150, 199, 0.3);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #48cae4 0%, #0096c7 100%);
}
.stChatMessage {
    background: rgba(2, 40, 76, 0.85);
    border-radius: 18px;
    border: 1px solid rgba(0, 168, 232, 0.25);
    color: #f1fbff;
}
.stChatInputContainer {
    background: rgba(0, 29, 58, 0.92);
    border-radius: 20px;
    border: 1px solid rgba(0, 168, 232, 0.25);
}
.stMarkdown, .stCaption, .stText { color: inherit; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = os.getenv("DATABASE_PATH", "data/restaurants.db")
DEFAULT_LAT = float(os.getenv("DEFAULT_LATITUDE", "13.0418"))
DEFAULT_LON = float(os.getenv("DEFAULT_LONGITUDE", "80.2337"))

GOODFOODS_AREAS = {
    "T. Nagar": (13.0418, 80.2337),
    "Nungambakkam": (13.0615, 80.2425),
    "Anna Nagar": (13.0879, 80.2128),
    "Velachery": (12.9801, 80.2209),
    "Adyar": (13.0067, 80.2570),
    "Besant Nagar": (13.0008, 80.2668),
    "Mylapore": (13.0300, 80.2680),
    "Alwarpet": (13.0310, 80.2500),
    "OMR": (12.9279, 80.2340),
    "ECR": (12.9455, 80.2487),
    "Guindy": (13.0065, 80.2203),
    "Kilpauk": (13.0790, 80.2470),
    "Tambaram": (12.9229, 80.1279),
    "Porur": (13.0492, 80.1764),
    "Pallavaram": (12.9676, 80.1521),
}

QUICK_ACTIONS = [
    (
        "🎯 Discover concepts near me",
        "Scan the top-rated outlets tailored to your preference radius.",
        "Find the highest-rated GoodFoods concepts near me within 3 km.",
    ),
    (
        "🍽️ Secure tonight 7:30 PM",
        "Lock in a two-top with non-veg options around Adyar.",
        "Hold a table for two at 7:30 PM tonight near Adyar with non-veg options.",
    ),
    (
        "🛠️ Build full itinerary",
        "Stitch together pre-dinner drinks, dinner, and dessert in one flow.",
        "Design a pre-dinner drinks + dinner + dessert itinerary around a premium concept.",
    ),
    (
        "🍷 Pairing suggestions",
        "Match tonight’s menu with bespoke beverage pairings.",
        "Recommend drink pairings for a seafood-focused dinner tonight.",
    ),
    (
        "📍 Explore coastal feasts",
        "Surface seafood-forward venues with live catch specials.",
        "Show me seafood-focused GoodFoods restaurants with availability this weekend.",
    ),
    (
        "💼 Arrange a business dinner",
        "Find sophisticated venues with private seating and premium menus.",
        "Find a premium GoodFoods outlet suitable for a business dinner tomorrow at 8 PM.",
    ),
]

STRUCTURED_RESPONSE_KEYS = (
    "restaurants",
    "bookings",
    "reservation",
    "restaurant",
    "reservation_fee",
    "estimated_spend_per_person",
    "estimated_subtotal",
    "estimated_total_with_fee",
)


def attach_structured_fields(response: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """Copy structured fields (restaurants, bookings, reservation, etc.) into payload."""
    for key in STRUCTURED_RESPONSE_KEYS:
        if key in response:
            payload[key] = response[key]


def try_parse_payload(content: Any) -> Optional[Dict[str, Any]]:
    """
    Attempt to coerce arbitrary content into a structured dict payload.

    Returns:
        Dict payload suitable for render_json_response, or None if parsing fails.
    """
    if isinstance(content, dict):
        return content

    if isinstance(content, list):
        return {"options": content}

    if not isinstance(content, str):
        return None

    raw = content.strip()
    if not raw or raw[0] not in "{[":
        return None

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {"options": parsed}
    return None

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def initialize_app() -> None:
    """Ensure the database exists with the latest schema."""
    if not Path(DB_PATH).exists():
        initialize_database(DB_PATH)


def init_session_state() -> None:
    """Set default values for commonly used session keys."""
    defaults = {
        "customer_id": None,
        "customer_name": None,
        "customer_phone": None,
        "customer_area": None,
        "user_lat": DEFAULT_LAT,
        "user_lon": DEFAULT_LON,
        "messages": [],
        "orchestrator": None,
        "quick_command": None,
        "pending_prompt": None,
        "show_debug_json": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "paid_reservations" not in st.session_state:
        st.session_state.paid_reservations = set()


def ensure_orchestrator() -> None:
    """Create the orchestrator agent if missing."""
    if st.session_state.get("orchestrator"):
        return

    customer_id = st.session_state.get("customer_id")
    customer_name = st.session_state.get("customer_name")
    customer_phone = st.session_state.get("customer_phone")

    if not all([customer_id, customer_name, customer_phone]):
        return

    lat = st.session_state.get("user_lat") or DEFAULT_LAT
    lon = st.session_state.get("user_lon") or DEFAULT_LON

    try:
        st.session_state.orchestrator = OrchestratorAgent(
            DB_PATH, customer_id, customer_name, customer_phone, lat, lon
        )
    except Exception as exc:
        st.error(f"Unable to initialise GoodFoods concierge: {exc}")


def process_quick_command() -> None:
    """Execute any queued quick actions (like book button taps)."""
    command = st.session_state.pop("quick_command", None)
    orchestrator = st.session_state.get("orchestrator")

    if not command or not orchestrator:
        return

    if isinstance(command, str):
        command = {"type": "prompt", "text": command}

    if command.get("type") == "book":
        restaurant = command["restaurant"]
        user_prompt = (
            f"I'd like to book a table at {restaurant['name']} in Chennai. "
            "I still need to finalise the date, time, and party size—please help me confirm the details."
        )

        st.session_state.messages.append({"role": "user", "content": user_prompt})

        try:
            with st.spinner("Checking live availability..."):
                response = orchestrator.process_message(user_prompt)

            summary_text = None
            if response.get("json"):
                summary_text = response["json"].get("summary")

            response_payload = {
                "role": "assistant",
                "content": summary_text or response["text"]
            }

            if response.get("json"):
                response_payload["json"] = response["json"]

            attach_structured_fields(response, response_payload)
            st.session_state.messages.append(response_payload)

        except Exception as exc:
            st.error(f"Unable to process booking request: {exc}")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"I ran into an issue while trying to book that table: {exc}",
                }
            )

    elif command.get("type") == "prompt":
        prompt_text = command["text"]

        if st.session_state.get("pending_prompt"):
            return

        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.session_state.pending_prompt = prompt_text
        st.experimental_rerun()


def process_pending_prompt() -> None:
    """If a prompt is pending, fetch assistant response."""
    pending_prompt = st.session_state.get("pending_prompt")
    orchestrator = st.session_state.get("orchestrator")

    if not pending_prompt or not orchestrator:
        return

    rerun_needed = False

    try:
        with st.spinner("Curating ideas..."):
            response = orchestrator.process_message(pending_prompt)

        summary_text = None
        if response.get("json"):
            summary_text = response["json"].get("summary")

        response_payload = {
            "role": "assistant",
            "content": summary_text or response["text"]
        }

        attach_structured_fields(response, response_payload)

        st.session_state.messages.append(response_payload)
        rerun_needed = True

    except Exception as exc:
        st.error(f"Unable to process that request: {exc}")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"I ran into an issue while handling that suggestion: {exc}",
            }
        )

    finally:
        st.session_state.pending_prompt = None
        if rerun_needed:
            st.experimental_rerun()


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------


def render_login() -> None:
    """Render the onboarding form for new or returning guests."""
    st.title("🍽️ GoodFoods Signature Experiences")
    st.caption("Discover curated cafés, chef-driven dinners, wine lounges, and dessert studios across Chennai.")
    st.divider()

    overview_col, form_col = st.columns([2, 1.2])

    with overview_col:
        st.subheader("Why guests love GoodFoods concierge")
        st.markdown(
            """
            - 🌇 **Neighbourhood-first** suggestions across T. Nagar, Besant Nagar, ECR, OMR, Anna Nagar, and more  
            - 🍷 **Every service style** covered: breakfast trails, Italian evenings, coastal supper clubs, wine pairings, dessert ateliers  
            - 📅 **Live availability** and curated offers surfaced instantly  
            - 🤝 **Conversational planning** that remembers your preferences
            """
        )
        st.info("Already dined with us? Use the same phone number to pick up where you left off.")

    with form_col:
        st.subheader("Step into the concierge")
        with st.form("goodfoods_login_form", clear_on_submit=False):
            name = st.text_input("Your name")
            phone = st.text_input("Mobile number")

            area_options = ["Auto-detect (T. Nagar)"] + list(GOODFOODS_AREAS.keys())
            area_choice = st.selectbox("Anchor locality", options=area_options, index=0)
            selected_area = None if area_choice == area_options[0] else area_choice

            submitted = st.form_submit_button("Launch GoodFoods Concierge", use_container_width=True)

    if submitted:
        if not name or not phone:
            st.error("Please share your name and mobile number to continue.")
            return

        if selected_area:
            lat, lon = GOODFOODS_AREAS[selected_area]
        else:
            lat, lon = DEFAULT_LAT, DEFAULT_LON
            selected_area = "T. Nagar"

        try:
            customer = get_or_create_customer(DB_PATH, name, phone)
            st.session_state.customer_id = customer["id"]
            st.session_state.customer_name = customer["name"]
            st.session_state.customer_phone = customer["phone"]
            st.session_state.customer_area = selected_area
            st.session_state.user_lat = lat
            st.session_state.user_lon = lon
            st.session_state.orchestrator = None  # force reinitialisation

            history = get_customer_conversations(DB_PATH, customer["id"])
            st.session_state.messages = []

            if history:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            f"Welcome back, {name}! 👋 Picking up our GoodFoods conversation right where we left off. "
                            "Ask for new ideas, check reservations, or say the word to book again."
                        ),
                    }
                )

                for conv in history[-30:]:
                    st.session_state.messages.append({"role": conv["role"], "content": conv["message"]})
            else:
                intro = (
                    f"Vanakkam {name}! I'm your GoodFoods concierge for Chennai. "
                    f"I can line up cafés, breakfast clubs, Italian evenings, wine lounges, "
                    f"and dessert tastings around {selected_area}. Just tell me what you're craving!"
                )
                st.session_state.messages.append({"role": "assistant", "content": intro})

            st.experimental_rerun()

        except Exception as exc:
            st.error(f"Unable to sign you in: {exc}")


def render_authenticated_view() -> None:
    """Render the main concierge experience once the guest is logged in."""
    ensure_orchestrator()

    tabs = st.tabs(["Concierge Chat", "My Booking History", "My Details"])

    with tabs[0]:
        render_concierge_tab()

    with tabs[1]:
        render_booking_history_tab()

    with tabs[2]:
        render_profile_tab()


def render_concierge_tab() -> None:
    """Display the conversational interface and quick actions."""
    orchestrator = st.session_state.get("orchestrator")

    top_bar = st.container()
    info_col, action_col = top_bar.columns([4, 1])

    with info_col:
        st.markdown(f"### Hello, {st.session_state.customer_name} 👋")
        st.caption(f"📞 {st.session_state.customer_phone}")
        if st.session_state.customer_area:
            st.caption(f"📍 Anchored in {st.session_state.customer_area}")

    with action_col:
        if st.button("New conversation", key="new_convo", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            intro = (
                f"Restarting our GoodFoods concierge session, {st.session_state.customer_name}. "
                f"Ready whenever you want to explore spots around {st.session_state.customer_area}!"
            )
            st.session_state.messages.append({"role": "assistant", "content": intro})
        if st.button("Log out", type="primary", use_container_width=True):
            keys = list(st.session_state.keys())
            for key in keys:
                del st.session_state[key]
            st.experimental_rerun()
        st.checkbox("Debug output", key="show_debug_json")

    st.divider()

    show_quick_actions()

    if not orchestrator:
        st.warning("The concierge is warming up — please try again in a moment.")
        return

    process_quick_command()

    debug_enabled = st.session_state.get("show_debug_json", False)

    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            payload = message.get("json")
            if not payload:
                parsed_payload = try_parse_payload(message.get("content"))
                if parsed_payload:
                    payload = parsed_payload
                    st.session_state.messages[idx]["json"] = parsed_payload

            if payload:
                render_json_response(payload)
            else:
                st.markdown(message["content"])

            if message.get("restaurants"):
                show_restaurant_cards(message["restaurants"])

            if message.get("bookings"):
                display_booking_cards(message["bookings"])

            if message.get("reservation"):
                render_payment_prompt(message)

            if debug_enabled:
                debug_payload = {}
                if payload:
                    debug_payload = payload
                else:
                    for key in STRUCTURED_RESPONSE_KEYS:
                        if key in message:
                            debug_payload[key] = message[key]

                if debug_payload:
                    with st.expander("Debug payload", expanded=False):
                        st.json(debug_payload)

    process_pending_prompt()

    if user_prompt := st.chat_input("Type your request..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("GoodFoods is thinking..."):
                try:
                    response = orchestrator.process_message(user_prompt)

                    payload_json = response.get("json")
                    if not payload_json:
                        payload_json = try_parse_payload(response.get("text"))

                    summary_text = None
                    if payload_json:
                        summary_text = payload_json.get("summary")
                        render_json_response(payload_json)
                    else:
                        st.markdown(response["text"])

                    response_payload = {
                        "role": "assistant",
                        "content": summary_text or response["text"]
                    }

                    if payload_json:
                        response_payload["json"] = payload_json

                    if "restaurants" in response:
                        show_restaurant_cards(response["restaurants"])
                    if "bookings" in response:
                        display_booking_cards(response["bookings"])

                    if debug_enabled:
                        debug_payload = payload_json or {}
                        if not debug_payload:
                            for key in STRUCTURED_RESPONSE_KEYS:
                                if key in response:
                                    debug_payload[key] = response[key]
                        if debug_payload:
                            with st.expander("Debug payload", expanded=False):
                                st.json(debug_payload)

                    attach_structured_fields(response, response_payload)

                    st.session_state.messages.append(response_payload)

                except Exception as exc:
                    error_text = f"I ran into an issue while handling that: {exc}"
                    st.error(error_text)
                    st.session_state.messages.append({"role": "assistant", "content": error_text})


def render_booking_history_tab() -> None:
    """Show a complete list of reservations for the current guest."""
    st.subheader("Your reservations with GoodFoods")
    reservations = get_customer_reservations(DB_PATH, st.session_state.customer_id)

    if not reservations:
        st.info("No reservations just yet — start a chat in the concierge tab to make one!")
        return

    display_booking_cards(reservations)


def render_profile_tab() -> None:
    """Show current guest information."""
    st.subheader("Guest details")

    details = st.container()
    col1, col2 = details.columns(2)

    with col1:
        st.markdown(f"**Name:** {st.session_state.customer_name}")
        st.markdown(f"**Mobile:** {st.session_state.customer_phone}")

    with col2:
        st.markdown(f"**Anchor locality:** {st.session_state.customer_area}")
        st.markdown(f"**Lat/Lon:** {st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f}")

    st.caption("Need to change your anchor location? Log out and sign back in with the new neighbourhood.")


# ---------------------------------------------------------------------------
# Display Helpers
# ---------------------------------------------------------------------------


def render_payment_prompt(message: Dict[str, Any]) -> None:
    """Render a payment confirmation widget when a reservation is made."""
    reservation = message.get("reservation")
    if not reservation:
        return

    reservation_id = reservation.get("id")
    if reservation_id is None:
        return

    paid_reservations = st.session_state.get("paid_reservations", set())
    restaurant = message.get("restaurant") or {}
    fee = message.get("reservation_fee", 50)
    subtotal = message.get("estimated_subtotal")
    total = message.get("estimated_total_with_fee")

    with st.container():
        if reservation_id in paid_reservations:
            st.success("Payment received — your table is ready! 💙")
            return

        st.markdown("### 💳 Complete Your Reservation")
        st.markdown(
            f"- **Restaurant:** {restaurant.get('name', 'GoodFoods destination')}\n"
            f"- **Date:** {reservation.get('reservation_date')}\n"
            f"- **Time:** {reservation.get('reservation_time')}\n"
            f"- **Guests:** {reservation.get('party_size')}"
        )

        fee_line = f"Reservation fee: ₹{fee}"
        if subtotal is not None and total is not None:
            fee_line += f" · Estimated spend ₹{subtotal} (incl. fee: ₹{total})"
        st.info(fee_line)

        col_pay, col_note = st.columns([1, 2])
        with col_pay:
            if st.button("Book Now", key=f"pay_{reservation_id}", use_container_width=True):
                paid_reservations.add(reservation_id)
                st.session_state.paid_reservations = paid_reservations
                st.success("Booking locked in and payment recorded! See you soon. 🌟")
                st.experimental_rerun()
        with col_note:
            st.caption("Tap **Book Now** to initiate payment. Complete the ₹50 fee via UPI/card to hold the table for 15 minutes.")


def render_json_response(payload: Dict[str, Any]) -> None:
    """Render structured JSON payload returned by the assistant."""
    if not isinstance(payload, dict):
        st.markdown(str(payload))
        return

    # Auto-build options from tool output if model omitted them
    options = payload.get("options")
    restaurants = payload.get("restaurants")
    itinerary_segments = payload.get("itinerary") or payload.get("journey") or []

    if (not options or len(options) == 0) and restaurants:
        generated_options = []
        for restaurant in restaurants[:5]:
            attributes = []
            if restaurant.get("has_parking"):
                attributes.append("Parking available")
            if restaurant.get("has_outdoor_seating"):
                attributes.append("Outdoor seating")
            if restaurant.get("yield_hint"):
                attributes.append(restaurant["yield_hint"])
            if restaurant.get("offer_preview"):
                attributes.append(f"Offer: {restaurant['offer_preview']}")
            if restaurant.get("fallback_reason"):
                attributes.append(restaurant["fallback_reason"])
            spend = restaurant.get("estimated_spend_per_person")
            details_parts = []
            if restaurant.get("available_tables") is not None:
                details_parts.append(f"{restaurant['available_tables']} tables open")
            if spend:
                details_parts.append(f"Avg spend ₹{spend}")
            details = " · ".join(details_parts) if details_parts else None

            generated_options.append(
                {
                    "title": restaurant.get("name"),
                    "subtitle": restaurant.get("cuisine"),
                    "distance_km": restaurant.get("distance_km"),
                    "details": details or "Ready for booking tonight.",
                    "attributes": attributes,
                }
            )
        payload["options"] = generated_options

    options = payload.get("options")
    if (not options or len(options) == 0) and itinerary_segments:
        generated_options = []
        seen_titles = set()
        for segment in itinerary_segments:
            stage = (
                segment.get("stage")
                or segment.get("slot")
                or segment.get("title")
                or segment.get("label")
            )
            segment_attributes = segment.get("attributes") or []
            stage_summary = segment.get("summary") or segment.get("details")
            venues = (
                segment.get("options")
                or segment.get("venues")
                or segment.get("stops")
                or segment.get("destinations")
            )

            # If the segment itself carries venue info, treat it as a single option
            if not venues:
                venues = [segment]

            for venue in venues:
                title = venue.get("title") or venue.get("name")
                if not title or title in seen_titles:
                    continue

                subtitle = venue.get("subtitle") or venue.get("cuisine")
                details = (
                    venue.get("details")
                    or venue.get("summary")
                    or stage_summary
                    or "Curated for this itinerary step."
                )

                distance = venue.get("distance_km")
                venue_attributes = venue.get("attributes") or venue.get("highlights") or []

                combined_attributes = []
                if stage and stage not in combined_attributes:
                    combined_attributes.append(stage)
                combined_attributes.extend(attr for attr in segment_attributes if attr not in combined_attributes)
                combined_attributes.extend(attr for attr in venue_attributes if attr not in combined_attributes)

                generated_options.append(
                    {
                        "title": title,
                        "subtitle": subtitle,
                        "distance_km": distance,
                        "details": details,
                        "attributes": combined_attributes,
                    }
                )
                seen_titles.add(title)

        if generated_options:
            payload["options"] = generated_options

    summary = payload.get("summary")
    if summary:
        st.markdown(f"**{summary}**")

    options = payload.get("options") or []
    for option in options:
        with st.container():
            title = option.get("title") or "Option"
            subtitle = option.get("subtitle")
            details = option.get("details")
            distance = option.get("distance_km")
            attributes = option.get("attributes") or []

            header = f"**{title}**"
            if subtitle:
                header += f" · _{subtitle}_"
            st.markdown(header)

            if distance is not None:
                st.caption(f"Distance: {distance} km")

            if details:
                st.markdown(details)

            if attributes:
                st.caption(" · ".join(attributes))

    next_steps = payload.get("next_steps")
    if next_steps:
        st.markdown(f"_Next:_ {next_steps}")

    if itinerary_segments:
        st.markdown("**Suggested itinerary**")
        for segment in itinerary_segments:
            stage = (
                segment.get("stage")
                or segment.get("slot")
                or segment.get("title")
                or segment.get("label")
                or "Experience"
            )
            stage_summary = segment.get("summary") or segment.get("details")
            st.markdown(f"**{stage}**")
            if stage_summary:
                st.markdown(stage_summary)

            venues = (
                segment.get("options")
                or segment.get("venues")
                or segment.get("stops")
                or segment.get("destinations")
            ) or []

            for venue in venues:
                name = venue.get("title") or venue.get("name")
                if not name:
                    continue
                subtitle = venue.get("subtitle") or venue.get("cuisine")
                description = venue.get("details") or venue.get("summary")
                attributes = venue.get("attributes") or venue.get("highlights") or []
                line = f"- {name}"
                if subtitle:
                    line += f" · _{subtitle}_"
                if description:
                    line += f": {description}"
                st.markdown(line)
                if attributes:
                    st.caption(" · ".join(attributes))

    fee = payload.get("reservation_fee")
    if fee is not None:
        subtotal = payload.get("estimated_subtotal")
        total = payload.get("estimated_total_with_fee")
        fee_msg = f"Reservation fee: ₹{fee}"
        if subtotal is not None and total is not None:
            fee_msg += f" · Estimated spend ₹{subtotal} (incl. fee: ₹{total})"
        st.info(fee_msg)


def show_restaurant_cards(restaurants: list) -> None:
    """Render restaurant recommendation cards with quick-book buttons."""
    if not restaurants:
        st.info("No destinations matched that filter. Try broadening your search.")
        return

    for restaurant in restaurants[:6]:
        card = st.container()
        header_cols = card.columns([4, 1])

        with header_cols[0]:
            st.markdown(f"### {restaurant['name']}")
            st.markdown(f"**{restaurant['cuisine']}**")
            st.caption(f"📍 {restaurant['address']}")

        with header_cols[1]:
            if st.button("Book", key=f"book_{restaurant['id']}", use_container_width=True):
                st.session_state.quick_command = {"type": "book", "restaurant": restaurant}

        detail_cols = card.columns(3)

        with detail_cols[0]:
            st.metric("Rating", f"{restaurant['rating']} ⭐")
            spend = restaurant.get("estimated_spend_per_person")
            if spend:
                st.caption(f"Avg spend: ₹{spend} per guest")
            else:
                st.caption(f"Price: {restaurant['price_range']}")

        with detail_cols[1]:
            distance = restaurant.get("distance_km")
            distance_text = f"{distance} km" if distance is not None else "N/A"
            st.metric("Distance", distance_text)
            st.caption(f"Tables open: {restaurant['available_tables']}")

        with detail_cols[2]:
            st.caption(f"🕒 {restaurant.get('opening_time', '—')} – {restaurant.get('closing_time', '—')}")
            features = []
            if restaurant.get("has_parking"):
                features.append("🚗 Parking")
            if restaurant.get("has_outdoor_seating"):
                features.append("🌿 Alfresco")
            st.caption(" · ".join(features) or "Indoor seating")
            spend_hint = restaurant.get("estimated_spend_hint")
            if spend_hint:
                st.caption(spend_hint)

        yield_signal = restaurant.get("yield_signal")
        yield_hint = restaurant.get("yield_hint")
        if yield_signal == "surge":
            st.warning(yield_hint or "High demand period – consider premium pricing.")
        elif yield_signal == "discount":
            st.info(yield_hint or "Opportunity to offer discounts or bundles.")
        elif yield_hint:
            st.caption(yield_hint)

        sponsored_bid = restaurant.get("sponsored_bid")
        if sponsored_bid:
            st.caption(f"Sponsored placement bid: ₹{sponsored_bid} per confirmed booking.")

        if restaurant.get("enterprise_fit"):
            st.caption(restaurant.get("enterprise_hint") or "Enterprise-ready venue for corporate dining.")

        if restaurant.get("fallback_reason"):
            st.caption(f"👉 {restaurant['fallback_reason']}")

        offer_preview = restaurant.get("offer_preview")
        if offer_preview:
            st.success(f"🌟 Offer: {offer_preview}")
        elif restaurant.get("has_active_offers"):
            st.success("🌟 Active offer available")

        st.markdown("---")


def show_quick_actions() -> None:
    """Display quick action suggestions with one-click prompts."""
    with st.container():
        st.subheader("Quick suggestions")
        for i in range(0, len(QUICK_ACTIONS), 3):
            cols = st.columns(3)
            for idx, (col, action) in enumerate(zip(cols, QUICK_ACTIONS[i : i + 3])):
                title, description, prompt = action
                with col:
                    st.markdown(
                        f"""
                        <div class="quick-card">
                            <h4>{title}</h4>
                            <p>{description}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("Try this", key=f"qa_{i+idx}", use_container_width=True):
                        st.session_state.quick_command = {"type": "prompt", "text": prompt}
        st.markdown("---")


def display_booking_cards(bookings: list) -> None:
    """Render reservation cards for current or past bookings."""
    status_badge = {
        "confirmed": "✅ Confirmed",
        "cancelled": "❌ Cancelled",
        "completed": "🎉 Completed",
        "no_show": "⚠️ No Show",
    }

    for booking in bookings:
        row = st.container()
        header_cols = row.columns([3, 2, 1])

        with header_cols[0]:
            st.markdown(f"### {booking['restaurant_name']}")
            st.caption(f"{booking['cuisine']}")
            st.caption(booking["address"])

        with header_cols[1]:
            st.markdown(f"**Date:** {booking['reservation_date']}")
            st.markdown(f"**Time:** {booking['reservation_time']}")
            st.markdown(f"**Party:** {booking['party_size']} guests")

        with header_cols[2]:
            badge = status_badge.get(booking["status"], booking["status"].title())
            st.write(badge)

        if booking.get("special_requests"):
            st.caption(f"📝 {booking['special_requests']}")

        st.markdown("---")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """Primary Streamlit entry point."""
    initialize_app()
    init_session_state()

    if st.session_state.customer_id is None:
        render_login()
    else:
        render_authenticated_view()


if __name__ == "__main__":
    main()

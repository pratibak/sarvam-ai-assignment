"""
Orchestrator agent - coordinates LLM and tool calling.

This is the main agent that:
1. Receives user messages
2. Uses OpenAI to determine intent and select tools
3. Executes tools
4. Formats responses
"""

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from agents.prompts import get_orchestrator_system_prompt
from agents.tools import TOOL_SCHEMAS, execute_tool
from database.db_manager import save_conversation_message

# Load environment variables
load_dotenv()


class OrchestratorAgent:
    """
    Main orchestrator agent using OpenAI for tool calling.
    """

    def __init__(
        self,
        db_path: str,
        customer_id: int,
        customer_name: str,
        customer_phone: str,
        user_lat: float,
        user_lon: float,
    ):
        """
        Initialize orchestrator.

        Args:
            db_path: Database path
            customer_id: Current customer ID
            customer_name: Customer name
            customer_phone: Customer phone
            user_lat: User latitude
            user_lon: User longitude
        """
        self.db_path = db_path
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.customer_phone = customer_phone
        self.user_lat = user_lat
        self.user_lon = user_lon

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

        self.system_prompt = get_orchestrator_system_prompt(
            customer_name,
            customer_phone,
            user_lat,
            user_lon,
        )

        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        # Keep at least 5 prior conversational turns by default
        self.max_history_turns = int(os.getenv("CHAT_HISTORY_TURNS", "3"))

    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return response.
        """
        self.messages.append({"role": "user", "content": user_message})
        self._trim_history()

        try:
            save_conversation_message(
                self.db_path,
                self.customer_id,
                "user",
                user_message,
            )
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Warning: Failed to log user message: {exc}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except Exception as exc:
            return {
                "text": f"I apologize, but I encountered an error: {exc}. Please try again.",
                "error": str(exc),
            }

        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            return self._handle_tool_calls(assistant_message)

        response_text = assistant_message.content
        self.messages.append({"role": "assistant", "content": response_text})

        try:
            save_conversation_message(
                self.db_path,
                self.customer_id,
                "assistant",
                response_text,
            )
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Warning: Failed to log assistant message: {exc}")

        parsed_json = self._try_parse_json(response_text)

        self._trim_history()
        return {"text": response_text, "json": parsed_json}

    def _handle_tool_calls(self, assistant_message) -> Dict[str, Any]:
        """
        Handle tool calls from the assistant.
        """
        self.messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ],
            }
        )

        tool_results = []

        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            result = execute_tool(
                function_name,
                arguments,
                self.db_path,
                self.customer_id,
                self.user_lat,
                self.user_lon,
            )

            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(result),
                }
            )

            tool_results.append({"tool": function_name, "result": result})

        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )

        response_text = final_response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": response_text})
        self._trim_history()

        tool_names = [tr["tool"] for tr in tool_results]
        tool_used_str = ", ".join(tool_names) if tool_names else None

        try:
            save_conversation_message(
                self.db_path,
                self.customer_id,
                "assistant",
                response_text,
                tool_used=tool_used_str,
            )
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Warning: Failed to log assistant message with tools: {exc}")

        structured_data = self._extract_structured_data(tool_results)

        parsed_json = self._try_parse_json(response_text)

        self._trim_history()
        return {"text": response_text, "json": parsed_json, "tool_results": tool_results, **structured_data}

    @staticmethod
    def _try_parse_json(content: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse the assistant response as JSON.
        Returns None if parsing fails.
        """
        try:
            return json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return None

    def _trim_history(self) -> None:
        """Keep only the most recent conversation turns to reduce latency."""
        if self.max_history_turns <= 0 or len(self.messages) <= 1:
            return

        system_message = self.messages[0]
        others = self.messages[1:]

        kept: List[Dict[str, Any]] = []
        counted_turns = 0

        for message in reversed(others):
            kept.append(message)
            if message["role"] in {"user", "assistant"}:
                counted_turns += 1
            if counted_turns >= self.max_history_turns * 2:
                break

        kept.reverse()
        self.messages = [system_message] + kept

    def _extract_structured_data(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured data from tool results for UI rendering.
        """
        data: Dict[str, Any] = {}

        for tool_result in tool_results:
            tool_name = tool_result["tool"]
            result = tool_result["result"]

            if tool_name == "find_restaurants" and result.get("status") == "success":
                data["restaurants"] = result.get("results", [])
            elif tool_name == "make_reservation" and result.get("status") == "success":
                data["reservation"] = result.get("reservation")
                data["restaurant"] = result.get("restaurant")
                data["reservation_fee"] = result.get("reservation_fee")
                data["estimated_spend_per_person"] = result.get("estimated_spend_per_person")
                data["estimated_subtotal"] = result.get("estimated_subtotal")
                data["estimated_total_with_fee"] = result.get("estimated_total_with_fee")
            elif tool_name == "get_my_bookings" and result.get("status") == "success":
                data["bookings"] = result.get("bookings", [])
            elif tool_name == "get_daily_offers" and result.get("status") == "success":
                data["offers"] = result.get("offers", [])

        return data

    def reset_conversation(self) -> None:
        """Reset conversation history (keep system prompt)."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history."""
        return self.messages.copy()

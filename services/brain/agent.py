from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional

from .ollama_client import OllamaClient
from .memory import ConversationMemory
from .prompts import get_system_prompt
from .retriever import HybridRetriever
from .tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

MAX_REACT_STEPS = 8


def _extract_tool_call(text: str) -> tuple[str, dict] | None:
    """Extract a tool call JSON from LLM response.

    Handles nested braces by using brace-counting instead of regex.
    Looks for: {"tool": "...", "args": {...}}
    """
    # Find the start of a potential tool call
    idx = text.find('"tool"')
    if idx == -1:
        return None

    # Walk backward to find the opening brace
    start = text.rfind("{", 0, idx)
    if start == -1:
        return None

    # Walk forward with brace counting to find the matching close
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if "tool" in obj and "args" in obj:
                        return obj["tool"], obj["args"]
                except json.JSONDecodeError:
                    pass
                break

    # Fallback: try regex for simple cases
    m = re.search(
        r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{.*?\})\s*\}',
        text,
        re.DOTALL,
    )
    if m:
        try:
            return m.group(1), json.loads(m.group(2))
        except json.JSONDecodeError:
            return m.group(1), {}

    return None


class Agent:
    """ReAct agent loop: Observe → Think → Act → Observe ..."""

    def __init__(
        self,
        llm: OllamaClient,
        tools: List[BaseTool] | None = None,
        memory: ConversationMemory | None = None,
        max_steps: int = MAX_REACT_STEPS,
        retriever: HybridRetriever | None = None,
    ):
        self.llm = llm
        self.tools: Dict[str, BaseTool] = {}
        if tools:
            for t in tools:
                self.tools[t.name] = t
        self.memory = memory or ConversationMemory()
        self.max_steps = max_steps
        self.retriever = retriever
        self._system_prompt = get_system_prompt()

    def register_tool(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool

    def _tool_list_str(self) -> str:
        """Short tool listing for prompts."""
        return ", ".join(sorted(self.tools.keys()))

    @staticmethod
    def _truncate_output(text: str, max_len: int = 2000) -> str:
        """Truncate long tool output to keep context manageable."""
        if len(text) > max_len:
            return text[:max_len] + " [truncated]"
        return text

    def _get_rag_context(self, query: str) -> str:
        """Retrieve relevant knowledge base context if available."""
        if not self.retriever:
            return ""
        try:
            results = self.retriever.search(query, top_k=3)
            relevant = [(cid, payload, score) for cid, payload, score in results if score > 0.5]
            if not relevant:
                return ""
            fragments = [payload.get("text", "") for _, payload, _ in relevant]
            ctx = "\n---\n".join(fragments)
            return f"\nRelevant knowledge base context:\n{ctx}\n"
        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return ""

    async def run(self, user_input: str) -> str:
        self.memory.add("user", user_input)

        # RAG context injection
        rag_context = self._get_rag_context(user_input)

        history = self.memory.get_text_history(last_n=10)
        prompt = f"{self._system_prompt}\n{rag_context}\nConversation:\n{history}\n\nAssistant:"

        for step in range(self.max_steps):
            response = await self.llm.generate(prompt=prompt)
            response = response.strip()

            # Check if the response contains a tool call
            tool_call = _extract_tool_call(response)
            if tool_call is None:
                # No tool call — final answer
                self.memory.add("assistant", response)
                return response

            tool_name, tool_args = tool_call
            logger.info("Step %d: tool=%s args=%s", step + 1, tool_name, tool_args)

            # Execute tool
            result = await self._execute_tool(tool_name, tool_args)

            # Add tool interaction to context
            # Truncate very long outputs to keep context manageable
            output_text = self._truncate_output(result.output)

            tool_text = f'[Tool: {tool_name}({tool_args})] → {output_text}'
            self.memory.add("tool", tool_text)

            # Build next prompt — allow agent to continue reasoning or call another tool
            prompt = (
                f"{self._system_prompt}\n\n"
                f"Conversation:\n{self.memory.get_text_history(last_n=12)}\n\n"
                f"The tool '{tool_name}' returned the result above.\n"
                f"If the task is complete, respond to the user with the result.\n"
                f"If more steps are needed, call another tool.\n"
                f"Assistant:"
            )

        # Max steps reached
        final = await self.llm.generate(
            prompt=f"{prompt}\n\nYou have reached the maximum number of steps. Provide a final answer based on what you know."
        )
        self.memory.add("assistant", final.strip())
        return final.strip()

    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> ToolResult:
        tool = self.tools.get(name)
        if not tool:
            available = self._tool_list_str()
            return ToolResult(
                success=False,
                output=f"Unknown tool: '{name}'. Available tools: {available}",
            )
        try:
            logger.info("Executing tool=%s args=%s", name, args)
            return await tool.execute(**args)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e, exc_info=True)
            return ToolResult(success=False, output=f"Tool error: {e}")

    async def run_stream(self, user_input: str) -> AsyncIterator[Dict[str, Any]]:
        """Streaming ReAct loop. Yields dicts:
        - {"type": "tool", "name": "...", "status": "running|done", "output": "..."}
        - {"type": "token", "text": "..."}
        - {"type": "done", "full_text": "..."}
        """
        self.memory.add("user", user_input)

        rag_context = self._get_rag_context(user_input)
        history = self.memory.get_text_history(last_n=10)
        prompt = f"{self._system_prompt}\n{rag_context}\nConversation:\n{history}\n\nAssistant:"

        for step in range(self.max_steps):
            # Collect full response (need complete text to detect tool calls)
            full_response = ""
            async for token in self.llm.generate_stream(prompt=prompt):
                full_response += token

            full_response = full_response.strip()

            # Check for tool call
            tool_call = _extract_tool_call(full_response)
            if tool_call is None:
                # Final answer — yield already-collected text in word chunks
                self.memory.add("assistant", full_response)
                # Simulate streaming by yielding word-by-word
                words = full_response.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else " " + word
                    yield {"type": "token", "text": token}
                yield {"type": "done", "full_text": full_response}
                return

            tool_name, tool_args = tool_call
            logger.info("Stream step %d: tool=%s", step + 1, tool_name)
            yield {"type": "tool", "name": tool_name, "status": "running", "output": ""}

            result = await self._execute_tool(tool_name, tool_args)

            output_text = self._truncate_output(result.output)

            yield {"type": "tool", "name": tool_name, "status": "done", "output": output_text}

            tool_text = f'[Tool: {tool_name}({tool_args})] → {output_text}'
            self.memory.add("tool", tool_text)

            prompt = (
                f"{self._system_prompt}\n\n"
                f"Conversation:\n{self.memory.get_text_history(last_n=12)}\n\n"
                f"The tool '{tool_name}' returned the result above.\n"
                f"If the task is complete, respond to the user with the result.\n"
                f"If more steps are needed, call another tool.\n"
                f"Assistant:"
            )

        # Max steps — stream final
        final = ""
        final_prompt = f"{prompt}\n\nYou have reached the maximum number of steps. Provide a final answer based on what you know."
        async for token in self.llm.generate_stream(prompt=final_prompt):
            final += token
            yield {"type": "token", "text": token}
        self.memory.add("assistant", final.strip())
        yield {"type": "done", "full_text": final.strip()}

    async def chat(self, user_input: str) -> str:
        """Simple chat without tool execution."""
        self.memory.add("user", user_input)
        history = self.memory.get_text_history(last_n=10)
        prompt = f"{self._system_prompt}\n\nConversation:\n{history}\n\nAssistant:"
        response = await self.llm.generate(prompt=prompt)
        response = response.strip()
        self.memory.add("assistant", response)
        return response

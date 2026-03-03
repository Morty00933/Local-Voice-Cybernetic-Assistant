"""Chat history + input frame."""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable


class ChatFrame(ctk.CTkFrame):
    """Scrollable chat history with text input and send button."""

    def __init__(
        self,
        master,
        on_send: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_send = on_send

        # Chat history (read-only textbox)
        self.history = ctk.CTkTextbox(
            self,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(size=14),
        )
        self.history.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Input row
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.input_field = ctk.CTkEntry(
            input_frame,
            placeholder_text="Message...",
            font=ctk.CTkFont(size=14),
            height=40,
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.input_field.bind("<Return>", self._handle_enter)

        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            width=80,
            height=40,
            command=self._handle_send,
        )
        self.send_btn.pack(side="right")

    def _handle_enter(self, event) -> None:
        self._handle_send()

    def _handle_send(self) -> None:
        text = self.input_field.get().strip()
        if not text:
            return
        self.input_field.delete(0, "end")
        self._on_send(text)

    def append_message(self, role: str, text: str) -> None:
        """Add a message to the chat history."""
        self.history.configure(state="normal")
        if role == "user":
            prefix = "You"
        elif role == "assistant":
            prefix = "LVCA"
        elif role == "tool":
            prefix = "  [tool]"
        else:
            prefix = role

        self.history.insert("end", f"{prefix}: {text}\n\n")
        self.history.see("end")
        self.history.configure(state="disabled")

    def append_token(self, token: str) -> None:
        """Append a streaming token to the last line."""
        self.history.configure(state="normal")
        self.history.insert("end", token)
        self.history.see("end")
        self.history.configure(state="disabled")

    def start_assistant_message(self) -> None:
        """Start a new assistant message line."""
        self.history.configure(state="normal")
        self.history.insert("end", "LVCA: ")
        self.history.configure(state="disabled")

    def end_assistant_message(self) -> None:
        """End the assistant message line."""
        self.history.configure(state="normal")
        self.history.insert("end", "\n\n")
        self.history.see("end")
        self.history.configure(state="disabled")

    def set_input_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.input_field.configure(state=state)
        self.send_btn.configure(state=state)

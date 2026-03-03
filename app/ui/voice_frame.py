"""Voice recording button frame."""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable


class VoiceFrame(ctk.CTkFrame):
    """Push-to-talk voice button with recording indicator."""

    def __init__(
        self,
        master,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_start = on_start
        self._on_stop = on_stop
        self._recording = False

        self.mic_btn = ctk.CTkButton(
            self,
            text="MIC",
            width=60,
            height=40,
            fg_color="#333333",
            hover_color="#555555",
        )
        self.mic_btn.pack(side="left", padx=(0, 4))

        # Bind press/release for push-to-talk
        self.mic_btn.bind("<ButtonPress-1>", self._press)
        self.mic_btn.bind("<ButtonRelease-1>", self._release)

        self.indicator = ctk.CTkLabel(
            self,
            text="",
            width=16,
            font=ctk.CTkFont(size=12),
        )
        self.indicator.pack(side="left")

    def _press(self, event) -> None:
        if not self._recording:
            self._recording = True
            self.mic_btn.configure(fg_color="#CC3333", text="REC")
            self.indicator.configure(text="Recording...")
            self._on_start()

    def _release(self, event) -> None:
        if self._recording:
            self._recording = False
            self.mic_btn.configure(fg_color="#333333", text="MIC")
            self.indicator.configure(text="")
            self._on_stop()

    @property
    def is_recording(self) -> bool:
        return self._recording

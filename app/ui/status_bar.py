"""Status bar showing service health and GPU usage."""
from __future__ import annotations

import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    """Bottom bar: service status dots + optional GPU info."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=30, **kwargs)

        self._services = {}

        for name in ("Brain", "TTS", "STT"):
            dot = ctk.CTkLabel(
                self,
                text=f"  {name}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            dot.pack(side="left", padx=(8, 0))
            self._services[name.lower()] = dot

        self.gpu_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.gpu_label.pack(side="right", padx=8)

    def update_status(self, services: dict[str, bool]) -> None:
        """Update service status dots. services = {"brain": True, "tts": False, ...}"""
        for name, ok in services.items():
            dot = self._services.get(name)
            if dot:
                color = "#00CC66" if ok else "#CC3333"
                dot.configure(text_color=color)

    def set_gpu(self, text: str) -> None:
        self.gpu_label.configure(text=text)

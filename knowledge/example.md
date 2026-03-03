# LVCA — Local Voice Cybernetic Assistant

LVCA is a fully local Jarvis-like voice assistant running on a single machine with an RTX 3060 12GB GPU.

## Architecture

The system uses a microservices architecture with 4 Docker services:
- **STT** (Speech-to-Text): Faster Whisper large-v3-turbo
- **Brain**: ReAct agent with Qwen 2.5 7B, 25+ tools
- **TTS** (Text-to-Speech): Piper TTS (Russian voice)
- **Orchestrator**: Coordinates the STT → Brain → TTS pipeline

Plus a native **Desktop Agent** running on Windows (port 9100) for desktop control.

## Desktop Control

LVCA can control the desktop through tools:
- Launch/close applications
- Manage windows (focus, minimize, maximize)
- Type text, press hotkeys
- Take screenshots and analyze them
- Control volume and media playback
- Read/write clipboard
- Monitor system resources
- Send desktop notifications

## How to Use

1. `make setup` — download all required models
2. `make up` — start all Docker services
3. `make desktop-agent` — start the Desktop Agent (native Windows)
4. `make chat` — quick text chat test
5. `make app` — launch the desktop application with voice

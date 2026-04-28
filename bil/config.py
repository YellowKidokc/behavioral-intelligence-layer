"""Default endpoint configuration for BIL CLIs and clients.

These values are sensible defaults for the reference deployment (a Synology
NAS at ``192.168.1.177`` running BIL on port 8420 and Ollama on port 11434).
**Override them for your own network** either by editing this file once or by
passing the ``--host`` / ``--ollama`` / ``--bil`` flags on each CLI invocation.

Environment variables, when set, win over the constants below — handy for
running the same code on the NAS itself (``BIL_HOST=http://localhost:8420``)
versus a workstation pointing at the NAS over LAN.
"""
from __future__ import annotations

import os

# Default BIL HTTP server (used by bil.ingest and bil.llm_query --bil).
BIL_HOST = os.environ.get("BIL_HOST", "http://192.168.1.177:8420")

# Default Ollama endpoint (used by bil.llm_query --ollama).
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.1.177:11434")

# Default Ollama model (used by bil.llm_query --model).
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

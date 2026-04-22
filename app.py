"""
Dune Chatbot - Versión simple sin RAG externo
Usa datos básicos embebidos
"""

import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple greeting + basic info
GREETING = """
🤖 ¡Bienvenido a Dune Bot!

Soy el asistente oficial de Dune: Arrakis Dominion.

Puedo ayudarte con:
- 🌍 Historia y lore del universo Dune
- 🎮 Mecánicas y desarrollo del juego
- 📖 Documentación técnica

Pregúntame lo que quieras sobre el juego.
"""

# Basic responses
BASIC_INFO = {
    "juego": "Dune: Arrakis Dominion es un juego de estrategia y gestión de recursos ambientado en el universo de Dune. Controlas una Casa Menor en Arrakis.",
    "especia": "La Melange (especia) es el recurso más valioso del universo. Solo se encuentra en Arrakis y extiende la vida consciente.",
    "houses": "Las Grandes Casas incluyen: Atreides, Harkonnen, Corrino, y muchas Casas Menores.",
    "arrakis": "Arrakis es el tercer planeta del sistema Canopus, el único lugar donde se produce la Especia.",
    "fremen": "Los Fremen son los habitantes nativos del desierto de Arrakis.",
}

def get_response(question: str) -> str:
    """Get a simple response"""
    question = question.lower()
    
    for key, value in BASIC_INFO.items():
        if key in question:
            return value
    
    return GREETING

# Gradio interface
import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente oficial de Dune: Arrakis Dominion",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia?",
        "¿Who are the Great Houses?",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
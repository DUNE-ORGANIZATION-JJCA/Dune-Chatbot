"""
Dune Chatbot - Con RAG desde GitHub
"""

import os
import sys
import logging
import subprocess
from git import Repo

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CLONAR RAG DESDE GITHUB
# ============================================

RAG_PATH = os.path.join(os.path.dirname(__file__), "dune_rag")

def clone_rag():
    """Clona el RAG desde GitHub"""
    if not os.path.exists(RAG_PATH):
        logger.info("Clonando Dune-RAG...")
        try:
            Repo.clone_from(
                "https://github.com/DUNE-ORGANIZATION-JJCA/Dune-RAG.git",
                RAG_PATH,
                depth=1
            )
            logger.info("Dune-RAG clonado")
        except Exception as e:
            logger.error(f"Error: {e}")

# Intentar clonar
try:
    clone_rag()
except:
    pass

# Añadir al path
if RAG_PATH in sys.path:
    sys.path.insert(0, RAG_PATH)

# Intentar importar
try:
    if os.path.exists(RAG_PATH):
        sys.path.insert(0, RAG_PATH)
        from rag import_loader as rag_loader
        logger.info("RAG importado")
except Exception as e:
    logger.error(f"Error importando RAG: {e}")
    rag_loader = None

# ============================================
# RESPUESTAS
# ============================================

GREETING = """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente de Dune: Arrakis Dominion.
Puedo ayudarte sobre el juego, historia, y más.
"""

INFO = {
    "juego": "Dune: Arrakis Dominion es un juego de estrategia ambientado en Dune. Controlas una Casa Menor en Arrakis.",
    "especia": "La Melange es el recurso más valioso, solo se encuentra en Arrakis.",
    "houses": "Las Grandes Casas: Atreides, Harkonnen, Corrino, y más.",
    "arrakis": "Arrakis es el planeta desértico donde se produce la Especia.",
    "fremen": "Los Fremen son los nativos del desierto de Arrakis.",
}

def get_response(question: str) -> str:
    q = question.lower()
    for k, v in INFO.items():
        if k in q:
            return v
    return GREETING

# Gradio
import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune: Arrakis Dominion"
).launch(server_name="0.0.0.0", server_port=7860)
"""
Dune Chatbot - Con RAG desde GitHub
"""

import os
import sys
import logging
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

RAG_BASE = "/tmp/dune_rag"
RAG_DIR = os.path.join(RAG_BASE, "rag")

def clone_rag():
    """Clona el RAG desde GitHub"""
    if not os.path.exists(RAG_BASE):
        logger.info("Clonando Dune-RAG desde GitHub...")
        try:
            Repo.clone_from(
                "https://github.com/DUNE-ORGANIZATION-JJCA/Dune-RAG.git",
                RAG_BASE,
                depth=1
            )
            logger.info("Dune-RAG clonado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error clonado: {e}")
            return False
    return True

# Intentar clonar
clone_rag()

# Añadir path del RAG
if os.path.exists(RAG_DIR):
    sys.path.insert(0, RAG_DIR)

# ============================================
# IMPORTAR RAG
# ============================================

RAG_AVAILABLE = False
try:
    from loader import GitHubLoader, DuneConfig, REPO_FILES
    logger.info("RAG importado correctamente")
    RAG_AVAILABLE = True
except Exception as e:
    logger.error(f"Error importando RAG: {e}")
    raise

# ============================================
# RESPUESTAS
# ============================================

GREETING = """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente de Dune: Arrakis Dominion.
"""

INFO = {
    "juego": "Dune: Arrakis Dominion es un juego de estrategia ambientado en Dune.",
    "especia": "La Melange es el recurso más valioso, solo se encuentra en Arrakis.",
    "houses": "Las Grandes Casas: Atreides, Harkonnen, Corrino.",
    "arrakis": "Arrakis es el planeta desértico donde se produce la Especia.",
    "fremen": "Los Fremen son los habitantes nativos del desierto.",
}

def get_response(question: str, history=None) -> str:
    """Responde preguntas"""
    q = question.lower()
    
    for key, value in INFO.items():
        if key in q:
            return value
    
    if RAG_AVAILABLE:
        return "RAG conectado desde GitHub! Puedo ayudarte más."
    
    return GREETING

# Gradio
import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune: Arrakis Dominion"
).launch(server_name="0.0.0.0", server_port=7860)
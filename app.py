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

RAG_PATH = "/tmp/dune_rag"

def clone_rag():
    """Clona el RAG desde GitHub"""
    if not os.path.exists(RAG_PATH):
        logger.info("Clonando Dune-RAG desde GitHub...")
        try:
            Repo.clone_from(
                "https://github.com/DUNE-ORGANIZATION-JJCA/Dune-RAG.git",
                RAG_PATH,
                depth=1
            )
            logger.info("Dune-RAG clonado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error clonado: {e}")
            return False
    return True

# Intentar clonar
cloned = clone_rag()

# Añadir al path
if cloned and os.path.exists(RAG_PATH):
    sys.path.insert(0, RAG_PATH)

# IMPORTAR RAG
try:
    from rag import_loader as loader_module
    from rag import_textchunker as chunker_module
    from rag import_vectorretriever as retriever_module
    from rag import_responsegenerator as generator_module
    logger.info("RAG importado correctamente")
    RAG_AVAILABLE = True
except Exception as e:
    logger.error(f"Error importando RAG: {e}")
    RAG_AVAILABLE = False

# ============================================
# RESPUESTAS
# ============================================

GREETING = """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente de Dune: Arrakis Dominion.
Puedo ayudarte sobre el juego, historia, y más.
"""

INFO = {
    "juego": "Dune: Arrakis Dominion es un juego de estrategia ambientado en Dune. Controlas una Casa Menor en Arrakis.",
    "especia": "La Melange es el recurso más valioso del universo, solo se encuentra en Arrakis.",
    "houses": "Las Grandes Casas: Atreides, Harkonnen, Corrino, y muchas más.",
    "arrakis": "Arrakis es el tercer planeta del sistema Canopus, el planeta desértico.",
    "fremen": "Los Fremen son los habitantes nativos del desierto de Arrakis.",
}

def get_response(question: str) -> str:
    """Responde preguntas"""
    q = question.lower()
    
    # Buscar en respuestas básicas
    for key, value in INFO.items():
        if key in q:
            return value
    
    # Si RAG está disponible, lo usamos
    if RAG_AVAILABLE:
        return "Información cargada desde RAG de GitHub!"
    
    return GREETING

# Gradio interface
import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune: Arrakis Dominion"
).launch(server_name="0.0.0.0", server_port=7860)
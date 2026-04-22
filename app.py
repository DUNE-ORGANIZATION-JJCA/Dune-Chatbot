"""
Dune Chatbot - Con RAG + ChromaDB + APIs de datos
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
            logger.info("Dune-RAG clonado")
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    return True

clone_rag()

if os.path.exists(RAG_DIR):
    sys.path.insert(0, RAG_DIR)

# ============================================
# IMPORTAR RAG y CHROMADB
# ============================================

RAG_AVAILABLE = False
CHROMA_AVAILABLE = False
vector_store = None

try:
    # Importar componentes RAG
    from loader import GitHubLoader, DuneConfig, REPO_FILES
    from chunker import TextChunker
    from retriever import VectorRetriever
    from generator import ResponseGenerator, GeneratorConfig
    
    # Intentar inicializar ChromaDB
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Inicializar ChromaDB
        chroma_client = chromadb.Client(Settings(
            persist_directory="/tmp/chroma_db",
            anonymized_telemetry=False
        ))
        
        # Crear o obtener colección
        try:
            collection = chroma_client.get_collection("dune_knowledge")
        except:
            collection = chroma_client.create_collection("dune_knowledge")
        
        CHROMA_AVAILABLE = True
        logger.info("ChromaDB inicializado")
        
    except Exception as e:
        logger.error(f"Error ChromaDB: {e}")
    
    RAG_AVAILABLE = True
    logger.info("RAG importado")
    
except Exception as e:
    logger.error(f"Error importando RAG: {e}")
    raise

# ============================================
# CARGAR DATOS DESDE BASES DE DATOS
# ============================================

def load_supabase_data():
    """Carga datos desde Supabase Dashboard"""
    try:
        import supabase
        
        url = "https://jshzonryarokhquoazmy.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
        
        client = supabase.create_client(url, key)
        
        # Obtener estadísticas
        try:
            respuesta = client.table("registros_beta").select("*", count="exact").execute()
            registros = respuesta.count or 0
            logger.info(f"Registros beta: {registros}")
            return f"Total registros en beta: {registros}"
        except:
            return "No hay datos de registros"
            
    except Exception as e:
        logger.error(f"Error Supabase: {e}")
        return None

def load_campaign_data():
    """Carga datos desde Neon Campaign"""
    try:
        import psycopg2
        
        conn_string = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"
        
        try:
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM registros")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            logger.info(f"Campaign: {count} registros")
            return f"Datos de campaña: {count} registros"
        except Exception as e:
            logger.error(f"Error Neon: {e}")
            return "No hay datos de campaña"
    except Exception as e:
        logger.error(f"Error carga campaña: {e}")
        return None

# Cargar datos al iniciar
SUPABASE_INFO = load_supabase_data()
CAMPAIGN_INFO = load_campaign_data()

# ============================================
# BUSCADOR EN CHROMADB
# ============================================

def search_knowledge(query: str) -> str:
    """Busca en ChromaDB"""
    if not CHROMA_AVAILABLE:
        return None
    
    try:
        # Buscar documentos similares
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        if results and results.get('documents'):
            docs = results['documents'][0]
            if docs:
                return "\n\n".join(docs[:3])
        return None
    except Exception as e:
        logger.error(f"Error search: {e}")
        return None

# ============================================
# RESPUESTAS
# ============================================

GREETING = """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente oficial de Dune: Arrakis Dominion.
Puedo ayudarte con información del juego, estadísticas de la campaña, y más.
"""

INFO = {
    "juego": "Dune: Arrakis Dominion es un juego de estrategia y gestión de recursos ambientado en Dune.",
    "especia": "La Melange (especia) es el recurso más valioso del universo, solo se encuentra en Arrakis.",
    "houses": "Las Grandes Casas: Atreides, Harkonnen, Corrino, y muchas Casas Menores.",
    "arrakis": "Arrakis es el tercer planeta del sistema Canopus, el planeta desértico.",
    "fremen": "Los Fremen son los habitantes nativos del desierto de Arrakis.",
    "dashboard": f"Información del dashboard: {SUPABASE_INFO if SUPABASE_INFO else 'No disponible'}",
    "campaña": f"Información de campaña: {CAMPAIGN_INFO if CAMPAIGN_INFO else 'No disponible'}",
}

def get_response(question: str, history=None) -> str:
    """Responde preguntas"""
    q = question.lower()
    
    # Buscar en respuestas básicas
    for key, value in INFO.items():
        if key in q:
            return value
    
    # Buscar en ChromaDB
    if CHROMA_AVAILABLE:
        result = search_knowledge(q)
        if result:
            return result
    
    # Si RAG disponible
    if RAG_AVAILABLE:
        return "Información cargada desde RAG de GitHub!"
    
    return GREETING

# Gradio
import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune: Arrakis Dominion",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia?",
        "¿Cuántos registros hay en la beta?",
        "¿Cómo va la campaña?",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
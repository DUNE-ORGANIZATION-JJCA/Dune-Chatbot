"""
Dune Chatbot - Sistema RAG completo
Carga documentos desde GitHub + ChromaDB + APIs de datos
"""

import os
import sys
import logging
from git import Repo
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURACIÓN
# ============================================

GITHUB_ORG = "DUNE-ORGANIZATION-JJCA"
DOCUMENTOS_REPO = "Dune-Documentacion"
RAG_BASE = "/tmp/dune_rag"
CHROMA_DIR = "/tmp/chroma_db"

# Credenciales (NO exponer en producción)
SUPABASE_URL = "https://jshzonryarokhquoazmy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
NEON_CONN = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# ============================================
# CARGAR DOCUMENTOS DESDE GITHUB
# ============================================

def get_github_file(repo: str, path: str) -> str:
    """Obtiene archivo desde GitHub API"""
    url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/contents/{path}"
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Dune-Chatbot"})
        if response.status_code == 200:
            import base64
            data = response.json()
            content = data.get("content", "")
            if content:
                return base64.b64decode(content).decode("utf-8")
    except Exception as e:
        logger.error(f"Error getting {path}: {e}")
    return None

def load_game_documents():
    """Carga documentos del juego desde GitHub"""
    documents = []
    
    # Archivos de documentación del juego
    files = [
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Storytelling.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Manual_Tecnico.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_GDD_Recursos.md"),
    ]
    
    logger.info("Cargando documentos del juego...")
    
    for repo, path in files:
        content = get_github_file(repo, path)
        if content:
            # Extraer título del documento
            title = path.replace(".md", "").replace("_", " ")
            documents.append({
                "title": title,
                "content": content[:5000]  # Limitar tamaño
            })
            logger.info(f"Cargado: {path}")
    
    return documents

# ============================================
# CHROMADB
# ============================================

CHROMA_AVAILABLE = False
collection = None

def init_chromadb():
    """Inicializa ChromaDB y carga documentos"""
    global collection, CHROMA_AVAILABLE
    
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
        
        # Crear cliente
        chroma_client = chromadb.Client(Settings(
            persist_directory=CHROMA_DIR,
            anonymized_telemetry=False
        ))
        
        # Crear o obtener colección
        try:
            collection = chroma_client.get_collection("dune_knowledge")
            logger.info("Colección ChromaDB obtenida")
        except:
            collection = chroma_client.create_collection("dune_knowledge")
            logger.info("Colección ChromaDB creada")
        
        # Cargar documentos si colección vacía
        if collection.count() == 0:
            logger.info("Cargando documentos en ChromaDB...")
            
            # Cargar documentos del juego
            docs = load_game_documents()
            
            if docs:
                # Crear embeddings
                model = SentenceTransformer('all-MiniLM-L6-v2')
                texts = [d["content"] for d in docs]
                titles = [d["title"] for d in docs]
                
                # Generar embeddings
                embeddings = model.encode(texts, show_progress_bar=True)
                
                # Añadir a ChromaDB
                collection.add(
                    documents=texts,
                    ids=[f"doc_{i}" for i in range(len(texts))],
                    metadatas=[{"title": t} for t in titles]
                )
                
                logger.info(f"Documentos guardados en ChromaDB: {len(docs)}")
        
        CHROMA_AVAILABLE = True
        logger.info("ChromaDB inicializado correctamente")
        
    except Exception as e:
        logger.error(f"Error ChromaDB: {e}")
        CHROMA_AVAILABLE = False

# Inicializar ChromaDB
init_chromadb()

# ============================================
# CONSULTAS A BASES DE DATOS
# ============================================

def get_supabase_stats():
    """Obtiene estadísticas de Supabase Dashboard"""
    try:
        import supabase
        
        client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Contar registros
        try:
            r1 = client.table("registros_beta").select("*", count="exact").execute()
            registros = r1.count or 0
        except:
            registros = 0
        
        # Contar sesiones
        try:
            r2 = client.table("sesiones_web").select("*", count="exact").execute()
            sesiones = r2.count or 0
        except:
            sesiones = 0
        
        return f"Registros en beta: {registros}, Sesiones: {sesiones}"
        
    except Exception as e:
        logger.error(f"Error Supabase: {e}")
        return "No disponible"

def get_campaign_stats():
    """Obtiene estadísticas de Campaign (Neon)"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(NEON_CONN)
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT COUNT(*) FROM registros")
            count = cur.fetchone()[0]
        except:
            count = "No accesible"
        
        cur.close()
        conn.close()
        
        return f"Campaign: {count} registros"
        
    except Exception as e:
        logger.error(f"Error Campaign: {e}")
        return "No disponible"

# Cargar stats al iniciar
STATS_SUPABASE = get_supabase_stats()
STATS_CAMPAIGN = get_campaign_stats()

logger.info(f"Stats Supabase: {STATS_SUPABASE}")
logger.info(f"Stats Campaign: {STATS_CAMPAIGN}")

# ============================================
# RESPUESTAS DEL CHATBOT
# ============================================

def search_chromadb(query: str, n=3) -> str:
    """Busca en ChromaDB"""
    if not CHROMA_AVAILABLE or collection is None:
        return None
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n
        )
        
        if results and results.get('documents'):
            docs = results['documents'][0]
            if docs:
                return "\n\n".join([d[:800] for d in docs if d])
    except Exception as e:
        logger.error(f"Error search: {e}")
    
    return None

def get_response(question: str, history=None) -> str:
    """Responde preguntas"""
    q = question.lower()
    
    # === CONSULTAS ESPECÍFICAS ===
    
    # Dashboard / Beta
    if "beta" in q or "registro" in q or "dashboard" in q:
        return f"📊 Datos del Dashboard: {STATS_SUPABASE}"
    
    # Campaña
    if "campaña" in q or "campania" in q or "campaign" in q:
        return f"📈 Datos de Campaña: {STATS_CAMPAIGN}"
    
    # Juego / Historia / Lore
    if "juego" in q or "sobre" in q:
        result = search_chromadb("juego Arrakis Dominion")
        if result:
            return f"🎮 {result}"
    
    # Especia
    if "especia" in q or "melange" in q:
        result = search_chromadb("especia Melange Arrakis")
        if result:
            return f"🌟 {result}"
    
    # Casas
    if "casa" in q or "houses" in q or "atreides" in q or "harkonnen" in q:
        result = search_chromadb("Great Houses Atreides Harkonnen")
        if result:
            return f"🏰 {result}"
    
    # Fremen
    if "fremen" in q:
        result = search_chromadb("Fremen Arrakis")
        if result:
            return f"🏜️ {result}"
    
    # Recursos / Mecánicas
    if "recurso" in q or "mecanica" in q or "recurso" in q:
        result = search_chromadb("recursos sistema producción")
        if result:
            return f"⚙️ {result}"
    
    # Búsqueda general en ChromaDB
    result = search_chromadb(q)
    if result:
        return result
    
    # === RESPUESTA POR DEFECTO ===
    return """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente oficial de Dune: Arrakis Dominion.

Puedo ayudarte con:
- 📚 Historia y lore del universo Dune
- 🎮 Mecánicas y reglas del juego
- 📊 Estadísticas del dashboard (beta)
- 📈 Datos de la campaña
- 🏰 Las Grandes Casas

¡Pregúntame lo que quieras!"""

# ============================================
# INTERFAZ GRADIO
# ============================================

import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot - Arrakis Dominion",
    description="Asistente oficial del juego Dune: Arrakis Dominion",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia?",
        "¿Cuántos registros hay en la beta?",
        "¿Cómo va la campaña?",
        "Dime sobre las Grandes Casas",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
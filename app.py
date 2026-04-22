"""
Dune Chatbot - Sistema RAG inteligente con LLM
Carga documentos + ChromaDB + LLM para respuestas generativas
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
RAG_BASE = "/tmp/dune_rag"
CHROMA_DIR = "/tmp/chroma_db"

# Credenciales
SUPABASE_URL = "https://jshzonryarokhquoazmy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
NEON_CONN = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# HF Token
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ============================================
# CARGAR DOCUMENTOS DESDE GITHUB
# ============================================

def get_github_file(repo: str, path: str) -> str:
    url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/contents/{path}"
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Dune-Chatbot"})
        if response.status_code == 200:
            import base64
            data = response.json()
            content = data.get("content", "")
            if content:
                return base64.b64decode(content).decode("utf-8")
    except:
        pass
    return None

def load_game_documents():
    files = [
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Storytelling.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Manual_Tecnico.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_GDD_Recursos.md"),
    ]
    
    docs = []
    for repo, path in files:
        content = get_github_file(repo, path)
        if content:
            title = path.replace(".md", "").replace("_", " ")
            docs.append({"title": title, "content": content[:8000]})
            logger.info(f"Cargado: {path}")
    return docs

# ============================================
# CHROMADB
# ============================================

CHROMA_AVAILABLE = False
collection = None

def init_chromadb():
    global collection, CHROMA_AVAILABLE
    
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        
        chroma_client = chromadb.Client(chromadb.Settings(
            persist_directory=CHROMA_DIR,
            anonymized_telemetry=False
        ))
        
        try:
            collection = chroma_client.get_collection("dune_knowledge")
        except:
            collection = chroma_client.create_collection("dune_knowledge")
        
        if collection.count() == 0:
            docs = load_game_documents()
            if docs:
                model = SentenceTransformer('all-MiniLM-L6-v2')
                texts = [d["content"] for d in docs]
                titles = [d["title"] for d in docs]
                embeddings = model.encode(texts, show_progress_bar=True)
                collection.add(
                    documents=texts,
                    ids=[f"doc_{i}" for i in range(len(texts))],
                    metadatas=[{"title": t} for t in titles]
                )
                logger.info(f"Documentos guardados: {len(docs)}")
        
        CHROMA_AVAILABLE = True
        logger.info("ChromaDB inicializado")
        
    except Exception as e:
        logger.error(f"Error ChromaDB: {e}")

init_chromadb()

# ============================================
# LLM PARA GENERAR RESPUESTAS
# ============================================

LLM_AVAILABLE = False

def generate_with_llm(context: str, question: str) -> str:
    """Usa LLM para generar respuesta"""
    if not HF_TOKEN:
        return None
    
    try:
        import requests
        
        prompt = f"""Eres el asistente oficial de Dune: Arrakis Dominion.
Responde de forma clara y concisa en español (máximo 2-3 oraciones).

Información relevante:
{context}

Pregunta: {question}

Respuesta:"""

        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 256,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        # Usar API de推理
        response = requests.post(
            "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-8B-Instruct",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "").split("Respuesta:")[-1].strip()
        
    except Exception as e:
        logger.error(f"Error LLM: {e}")
    
    return None

# ============================================
# CONSULTAS A BASES DE DATOS
# ============================================

def get_supabase_stats():
    try:
        import supabase
        client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        r1 = client.table("registros_beta").select("*", count="exact").execute()
        r2 = client.table("sesiones_web").select("*", count="exact").execute()
        return f"📊 Beta: {r1.count or 0} registros | Sesiones: {r2.count or 0}"
    except:
        return "📊 Datos no disponibles"

def get_campaign_stats():
    try:
        import psycopg2
        conn = psycopg2.connect(NEON_CONN)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM registros")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return f"📈 Campaña: {count} registros"
    except:
        return "📈 Datos de campaña no disponibles"

STATS_SUPABASE = get_supabase_stats()
STATS_CAMPAIGN = get_campaign_stats()

# ============================================
# BUSCAR Y GENERAR RESPUESTA
# ============================================

def search_and_generate(query: str) -> str:
    """Busca en ChromaDB y usa LLM para generar respuesta"""
    
    # Buscar documentos relevantes
    if CHROMA_AVAILABLE and collection:
        try:
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            
            if results and results.get('documents'):
                docs = results['documents'][0]
                if docs:
                    context = "\n\n".join([d[:1500] for d in docs if d])
                    
                    # Intentar usar LLM
                    if HF_TOKEN:
                        llm_response = generate_with_llm(context, query)
                        if llm_response:
                            return llm_response
                    
                    # Si no hay LLM, devolver respuesta resumida
                    return f"Según la documentación: {context[:500]}..."
        except Exception as e:
            logger.error(f"Error search: {e}")
    
    return None

# ============================================
# RESPUESTAS DEL CHATBOT
# ============================================

def get_response(question: str, history=None) -> str:
    """Responde preguntas"""
    q = question.lower()
    
    # Consultas específicas a bases de datos
    if "beta" in q or "registro" in q:
        return STATS_SUPABASE
    
    if "campaña" in q or "campania" in q:
        return STATS_CAMPAIGN
    
    # Búsqueda en ChromaDB + LLM
    result = search_and_generate(q)
    if result:
        return result
    
    # Respuesta por defecto
    return """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente de Dune: Arrakis Dominion.
Puedo ayudarte con:
- 📚 Historia y lore
- 🎮 Mecánicas del juego
- 📊 Stats de la beta
- 📈 Stats de campaña

¡Pregúntame!"""

# ============================================
# INTERFAZ
# ============================================

import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune: Arrakis Dominion",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia?",
        "¿Cuántos jugadores hay?",
        "¿Cómo funciona el sistema de recursos?",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
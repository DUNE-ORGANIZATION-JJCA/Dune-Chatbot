"""
Dune Chatbot - Sistema RAG inteligente
"""

import os
import sys
import logging
from git import Repo
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIG
# ============================================

GITHUB_ORG = "DUNE-ORGANIZATION-JJCA"
RAG_BASE = "/tmp/dune_rag"
CHROMA_DIR = "/tmp/chroma_db"

SUPABASE_URL = "https://jshzonryarokhquoazmy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
NEON_CONN = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

HF_TOKEN = os.getenv("HF_TOKEN", "")

# ============================================
# CARGAR DOCS DE GITHUB
# ============================================

def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/contents/{path}"
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "DuneBot"})
        if r.status_code == 200:
            import base64
            return base64.b64decode(r.json()["content"]).decode("utf-8")
    except:
        pass
    return None

def load_docs():
    files = [
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Storytelling.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Manual_Tecnico.md"),
    ]
    docs = []
    for repo, path in files:
        c = get_github_file(repo, path)
        if c:
            docs.append({"title": path.replace(".md", ""), "content": c[:6000]})
    return docs

# ============================================
# CHROMADB
# ============================================

collection = None

def init_chromadb():
    global collection
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        
        client = chromadb.Client(chromadb.Settings(persist_directory=CHROMA_DIR, anonymized_telemetry=False))
        collection = client.get_or_create_collection("dune_knowledge")
        
        if collection.count() == 0:
            docs = load_docs()
            if docs:
                model = SentenceTransformer('all-MiniLM-L6-v2')
                embeddings = model.encode([d["content"] for d in docs])
                collection.add(
                    documents=[d["content"] for d in docs],
                    ids=[f"doc_{i}" for i in range(len(docs))],
                    metadatas=[{"title": d["title"]} for d in docs]
                )
                logger.info(f"Guardados {len(docs)} docs")
        logger.info("ChromaDB listo")
    except Exception as e:
        logger.error(f"Error: {e}")

init_chromadb()

# ============================================
# BASE DE DATOS
# ============================================

def get_stats():
    try:
        import supabase
        c = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        r = c.table("registros_beta").select("*", count="exact").execute()
        s = c.table("sesiones_web").select("*", count="exact").execute()
        return f"📊 Beta: {r.count or 0} | Sesiones: {s.count or 0}"
    except:
        return "No disponible"

def get_campaign():
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(NEON_CONN)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM registros")
        n = cur.fetchone()[0]
        cur.close()
        conn.close()
        return f"📈 Campaña: {n}"
    except:
        return "No disponible"

STATS = get_stats()
CAMPAIGN = get_campaign()

# ============================================
# RESPUESTA INTELIGENTE CON LLM
# ============================================

def get_llm_response(query: str) -> str:
    """Genera respuesta con LLM"""
    if not HF_TOKEN:
        return None
    
    # Sacar contexto relevante
    context = ""
    if collection and collection.count() > 0:
        try:
            results = collection.query(query_texts=[query], n_results=2)
            if results and results.get("documents"):
                context = "\n".join([d[:800] for d in results["documents"][0] if d])
        except:
            pass
    
    if not context:
        return None
    
    try:
        # Usar la API de chat con formato correcto
        import requests
        
        # Prompt simple
        prompt = f"""Eres el asistente de Dune: Arrakis Dominion.
Responde en español, máximo 3 oraciones cortas.

CONTEXTO:
{context}

 pregunta: {query}

Respuesta:"""
        
        response = requests.post(
            "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-8B-Instruct",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "do_sample": True
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"LLM respuesta: {data}")
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "").split("Respuesta:")[-1].strip()
                
    except Exception as e:
        logger.error(f"Error LLM: {e}")
    
    return None

# ============================================
# RESPUESTA PRINCIPAL
# ============================================

def get_response(question: str, history=None) -> str:
    q = question.lower()
    
    # Stats
    if "beta" in q or "registro" in q:
        return STATS
    if "campaña" in q or "campania" in q:
        return CAMPAIGN
    
    # Intentar LLM
    if HF_TOKEN:
        result = get_llm_response(question)
        if result:
            return result
    
    # Buscar en docs y resumir
    if collection and collection.count() > 0:
        try:
            results = collection.query(query_texts=[q], n_results=2)
            if results and results.get("documents"):
                doc = results["documents"][0][0][:600]
                # Resumir manualmente
                return f"Según la documentación: {doc[:400]}..."
        except:
            pass
    
    return """🤖 ¡Bienvenido!

Soy el asistente de Dune: Arrakis Dominion.

Pregúntame sobre:
- El juego y su historia
- Las Casas (Atreides, Harkonnen...)
- La especia Melange
- Stats de la beta y campaña

¿Qué quieres saber?"""

# ============================================
# GRADIO
# ============================================

import gradio as gr

gr.ChatInterface(
    fn=get_response,
    title="🤖 Dune Bot",
    description="Asistente de Dune",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia?",
        "¿Cuántos players hay?"
    ]
).launch(server_name="0.0.0.0", server_port=7860)
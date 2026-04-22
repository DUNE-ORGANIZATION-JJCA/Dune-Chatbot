"""
Dune Chatbot - RAG Mejorado y robusto
"""

import os
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
GITHUB_ORG = "DUNE-ORGANIZATION-JJCA"
HF_TOKEN = os.getenv("HF_TOKEN", "")

SUPABASE_URL = "https://jshzonryarokhquoazmy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzaHpvbnJ5YXJva2hxdW9hem15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2OTM2NDIsImV4cCI6MjA5MjI2OTY0Mn0.wOrhlsEHnFUHmrB0Hr85QR8rck6cDqr7CxAeae9vJj4"
NEON_CONN = "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# ==================== CARGAR DOCUMENTOS ====================

def get_file(repo, path):
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_ORG}/{repo}/contents/{path}",
            headers={"User-Agent": "DuneBot"}
        )
        if r.status_code == 200:
            import base64
            return base64.b64decode(r.json()["content"]).decode("utf-8")
    except:
        pass
    return None

def load_all_docs():
    """Carga todos los documentos del juego"""
    files = [
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Storytelling.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_Manual_Tecnico.md"),
        ("Dune-Documentacion", "Dune_Arrakis_Dominion_GDD_Recursos.md"),
    ]
    
    all_docs = []
    for repo, path in files:
        content = get_file(repo, path)
        if content:
            # Dividir en secciones por ##
            sections = content.split("## ")
            for sec in sections:
                if len(sec) > 100:
                    all_docs.append(sec[:2000])
    
    logger.info(f"Documentos cargados: {len(all_docs)}")
    return all_docs

DOCS = load_all_docs()

# ==================== BUSCAR ====================

def find_relevant_docs(query):
    """Busca documentos relevantes usando búsqueda simple"""
    query_lower = query.lower()
    results = []
    
    # Palabras clave del query
    keywords = [w for w in query_lower.split() if len(w) > 3]
    
    for doc in DOCS:
        doc_lower = doc.lower()
        score = sum(1 for kw in keywords if kw in doc_lower)
        if score > 0:
            results.append((score, doc))
    
    # Ordenar por puntuación
    results.sort(reverse=True)
    return [r[1] for r in results[:3]]

# ==================== LLM ====================

def ask_llm(context, question):
    """Pregunta al LLM"""
    if not HF_TOKEN:
        return None
    
    prompt = f"""Eres un asistente del juego Dune: Arrakis Dominion.
Responde de forma clara y concisa (máximo 2 oraciones).

Información del juego:
{context[:1500]}

Pregunta: {question}

Respuesta:"""

    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7
                }
            },
            timeout=60
        )
        
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "").split("Respuesta:")[-1].strip()
                
    except Exception as e:
        logger.error(f"LLM error: {e}")
    
    return None

# ==================== BASE DE DATOS ====================

def get_db_stats():
    try:
        import supabase
        c = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
        r = c.table("registros_beta").select("*", count="exact").execute()
        s = c.table("sesiones_web").select("*", count="exact").execute()
        return f"📊 Beta: {r.count or 0} jugadores | {s.count or 0} sesiones"
    except Exception as e:
        return "📊 Beta: datos no disponibles"

def get_campaign_stats():
    try:
        import psycopg2
        conn = psycopg2.connect(NEON_CONN)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM registros")
        n = cur.fetchone()[0]
        return f"📈 Campaña: {n} participantes"
    except:
        return "📈 Campaña: datos no disponibles"

STATS = get_db_stats()
CAMPAIGN = get_campaign_stats()

# ==================== RESPUESTA ====================

def respond(question, history=None):
    """Responde a la pregunta"""
    q = question.lower()
    
    # === CONSULTAS ESPECIALES ===
    if "beta" in q or "registro" in q or "jugador" in q:
        return STATS
    
    if "campaña" in q or "campania" in q:
        return CAMPAIGN
    
    if "cuántos" in q or "cuenta" in q:
        return f"{STATS}, {CAMPAIGN}"
    
    # === BUSCAR EN DOCUMENTOS ===
    docs = find_relevant_docs(q)
    
    if docs:
        context = "\n\n".join(docs[:2])
        
        # Intentar LLM primero
        llm_answer = ask_llm(context, question)
        if llm_answer and len(llm_answer) > 10:
            return llm_answer
        
        # Si LLM falla, devolver contexto resumido
        return f"Según la documentación del juego: {docs[0][:400]}..."
    
    # === RESPUESTA POR DEFECTO ===
    return """🤖 ¡Bienvenido a Dune Bot!

Soy el asistente oficial de Dune: Arrakis Dominion.

Puedo ayudarte con:
• Historia y lore del universo Dune
• Mecánicas del juego
• Stats de la beta y campaña
• Las Casas principales

¡Pregúntame lo que quieras!"""

# ==================== GRADIO ====================

import gradio as gr

gr.ChatInterface(
    fn=respond,
    title="🤖 Dune Bot - Arrakis Dominion",
    description="Asistente oficial del juego",
    examples=[
        "¿De qué trata el juego?",
        "¿Qué es la especia Melange?",
        "¿Cuántos jugadores hay en la beta?",
        "Dime sobre las Casas",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
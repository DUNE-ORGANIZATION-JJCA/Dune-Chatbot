"""
Dune Chatbot - Gradio Space
Usa Supabase pgvector + HF Inference
"""

import os
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")

NEON_CONN = os.getenv(
    "NEON_CONN",
    "postgresql://neondb_owner:npg_u4HxQmsKZMG1@ep-jolly-glade-alwj6pos-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"
)

# ==================== DATABASE ====================
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer

# Cache global
_model = None
_db_conn = None


def get_model():
    """Cargar modelo de embeddings"""
    global _model
    if _model is None:
        logger.info("Cargando modelo de embeddings...")
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def get_db():
    """Conexión a la base de datos"""
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        _db_conn = psycopg2.connect(NEON_CONN)
    return _db_conn


def search_docs(query, top_k=3):
    """Buscar documentos relevantes"""
    model = get_model()
    
    # Embed query
    emb = model.encode(query).tolist()
    emb = np.array(emb)
    emb = emb / np.linalg.norm(emb)
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT text, 1 - (embedding <=> %s::vector) as sim
        FROM dune_knowledge
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    ''', (emb.tolist(), emb.tolist(), top_k))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "text": row[0][:500],
            "score": row[1]
        })
    
    return results


# ==================== LLM ====================

def ask_llm(context, question):
    """Pregunta al LLM"""
    if not HF_TOKEN:
        return None
    
    prompt = f"""Eres Arthur, el Custodio del Desierto.
Respondes preguntas sobre el juego Dune: Arrakis Dominion.
Sé detallado pero conciso.

Contexto:
{context[:2000]}

Pregunta: {question}

Responde usando EXCLUSIVAMENTE la información del contexto."""

    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 300,
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "").split("Pregunta:")[-1].strip()
                
    except Exception as e:
        logger.error(f"LLM error: {e}")
    
    return None


# ==================== RESPOND ====================

def respond(question, history=None):
    """Responde a la pregunta"""
    if not question or question.strip() == "":
        return "El desierto espera tus palabras. ¿Qué deseas saber?"
    
    # Buscar documentos relevantes
    results = search_docs(question)
    
    if results:
        # Construir contexto
        context = "\n\n".join([r["text"] for r in results])
        
        # Pedir al LLM
        answer = ask_llm(context, question)
        
        if answer and len(answer) > 10:
            return answer
        
        # Fallback: devolver contexto
        return f"Según la documentación: {results[0]['text'][:300]}..."
    
    # Respuesta por defecto
    return """🦊 ¡Bienvenido a Dune Bot!

Soy el asistente oficial de Dune: Arrakis Dominion.

Puedo ayudarte con:
• Historia y lore del universo Dune
• Mecánicas del juego
• Las Casas principales
• Cómo jugar y ganar

¡Pregúntame lo que quieras!"""


# ==================== GRADIO ====================

import gradio as gr

gr.ChatInterface(
    fn=respond,
    title="🦊 Arthur - El Custodio del Desierto",
    description="Asistente oficial de Dune: Arrakis Dominion",
    examples=[
        "¿Cómo se gana el juego?",
        "Dime sobre las Casas",
        "¿Qué unidades tiene Atreides?",
        "¿Cómo funciona la especia?",
    ]
).launch(server_name="0.0.0.0", server_port=7860)
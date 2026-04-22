"""
Dune Chatbot - Aplicación principal con Gradio + RAG

Importa RAG desde GitHub como paquete pip y usa HuggingFace para generar respuestas.
"""

import os
import sys
import logging
import subprocess
from typing import List, Dict, Any
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# INSTALAR RAG DESDE GITHUB
# ============================================

def install_rag_from_github():
    """Instala el RAG desde GitHub como paquete pip"""
    import subprocess
    import sys
    
    try:
        # Instalar como paquete editable desde GitHub
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "git+https://github.com/DUNE-ORGANIZATION-JJCA/Dune-RAG.git", "--quiet", "--no-deps"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            logger.info("Dune-RAG instalado correctamente")
        else:
            logger.warning(f"Error instalando RAG: {result.stderr}")
            raise Exception("Install failed")
    except Exception as e:
        logger.error(f"Error instalando RAG: {e}")
        raise

# Intentar instalar primero
try:
    install_rag_from_github()
except Exception as e:
    logger.warning(f"Instalación automática falló: {e}")

# Importar componentes RAG
try:
    from rag import (
        DuneConfig,
        GitHubLoader,
        TextChunker,
        VectorRetriever,
        ResponseGenerator,
        REPO_FILES,
        RetrieverConfig,
        GeneratorConfig
    )
    logger.info("RAG importado correctamente")
except ImportError as e:
    logger.error(f"Error importando RAG: {e}")
    raise

# Importar Gradio
import gradio as gr


# ============================================
# CONFIGURACIÓN
# ============================================

@dataclass
class ChatbotConfig:
    model_id: str = "meta-llama/Llama-3.1-8B-Instruct"
    use_quantized: bool = True
    n_retrieved_docs: int = 5
    chunk_size: int = 500
    title: str = "🤖 Dune Bot - Asistente de Arrakis Dominion"
    description: str = """¡Bienvenido! Soy el asistente oficial de Dune: Arrakis Dominion.
        
Puedo ayudarte con:
- 🌍 Historia y lore del universo Dune
- 🎮 Mecánicas y desarrollo del juego
- 📊 Estadísticas de la campaña y dashboard
- 💰 Información de la tienda
- 📖 Documentación técnica

¡Ask anything!"""


# ============================================
# CHATBOT
# ============================================

class DuneChatbot:
    def __init__(self, config: ChatbotConfig = None):
        self.config = config or ChatbotConfig()
        self.retriever = None
        self.generator = None
        self.chunker = None
        self.dune_config = None
        self._initialized = False
        self._knowledge_loaded = False
    
    def initialize(self, force_reload: bool = False):
        """Inicializa todos los componentes"""
        if self._initialized and not force_reload:
            return
        
        logger.info("Inicializando DuneChatbot...")
        
        # Config
        self.dune_config = DuneConfig()
        self.chunker = TextChunker()
        self.retriever = VectorRetriever()
        self.retriever.initialize()
        
        # Cargar conocimiento
        if not self._knowledge_loaded or force_reload:
            self._load_knowledge(force_reload)
        
        # LLM
        from rag.generator import GeneratorConfig
        
        self.llm_config = GeneratorConfig(
            model_id=self.config.model_id,
            use_quantized=self.config.use_quantized
        )
        
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            self.llm_config.huggingface_token = hf_token
        
        self.generator = ResponseGenerator(self.llm_config)
        self.generator.initialize()
        
        self._initialized = True
        logger.info("DuneChatbot inicializado correctamente!")
    
    def _load_knowledge(self, force_reload: bool = False):
        """Carga conocimiento desde GitHub"""
        from rag.chunker import process_documents
        
        stats = self.retriever.get_stats()
        if not force_reload and stats.get("document_count", 0) > 0:
            logger.info(f"Ya hay {stats['document_count']} documentos")
            self._knowledge_loaded = True
            return
        
        logger.info("Cargando conocimiento desde GitHub...")
        
        loader = GitHubLoader("Dune-Documentacion", self.dune_config)
        documents = {}
        
        for repo_name, files in REPO_FILES.items():
            logger.info(f"Cargando de {repo_name}...")
            repo_loader = GitHubLoader(repo_name, self.dune_config)
            
            for file_path in files:
                content = repo_loader.get_file_content(file_path)
                if content:
                    documents[f"{repo_name}/{file_path}"] = content
                    logger.info(f"  ✓ {file_path}")
        
        if documents:
            chunks = process_documents(documents, self.chunker)
            self.retriever.add_documents(chunks)
            self._knowledge_loaded = True
            logger.info(f"Conocimiento cargado: {len(chunks)} chunks")
    
    def chat(self, message: str, history: List = None) -> str:
        """Procesa un mensaje"""
        if not self._initialized:
            self.initialize()
        
        message = message.strip()
        if not message:
            return "Por favor, ingresa una pregunta."
        
        logger.info(f"Pregunta: {message[:100]}...")
        
        docs = self.retriever.retrieve(message, n_results=self.config.n_retrieved_docs)
        response = self.generator.generate(question=message, documents=docs)
        
        return response


# ============================================
# INTERFAZ GRADIO
# ============================================

chatbot = DuneChatbot()
chatbot.initialize()

def chat_fn(message: str, history: List) -> str:
    return chatbot.chat(message, history)

gr.ChatInterface(
    fn=chat_fn,
    title=chatbot.config.title,
    description=chatbot.config.description,
    chatbot=gr.Chatbot(height=500, show_copy_button=True),
    textbox=gr.Textbox(placeholder="Ask me anything about Dune..."),
    examples=[
        "¿De qué trata el juego?",
        "¿Who are the Great Houses?",
        "¿Cómo funciona el sistema de recursos?",
        "Tell me about the Fremen"
    ]
).launch(server_name="0.0.0.0", server_port=7860, share=True)
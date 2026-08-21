"""Regulatory RAG — indexação e busca semântica local sobre o corpus da LGPD.

Pipeline 100% local (sem chamada de API paga):
    corpus/*.txt --(corpus_loader)--> chunks --(sentence-transformers)--> embeddings
    --(ChromaDB PersistentClient)--> índice em disco (`data/`) --(query)--> RAGQueryResult

Uso:
    from core.regulatory_rag.index import build_index, query

    build_index()                       # gera/atualiza o índice em core/regulatory_rag/data/
    result = query("o que é dado sensível?", k=3)
    for chunk in result.chunks:
        print(chunk.article, chunk.score, chunk.text[:80])

O modelo de embeddings ("paraphrase-multilingual-MiniLM-L12-v2") e o cliente
ChromaDB são carregados de forma preguiçosa (lazy) e cacheados em nível de
módulo, para que os testes que não precisam deles (parsing de corpus) não
paguem o custo de importar/baixar o modelo.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from shared.schemas import RAGQueryResult, RegulatoryChunk

from core.regulatory_rag.corpus_loader import CorpusChunk, load_corpus

logger = logging.getLogger(__name__)

MODULE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = MODULE_DIR / "corpus"
DEFAULT_DATA_DIR = MODULE_DIR / "data"
COLLECTION_NAME = "lgpd_regulatory_corpus"

# Modelo leve, multilíngue (inclui PT-BR), adequado para busca semântica local
# em CPU sem exigir GPU nem chave de API.
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_embedding_model: Any = None  # cache do SentenceTransformer carregado


class ModelUnavailableError(RuntimeError):
    """Levantado quando o modelo de embeddings não pôde ser carregado/baixado.

    Tipicamente por falta de rede/timeout no primeiro download do peso do
    modelo pelo `sentence-transformers`. O restante do módulo (parsing de
    corpus) continua funcional mesmo quando este erro ocorre.
    """


def _get_embedding_model() -> Any:
    """Carrega (uma vez) e cacheia o SentenceTransformer usado para embeddings."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - dependência ausente
            raise ModelUnavailableError(
                "Pacote 'sentence-transformers' não está instalado no venv."
            ) from exc
        try:
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as exc:  # download/timeout/rede
            raise ModelUnavailableError(
                f"Falha ao carregar/baixar o modelo '{EMBEDDING_MODEL_NAME}': {exc}"
            ) from exc
    return _embedding_model


def _get_client(persist_dir: str | Path) -> Any:
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - dependência ausente
        raise ModelUnavailableError("Pacote 'chromadb' não está instalado no venv.") from exc
    return chromadb.PersistentClient(path=str(persist_dir))


def _chunk_id(index: int, chunk: CorpusChunk) -> str:
    article_slug = (chunk["article"] or "na").replace(" ", "").replace("º", "")
    return f"chunk-{index:03d}-art{article_slug}"


_DISCLAIMER_PREFIX = "# Resumo ilustrativo"


def _embedding_text(chunk: CorpusChunk) -> str:
    """Texto usado para GERAR o embedding — diferente do texto armazenado/retornado.

    Todo chunk do corpus começa com a mesma linha de cabeçalho padrão de
    paráfrase ("# Resumo ilustrativo do Art. X da LGPD... paráfrase para fins
    de demonstração técnica, não substitui..."), que é quase idêntica entre
    todos os chunks (só o número do artigo muda). Medido empiricamente: manter
    esse cabeçalho no texto embedado faz com que ele domine a similaridade de
    cosseno (frase longa repetida em todos os documentos), afogando o sinal
    distintivo de cada artigo e degradando o ranking (ex.: perguntas sobre
    "dado sensível" retornavam artigos de segurança/incidente em vez do
    artigo de definições/bases legais).

    Por isso, para fins de EMBEDDING (nunca para exibição — o texto completo
    com o disclaimer continua sendo o `document`/`RegulatoryChunk.text`
    armazenado e retornado por `query()`), removemos essa linha e prefixamos
    o `tema` do chunk (curto e altamente discriminativo, ex. "Definições
    (dado pessoal, dado sensível, anonimização, tratamento)"), o que produz
    embeddings muito mais separáveis entre artigos.
    """
    body_lines = [
        line for line in chunk["text"].splitlines() if not line.strip().startswith(_DISCLAIMER_PREFIX)
    ]
    body = "\n".join(body_lines).strip()
    tema = chunk["tema"] or ""
    return f"{tema}\n\n{body}".strip()


def build_index(persist_dir: str | None = None) -> int:
    """Constrói (ou reconstrói) o índice ChromaDB local a partir de `corpus/`.

    Lê todos os arquivos `.txt` de `core/regulatory_rag/corpus/`, gera
    embeddings com sentence-transformers e persiste no ChromaDB em
    `persist_dir` (padrão: `core/regulatory_rag/data/`).

    Retorna o número de chunks indexados.

    Levanta `ModelUnavailableError` se o modelo de embeddings não puder ser
    carregado (ex.: sem rede para o primeiro download).
    """
    persist_path = Path(persist_dir) if persist_dir else DEFAULT_DATA_DIR
    persist_path.mkdir(parents=True, exist_ok=True)

    chunks = load_corpus(CORPUS_DIR)
    if not chunks:
        raise RuntimeError(f"Nenhum arquivo de corpus encontrado em {CORPUS_DIR}")

    model = _get_embedding_model()
    documents = [c["text"] for c in chunks]  # texto completo (com disclaimer) — armazenado/exibido
    embedding_texts = [_embedding_text(c) for c in chunks]  # texto reduzido — só para embedding
    embeddings = model.encode(embedding_texts, show_progress_bar=False).tolist()

    client = _get_client(persist_path)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # coleção ainda não existia — ok
    # "paraphrase-multilingual-MiniLM-L12-v2" (como a maioria dos modelos
    # sentence-transformers) foi treinado para similaridade de cosseno — usar
    # a distância L2 padrão do Chroma degrada bastante a qualidade do ranking
    # para embeddings não normalizados. Forçamos o espaço "cosine" na coleção.
    collection = client.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    ids = [_chunk_id(i, c) for i, c in enumerate(chunks)]
    metadatas = [
        {"source": c["source"], "article": c["article"] or "", "tema": c["tema"] or ""}
        for c in chunks
    ]

    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    logger.info("Regulatory RAG: indexados %d chunks em %s", len(chunks), persist_path)
    return len(chunks)


def query(text: str, k: int = 3) -> RAGQueryResult:
    """Busca os `k` chunks regulatórios mais relevantes para `text`.

    Requer que `build_index()` já tenha sido executado (usa o índice
    persistido no diretório padrão `core/regulatory_rag/data/`).

    Retorna um `shared.schemas.RAGQueryResult` com os chunks ordenados por
    relevância (score de similaridade, maior é melhor).
    """
    client = _get_client(DEFAULT_DATA_DIR)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "Índice regulatório não encontrado ou vazio. Rode build_index() antes de query()."
        ) from exc

    model = _get_embedding_model()
    query_embedding = model.encode([text]).tolist()

    n_results = max(1, min(k, collection.count()))
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    chunks: list[RegulatoryChunk] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Coleção usa espaço "cosine" (ver build_index): distância de cosseno do
        # Chroma é (1 - similaridade_de_cosseno), então a similaridade é só a
        # inversão direta — monotônica e diretamente interpretável.
        similarity = 1.0 - float(dist)
        chunks.append(
            RegulatoryChunk(
                source=meta.get("source", ""),
                article=meta.get("article") or None,
                text=doc,
                score=round(similarity, 4),
            )
        )

    return RAGQueryResult(query=text, chunks=chunks)

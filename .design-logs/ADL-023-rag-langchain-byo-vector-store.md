# ADL-023: RAG Cache con LangChain, Qdrant por defecto y BYO Vector Store

**Fecha:** 2026-04-24
**Estado:** Activo
**Área:** Arquitectura — Vector Store / RAG
**Autor:** AI Session (Feature 005 — Foundational)
**Supersede parcialmente:** ADL-010 (RAG diferido), ADL-007 (Chroma + Vanna — archivado)

---

## Contexto

ADL-010 difirió toda la infraestructura RAG post-MVP porque:
- LangChain no estaba en el stack.
- La estrategia de embeddings no estaba decidida.
- Vanna (el vehículo original) fue descartada por ADL-009.

Feature 005 activa RAG como **caché semántico de widgets**: en vez de re-generar código cada vez que el usuario repite una consulta similar, el pipeline consulta primero un vector store y devuelve la sugerencia si el score supera 0.85. La decisión de activar o no el caché es transparente para el usuario (la sugerencia aparece como tarjeta `CacheReuseSuggestion` en el chat).

---

## Decisión

### Stack

| Componente | Elección | Justificación |
|---|---|---|
| Capa de abstracción | **LangChain** (`langchain-core`, `langchain-community`) | Interfaz única `VectorStore`; permite swapping de provider sin cambiar lógica de negocio |
| Provider por defecto | **Qdrant** (`langchain-qdrant`, `qdrant-client`) | Open source, se levanta con Docker Compose, HTTP API robusta, filtros por payload nativos |
| Embeddings | **text-embedding-3-small** vía **LiteLLMEmbeddings** | Multilingüe, 1536 dim, barato (~$0.02/1M tokens). Rutar por LiteLLM mantiene la abstracción de proveedor del ADL-006 |
| Metadata espejo | **SQLite** (`widget_cache_entries`) | Invalidación por SQL rápida sin depender de disponibilidad del vector store; analytics locales |
| Cifrado de credenciales BYO | **Fernet + SHA-256** (`cryptography`) | AES-256 simétrico; clave en env var; derivación determinística del hex input del usuario |

### Patrón de implementación

```
Prompt → CacheService.search()
           ├─ hit ≥ 0.85 → CacheReuseSuggestion al chat
           └─ miss        → pipeline LLM normal
                             → tras éxito: CacheService.index()
```

**Filtros obligatorios en toda búsqueda** (evitan cross-session leakage):
- `session_id == current_session`
- `connection_id == current_connection`
- `data_schema_hash == sha256(schema_actual)`
- `invalidated_at IS NULL`

**Dual-store**: el vector store guarda embeddings + payload mínimo; SQLite guarda metadata completa. La invalidación corre primero en SQLite (fast path); el delete del vector point es best-effort con fallback graceful.

### BYO Vector Store

El `vector_store_factory.py` soporta cinco providers vía imports lazy:
- **Qdrant** (default, Docker)
- **Chroma** (`langchain-chroma`, opcional)
- **Pinecone** (`langchain-pinecone`, opcional)
- **Weaviate** (`langchain-weaviate`, opcional)
- **PGVector** (`langchain-postgres`, opcional)

Las credenciales BYO se cifran con Fernet antes de persistir en `vector_store_configs`. Nunca se loguean ni se retornan por API.

### Degradación graceful (FR-013)

Si Qdrant no está disponible:
- `bootstrap.ensure_widget_cache_collection()` loguea warning y continúa — la app arranca igual.
- `CacheService.search()` retorna `[]` ante cualquier excepción.
- `CacheService.index()` loguea warning y no falla — el widget se genera normalmente.
- La invalidación por SQLite queda activa aunque el delete del vector point falle.

---

## Justificación

- **LangChain como capa**: abstraer el vector store evita que el código de negocio conozca detalles de Qdrant, Pinecone, etc. El cambio de provider futuro es una línea en la config, no una refactorización.
- **Qdrant por defecto sobre Chroma**: Qdrant tiene HTTP API, soporte de filtros por payload nativos (crítico para nuestros 4 filtros obligatorios), y es más adecuado para entornos Docker que Chroma (que maneja su propio proceso). ADL-007 eligió Chroma; con Vanna fuera del stack esa decisión no tiene continuidad.
- **LiteLLMEmbeddings sobre cliente OpenAI directo**: mantiene la abstracción de proveedor ya establecida en ADL-006. Si el usuario cambia de OpenAI a Anthropic, los embeddings también migran sin cambios de código.
- **SQLite espejo**: el vector store puede caerse; la metadata en SQLite garantiza que la invalidación semántica es posible aunque el provider no responda.
- **Score umbral 0.85**: elegido en Clarify Q2. Prioriza precisión sobre recall para evitar sugerencias falsas positivas.

---

## Consecuencias

### ✅ Positivas

- Pipeline de generación más rápido en prompts repetidos o similares.
- Usuarios no necesitan configurar nada para tener caché (Qdrant levanta con Docker Compose).
- BYO vector store es progresivo: funciona sin configuración adicional, extensible si el usuario lo necesita.
- Degradación graceful protege contra caída de Qdrant en producción.

### ⚠️ Trade-offs aceptados

- **Nueva dep de red en Docker Compose**: Qdrant como servicio adicional. Si el usuario no tiene Docker, el caché está deshabilitado (graceful).
- **`VECTOR_STORE_ENCRYPTION_KEY` es requerida** para BYO — si no está seteada, la operación aborta con RuntimeError claro. Para el Qdrant default no es necesaria.
- **`text-embedding-3-small` fijado en config**: cambiar el modelo requiere reindexar toda la colección. Documentado en `.env.example`.
- **LRU cache in-memory en `LiteLLMEmbeddings`**: por-proceso, no por-request. En contextos multi-worker puede generar llamadas duplicadas al proveedor de embeddings. Aceptable en MVP con uvicorn single-worker.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|---|---|
| **Chroma (ADL-007)** | Sin HTTP API nativa (process-embedded); filtros por metadata menos potentes. Sin continuidad con Vanna (descartada ADL-009). |
| **FAISS in-process** | Sin persistencia entre reinicios, sin filtros por payload, no apto para BYO. |
| **pgvector en la SQLite existente** | SQLite no soporta extensiones; pgvector requiere PostgreSQL. Cambio de DB principal fuera de alcance de esta feature. |
| **Embeddings directos con OpenAI SDK** | Rompe la abstracción de proveedor de ADL-006. LiteLLM ya gestiona las claves y el routing. |

---

## Decisiones Relacionadas

- **ADL-006** — LiteLLM como gateway: LiteLLMEmbeddings extiende este patrón a embeddings.
- **ADL-007** — Chroma RAG (archivado): este ADL lo reemplaza. Qdrant vence por API y filtros.
- **ADL-010** — RAG diferido: **supersedida** por este ADL. El caché se activa en Feature 005.
- **ADL-003** — SQLite como estado de app: `widget_cache_entries` sigue este patrón (metadata en SQLite, no en el vector store).

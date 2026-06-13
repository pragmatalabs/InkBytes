# Funcionalidades del Sistema

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

InkBytes tiene dos audiencias: el **lector/suscriptor** (frontend Reader) y el **operador/admin** (Backoffice). Entre ambos corre el pipeline automático Messor→Curator.

## Para el lector (Reader)

### Feed de eventos
La home (`/`) muestra eventos publicados con ranking *global-first* (ADR-0017): los eventos con al menos un outlet global reciben un bonus de frescura de +6 h. Dos layouts: editorial (tira "Latest" top-20, top story, secundarias en 2 columnas, stream con divisor "Regional") y lista plana filtrada. Filtros cliente de idioma/categoría/búsqueda persistidos en `localStorage`. Auto-refresh cada 20 min.

### Página de evento
`/event/[id]` muestra la síntesis Markdown, el *evidence rail* (citas 2–8 con enlace a la fuente), entidades, eventos relacionados (por solapamiento de entidades + topic) y un *media rail* de video. Botón de compartir (Web Share API con fallback a portapapeles).

### Trending topics y drill-down
`GET /topics/trending` alimenta chips de temas; al elegir uno se navega a `/?topic=` (filtrado server-side). Junk filtrado y cuasi-duplicados colapsados (ADR-0027).

### Grafo de entidades
`/entities` renderiza un grafo de fuerza de co-ocurrencia de entidades, SVG hecho a mano (simulación física propia). Permite arrastrar nodos, filtrar por tipo (PERSON/ORG/LOC/EVENT/OTHER), buscar y ver las páginas conectadas a cada entidad.

### Asistente de chat (RAG)
Botón flotante → overlay de chat sobre el corpus de **eventos publicados** (`POST /ask` → Curator, ADR-0022). Modos: `resume` (digest del día), `top10`, `chat` (Q&A libre con recuperación por embeddings). Renderiza `answer_md` con marcadores de cita `[n]` enlazados a `/event/{id}`.

### PWA
Manifest instalable (`display: standalone`), banner de instalación (Android intercepta `beforeinstallprompt`; iOS muestra instrucciones Share→"Add to Home Screen"). Daily splash móvil una vez/24 h con racha de lectura local y resumen "qué hay nuevo".

## Para el operador (Backoffice)

### Gestión de outlets
CRUD de outlets (`role:operator`), importación masiva con preview/apply, exportación. Cada outlet define región, idioma, vertical, prioridad, `feed_url` (RSS), `min_word_count` y `pulse` (outlet de breaking).

### Disparo y monitoreo de cosecha
`POST /scraping/trigger` crea un `ScrapingJob` y despacha `RunScrapingWorker`, que invoca la API de Messor (`/api/scrape/trigger`) local o vía SSH. Vistas de status, stream SSE de logs en vivo (`/scraping/{id}/stream`), historial de corridas y resultados por sesión.

### Moderación de eventos y páginas
`/moderation` lista eventos/páginas. Acciones (`role:operator`): publicar/despublicar/descartar páginas, re-sintetizar y re-clusterizar eventos. Cada acción publica un comando a Curator vía la management API de RabbitMQ (`curator.commands`).

### Configuración de Curator (`role:admin`)
`/settings` edita `curator_settings` (modelos LLM, umbrales de clustering, max tokens, presupuesto mensual, proveedores de embeddings/LLM). Botones: reset, **re-embed del corpus**, y el **kill-switch "Stop Curator"** (`processing_enabled`, ADR-0023) que pausa el pipeline sin perder mensajes.

### Gestión de API keys
`/api-keys` (`role:admin`): alta/baja de keys por proveedor (cifradas at-rest), test de validez, historial. Solo una key activa por proveedor.

### Observabilidad y costos
- `/health` y `/api/curator-pipeline`: probes de Postgres, Curator (`/status`), Messor (`/`) y RabbitMQ (colas clave).
- `/runtime`: estado de contenedores Docker (CPU/mem/red) vía socket del daemon.
- `/model-usage`: consumo de tokens y costo por modelo (filas escritas por Curator en `model_usage`).
- `/alerts`: alertas (scrape_low_success, stale_outlet, over_budget, pipeline_stalled) con acknowledge.
- `/audit-log`: bitácora de acciones de mutación.

### RBAC
Tres roles inclusivos: `viewer` (lectura) ⊂ `operator` (cosecha + moderación + outlets) ⊂ `admin` (settings, keys, usuarios, auditoría).

## Pipeline automático (Messor + Curator)

### Cosecha (Messor)
Ciclo programado 4×/día (`--schedule`) más un hilo *pulse* cada 5 min para outlets de breaking. RSS-first con fallback a crawl de homepage. Gate de frescura estricto (48 h), dedup en 3 capas, publicación por artículo a RabbitMQ.

### Curación (Curator)
Consume cada artículo y ejecuta **ENRICH → CLUSTER → SYNTHESIZE → (ILLUSTRATE)**:
- **ENRICH**: una llamada LLM clasifica theme/topic, resume, puntúa factualidad/sentimiento, extrae keywords y entidades; luego embebe (bge-m3).
- **CLUSTER**: asigna el artículo a un evento existente (vecino más cercano por coseno + solapamiento de entidades) o siembra uno nuevo. Detecta breaking news por velocidad.
- **SYNTHESIZE**: cuando un evento tiene ≥2 outlets, genera la página (headline + síntesis + evidence rail). Filtros de contenido promocional y filler.
- **ILLUSTRATE**: busca videos de YouTube relevantes para el media rail (fire-and-forget).
- **ASK**: backend del asistente de chat (RAG sobre eventos publicados).

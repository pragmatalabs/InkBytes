# Registro de Riesgos Arquitectónicos — InkBytes v0

## Top risks (ordenado por severidad)

| ID | Riesgo | Área | Probabilidad | Impacto | Severidad | Mitigación | Estado |
|---|---|---|---|---|---|---|---|
| **R-009** | Secretos previamente filtrados (env.yaml legacy) sin rotar y sin scrub de historia | Seguridad | Alta (público vía git history) | Crítico (DO Spaces, Anthropic, OpenAI, RabbitMQ comprometibles) | **Crítico** | Rotar todos los keys + `git filter-repo` para scrubbing + pre-commit gitleaks | 🔴 Abierto |
| **R-001** | LLM alucina hechos en SYNTHESIZE | Calidad / Legal | Alta | Alto (daño reputacional, reclamos de outlets) | **Alto** | Pase de validación: 2nd LLM call verifica que cada claim cite source; descartar oraciones sin source. Implementar Sprint-2. | 🟠 Parcial (prompt rule + evidence_rail mandatorio) |
| **R-005** | Single Droplet = single point of failure | Disponibilidad | Media (incidente DO posible) | Alto (Reader y pipeline caen juntos) | **Alto** | Aceptado para v0. Post-MVP: 2 Droplets + LB; o migrar a DO App Platform | 🟡 Aceptado v0 |
| **R-002** | Outlet bloquea nuestro scraper (rate-limit / CAPTCHA / IP ban) | Cosecha | Media | Medio (perder cobertura de 1+ outlet) | Alto | Per-outlet circuit breaker (5 fallos → skip 3 ciclos) + 12+ outlets ya configurados → otro 2 OK | 🟠 Parcial (sin circuit breaker aún) |
| **R-003** | Costos Anthropic se disparan (bug → loop, prompt grande, etc.) | Operacional | Media | Alto ($ inesperado) | Alto | Per-cycle cost guard (ADR Curator-0004 pendiente) + dashboard de costos diario | 🔴 Pendiente |
| **R-007** | Cluster produce eventos de 1-fuente (no-sintetizables) sistemáticamente | Producto | Media | Medio (catálogo vacío de cara al usuario) | Medio | Tuning de `similarity_threshold` y `entity_overlap_min` con fixtures reales; al final del Sprint-2 calibrar con dataset etiquetado | 🟡 Mitigación en curso |
| **R-011** | Dimensión de pgvector (1536) no coincide con embedding (1024 bge-m3) | Datos | Alta | Alto (Curator crash o filas con NULL embedding) | Alto | Corregir migration a `vector(1024)` antes de v0; reset si tablas pobladas | 🔴 Conocido, no resuelto |
| **R-006** | Postgres pgvector lento sin tuning (IVFFlat lists) | Performance | Baja | Medio (cluster query > 1s) | Medio | Comenzar con `lists=100`; recalcular cuando rows > 100k | 🟡 Aceptado |
| **R-008** | Queue workers de Laravel mueren silenciosamente | Operacional | Media | Alto (scrape "iniciado" desde UI no corre) | Alto | systemd unit + `restart=always`; alerta B11 si queue lag > 5 min | 🟠 Parcial (presente pero no monitoreado) |
| **R-004** | DO Managed Postgres con backup faltante o test de restore no probado | Datos | Baja | Crítico (pérdida de pages y articles) | Alto | DO managed daily backups; ejecutar restore test mensual a partir de v0 | 🔴 Pendiente test |
| **R-010** | `inkbytes` package legacy (pydantic v1) bloquea evolución | Mantenibilidad | Baja | Medio (técnicos: ralentiza features) | Medio | Roadmap Sprint-3: extraer modelos legacy a `packages/inkbytes-legacy`; nuevos modelos solo en `packages/contracts` (pydantic v2) | 🟡 Aceptado |
| R-012 | Outlet cambia su HTML estructura silenciosamente | Cosecha | Alta | Bajo (news outlets cambian poco mensualmente) | Bajo | newspaper3k es razonablemente tolerante; per-outlet success rate alerts en Sprint-2 | 🟡 Aceptado |
| R-013 | Reader brand voice no definido bloquea SYNTHESIZE prompt | Producto | Alta (decisión pendiente) | Bajo (modelo neutro v0 funciona) | Bajo | Lock antes de invitar primer usuario pago | 🟠 Pendiente decisión |
| R-014 | RabbitMQ free tier llega al límite mensual (1M msg) | Capacidad | Baja | Bajo (~30k/día estimado) | Bajo | Plan paid tier si > 20k/día sostenido | 🟢 Monitoreo |

## Criterios de severidad

- **Crítico**: Impacto regulatorio, brecha de datos, downtime total > 4 h
- **Alto**: Degradación severa, pérdida de datos secundarios, costo > 20% mensual
- **Medio**: Impacto en performance, funcionalidad parcial, deuda significativa
- **Bajo**: Deuda técnica, UX subóptimo, capacidad ociosa

## Deuda técnica arquitectónica identificada

| Área | Descripción | Esfuerzo | Prioridad | Sprint objetivo |
|---|---|---|---|---|
| Migrations | Sin runner formal; `_ensure_schema` mágico | M | Alta | Sprint-2 |
| pgvector dim | Mismatch 1536 vs 1024 | S | Alta | Antes de v0 (R-011) |
| Cost guard | Sin techo por ciclo | S | Alta | Sprint-2 |
| Per-outlet circuit breaker | Sin protección contra bloqueos | M | Alta | Sprint-2 |
| Tenacity wrappers | Sin retries explícitos en HTTP outbound | S | Media | Sprint-2 |
| OTel tracing | Sin trazas | M | Media | Sprint-2 |
| Schema versioning runner | `schema_migrations` table | M | Media | Sprint-3 |
| Per-claim provenance | `synthesis_md` no marca qué source dijo qué | L | Media (post-v0) | Sprint-3 |
| Reader auth/billing | Single shared password v0 | L | Alta post-v0 | Post-v0 |
| Multi-host workers | Para escalar > 200 outlets | L | Baja | Post-v0 |

## Convención de tracking

- Cada riesgo aquí debe tener un ticket linkado en el tracker (Linear / Jira / GitHub Issues).
- Revisión del registro cada sprint review.
- Cambiar estado a 🟢 **Cerrado** sólo cuando la mitigación esté implementada + verificada.
- Riesgos aceptados (🟡) son legítimos para v0 pero deben tener fecha de revisión.

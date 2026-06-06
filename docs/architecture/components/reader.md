# Componente: Reader — Next.js Public App (placeholder)

## Identificación

| Atributo | Valor |
|---|---|
| **Nombre** | Reader (`Reader/apps/web` — pendiente de scaffold) |
| **Tipo** | Web app pública |
| **Versión** | — (placeholder) |
| **Equipo dueño** | Front |
| **Estado** | No scaffoldeado al cierre de este SAD (D4 en `docs/mvp-plan.md`) |

## Propósito

Interfaz pública del lector pago. Renderiza:
- Home: lista de eventos publicados, ordenados por `freshness_at`.
- `/event/[id]`: el one-pager — headline, synthesis_md (markdown), evidence_rail, entities_top, freshness timestamp.

## Responsabilidades (target)

- Renderizar paginas estáticas/dinámicas desde Curator API.
- Aplicar single-shared-password gate (env `INKBYTES_DEMO_PASSWORD`) en v0.
- SEO básico (Open Graph, meta tags).
- Mobile-first responsive.

## NO es responsabilidad

- Auth real / billing (post-v0).
- Llamadas directas a Postgres (siempre vía Curator API).
- Cualquier LLM call (Curator hace todo upstream).

## Interfaces

### Expone (produce)

| Path | Tipo | Descripción |
|---|---|---|
| `/` | Server Component | Lista de top-N eventos por freshness |
| `/event/[id]` | Server Component | One-pager |
| `/about` | Static | Sobre el producto |
| `/_health` | API route | Healthcheck del Reader (no del backend) |

### Consume (depende de)

| Dependencia | Tipo | Uso |
|---|---|---|
| Curator API `/events`, `/events/{id}` | HTTP | Fuente única de datos |
| Tailwind utility classes | CSS | Estilos |
| Brand voice (TBD) | — | Tipografía + tono |

## Tecnología (target)

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Node 20 | LTS |
| Framework | Next.js | 14 (App Router) |
| UI | Tailwind | 3.x |
| Lenguaje | TypeScript | 5.x |

## Atributos de calidad

| Atributo | Objetivo v0 | Medición |
|---|---|---|
| Latencia render p95 | < 1.5 s (cache cálido) | Vercel Speed Insights o equivalent |
| LCP móvil | < 2.5 s | Lighthouse |
| Disponibilidad | 99.5% | Healthcheck |
| Bundle size first-load JS | < 150 KB gz | Next.js analyze |

## Pendientes inmediatos

- [ ] Scaffold (Next.js 14 + Tailwind).
- [ ] Lock brand voice → afecta también el prompt de SYNTHESIZE.
- [ ] Single-shared-password middleware.
- [ ] Páginas `/` y `/event/[id]` con datos reales de Curator.
- [ ] Mobile responsive QA en iPhone 14 / Android Pixel.

# IA Soberana — Dossier y Timeline Consolidado

> **Tesis validada:** en el estado actual del sector, la inteligencia artificial se comporta como *infraestructura crítica y activo geopolítico*, no como un producto de consumo. Quien no controla sus **chips, modelos, datos, cómputo/energía y reglas** queda expuesto a la decisión de un tercero. De ahí la conclusión: **la IA debe ser soberana** — gobernable por el país, la región o la institución que depende de ella.
>
> *Cobertura: **enero → julio 2026** en dos partes complementarias.*
> *— **Parte I (ene–jun 2026):** investigación web con **fuentes primarias verificadas** (BIS, SEC/EDGAR, Comisión Europea, Carnegie, Presidencia RD), verificación adversarial 2/3 votos.*
> *— **Parte II (22-jun → 16-jul 2026):** corpus de producción de **InkBytes** (`inkbytes-postgres`).*
> *Alcance: panorama global + sección LATAM/República Dominicana.*
> *Documento de apoyo analítico. No sustituye el juicio profesional ni la validación de las áreas de cumplimiento/legal/riesgo ante decisiones institucionales.*
> *Generado: 2026-07-16.*

---

## 0. Nota metodológica y de alcance (leer primero)

Este dossier se construyó **primero con datos de producción de InkBytes**, tal como se solicitó:

| Fuente extraída | Volumen | Ventana |
|---|---|---|
| Artículos totales en producción | 175.737 | 22-jun → 16-jul 2026 |
| Artículos con tema `technology` | 5.709 | ídem |
| Artículos relacionados con IA (título/topic) | 11.882 | ídem |
| Páginas publicadas (eventos sintetizados) tema tecnología | 631 | 23-jun → 16-jul |
| Editoriales diarias de tecnología ("El Circuito") | 14 ediciones (ES+EN) | 03-jul → 16-jul |

> ⚠️ **Sobre la cobertura temporal.** La base de producción de InkBytes sólo retiene **≈24 días** por el *clean-slate reset* de clustering (ADR-0031, jun-2026): todo lo anterior a 2026-06-22 fue purgado. Por eso el semestre completo se cubre en **dos partes**: la **Parte I (ene–jun 2026)** se reconstruyó con **investigación web verificada** (fuentes primarias, verificación adversarial), y la **Parte II (22-jun → 16-jul)** proviene íntegramente del corpus de producción de InkBytes. Ambas usan los mismos siete ejes, de modo que la línea de tiempo es continua enero → julio.

Todas las evidencias citadas abajo corresponden a **eventos publicados por InkBytes** (páginas sintetizadas a partir de ≥2 fuentes por evento; se indica el nº de fuentes y los medios subyacentes cuando la síntesis los nombra).

---

## 1. Resumen ejecutivo

En los ≈24 días observados, el corpus de InkBytes documenta que **cada capa de la pila de IA se convirtió en un punto de control geopolítico o corporativo**:

- **Chips:** EE.UU. usa el control de exportaciones como interruptor — llegó a **bloquear a extranjeros el acceso a modelos de Anthropic** (Claude Fable 5 / Mythos 5) y luego lo levantó tres semanas después (30-jun). China respondió con **chips propios** (DeepSeek) y disparó sus exportaciones de circuitos integrados **+96% a US$177 mil millones** en el primer semestre.
- **Modelos:** un supuesto **backdoor esteganográfico** en Claude Code que detectaba usuarios chinos (Alibaba lo prohibió) mostró que confiar en un modelo extranjero es confiar en su proveedor. En paralelo, las startups de EE.UU. **migran a modelos chinos abiertos** (10× más baratos; 41% de las descargas en Hugging Face).
- **Datos:** entrenamiento sin consentimiento (Meta Muse Image con fotos de Instagram; recolección ampliada de Google) y **cierres regulatorios por soberanía de datos** (Colombia cierra Worldcoin).
- **Cómputo y energía:** los centros de datos de IA encarecen la electricidad y la memoria, elevan emisiones y disputan agua — el **control físico del cómputo** es control real.
- **Reglas:** la ONU advierte que **la ventana de gobernanza se cierra** (EE.UU. controla ~¾ del cómputo mundial); la UE y varios estados usan la **regulación como herramienta de soberanía**.
- **Estrategias nacionales:** Corea del Sur (**US$576 mil M**), India (**US$19.7 mil M**), España (**€300 M** para una gigafábrica de IA), el **EU Chips Act**, y **República Dominicana** con su **primer Centro de Excelencia en IA (CEIA-RD)** con NVIDIA.

La lectura editorial propia de InkBytes lo sintetizó el **8 de julio** en *"La Frontera Invisible: Soberanía Digital en la Era de la IA"*: *la soberanía digital es "la capacidad de un país o región para gobernar su propio espacio tecnológico… la condición para que la tecnología sirva a las personas y no al revés."*

---

## 2. Los siete pilares que validan la conclusión "la IA debe ser soberana"

Cada pilar es un **argumento** seguido de la **evidencia fechada** hallada en producción de InkBytes.

### Pilar 1 — Dependencia de hardware: el chip es el nuevo petróleo, y su acceso es un interruptor político
**Argumento:** si un tercer país puede cortar tu acceso a las GPUs o a los modelos que corren sobre ellas, controla tu capacidad de innovar. El control de exportaciones dejó de ser comercio y pasó a ser palanca de seguridad nacional.

- **30-jun / 01-jul** — EE.UU. **levanta los controles de exportación** sobre los modelos más avanzados de Anthropic (Claude Fable 5 y Mythos 5) tras una prohibición de tres semanas que **había bloqueado a todos los extranjeros — incluido el propio personal no ciudadano de Anthropic** — y forzó a retirar los modelos a nivel mundial (28 fuentes; *AP, Tom's Hardware*).
- **24-jun** — Jensen Huang (Nvidia): *"la seguridad nacional va primero"*; los centros de datos con chips de contrabando son *"un callejón sin salida"*.
- **14-jul** — Nvidia **restringe el acceso a sus clientes autorizados en Asia**: el hardware avanzado ya es decisión de seguridad nacional, no de mercado.
- **14-jul** — **Exportaciones chinas de chips +96% → US$177.28 mil M** en el 1er semestre de 2026 (*Tom's Hardware, SCMP*): la respuesta de escala a la contención.

### Pilar 2 — Dependencia de modelos: confiar en un modelo extranjero es confiar en su proveedor
**Argumento:** un modelo cerrado y remoto puede vigilar, filtrar o "aprender" de tus datos, y su proveedor puede competir contigo. La independencia de modelo (abierto, auditable, on-prem/soberano) es defensa.

- **08-jul** — La **Base Nacional de Vulnerabilidades de China (NVDB)** advierte de un **"backdoor" en Claude Code** que transmitiría ubicación e identidad sin consentimiento; se halló **código esteganográfico** que detectaba usuarios chinos por zona horaria y proxy (versiones 2.1.91–2.1.196). **Alibaba prohíbe su uso** (8 fuentes; *CNA, Ars Technica*).
- **05-jul** — **Arthur Mensch (CEO de Mistral)** insta a las empresas a **abandonar los modelos cerrados**: los proveedores obtienen *"un apalancamiento inmenso"* al retener datos y competir con sus clientes.
- **26-jun** — **Anthropic acusa a Alibaba del mayor "ataque de destilación"** sobre Claude — extracción de conocimiento del modelo como frente de conflicto.
- **15-jul** — **Startups de EE.UU. migran a modelos chinos abiertos**: DeepSeek-V4 **10× más barato** (Lindy.ai movió el 100% de su tráfico); modelos chinos de peso abierto = **41% de las descargas en Hugging Face** y 6 de los 7 primeros en OpenRouter (13 fuentes; *NPR, TechCrunch*).
- **16-jul** — **Thinking Machines Lab (Mira Murati) libera Inkling**, modelo de **peso abierto** de 975 mil M de parámetros, descargable y modificable — señal de que la apertura es contra-estrategia a la dependencia.

### Pilar 3 — Soberanía de datos: quién entrena con qué, y bajo qué ley
**Argumento:** los datos de ciudadanos y empresas son el insumo del modelo. Sin control legal sobre su recolección y uso, la soberanía se pierde en el entrenamiento.

- **08-jul (Colombia)** — La **SIC confirma el cierre permanente de Worldcoin / Tools for Humanity** por violar la ley de protección de datos (Resolución 45710; recolección de datos de iris). Soberanía de datos aplicada como sanción.
- **12-jul** — **Meta desactiva Muse Image** tras la reacción por generar imágenes desde **fotos públicas de Instagram sin consentimiento** — "el espejo que no pide permiso".
- **07-jul (editorial)** — **Google amplió silenciosamente** la recolección (imágenes, audio, video) para entrenar sus modelos, con un *opt-out* que casi nadie encuentra.
- **16-jul (China)** — China **aprueba Apple Intelligence sólo con socios locales** (Qwen de Alibaba + Baidu): la **localización de datos y modelo** como condición de acceso al mercado.

### Pilar 4 — Infraestructura física y energía: controlar el cómputo es controlar la IA
**Argumento:** los modelos corren sobre acero, silicio, electricidad y agua reales. Quien no controla esa infraestructura no controla su IA — y paga externalidades.

- **13/14-jul** — **Meta expande Hyperion (Luisiana) a 5 GW, inversión > US$50 mil M** (9 fuentes). La editorial lo llama *"la trampa de la escala": el costo de entrada como foso infranqueable* — sólo los hiperescaladores compiten.
- **23-jun** — **Microsoft + Chevron**: planta de gas de **2.67 GW** en Texas dedicada a un data center de IA. La IA reconfigura el sistema energético.
- **05-jul** — **Los data centers de IA en EE.UU. enfrentan escasez de agua** al expandirse la sequía.
- **11-jul** — **Emisiones de Microsoft +25%** en un año por la expansión de centros de datos.
- **23–25-jun** — Resistencia local: **Monterey Park (California) prohíbe data centers por voto popular**; **40 alcaldes firman un pacto global** para regular su impacto ambiental; el Congreso de EE.UU. debate hacer que las Big Tech **paguen la energía** de sus data centers.

### Pilar 5 — Gobernanza y reglas: la regulación como herramienta de soberanía
**Argumento:** las reglas definen quién manda. Sin marco propio, se aceptan las reglas (y los sesgos) de otro.

- **02-jul** — El **panel científico independiente de la ONU** advierte que **la ventana de gobernanza se cierra rápidamente** y que la IA podría **ampliar la desigualdad global**: **EE.UU. controla ~¾ del cómputo** mundial (40 expertos).
- **07-jul** — **Illinois** firma una ley de IA con **auditorías de terceros obligatorias**; la ONU impulsa un pacto para proteger a menores y **António Guterres pide prohibir las armas autónomas letales** ("soberanía humana sobre la decisión de vida o muerte").
- **10-jul** — La **UE acusa a Meta de diseño adictivo** (multa potencial ~US$12 mil M) — Bruselas usa la regulación (DMA/DSA) como instrumento de soberanía.
- **07-jul (India)** — India **frena la función de nombres de usuario de WhatsApp** por riesgo de fraude: el mayor mercado (850 M usuarios) impone sus condiciones.

### Pilar 6 — Estrategias nacionales soberanas: la carrera ya es de Estados, no sólo de empresas
**Argumento:** los países que entienden la IA como infraestructura crítica están invirtiendo a escala estatal para no depender. Es el reconocimiento explícito de que la soberanía de IA se construye, no se compra.

- **29-jun** — **Corea del Sur: plan nacional de > US$576 mil M** ("triple eje": semiconductores, data centers de IA, IA física); **800 billones de won (US$518 mil M)** de Samsung + SK Hynix para cuatro nuevas fábricas.
- **15-jul** — **India: paquete de US$19.7 mil M** ("Semicon 2.0": US$13.3 mil M chips + US$6.5 mil M móviles) para reducir dependencia de importaciones.
- **23-jun** — **España: €300 M a EuroHPC** para pujar por una **gigafábrica de IA** europea + €107 M a Multiverse Computing.
- **10-jul** — **QuantumDiamonds: €91 M**, primera ayuda de fabricación bajo el **EU Chips Act** — Europa cerrando su brecha de chips.
- **29-jun** — **Austria pide a la UE "hospedar" a Anthropic** tras los cortes de EE.UU. — soberanía como reacción defensiva.

### Pilar 7 — Concentración de poder y respuesta pública: la soberanía también es interna
**Argumento:** aun dentro de un país, si el poder de IA se concentra en pocas manos privadas, el Estado y la ciudadanía pierden soberanía sobre una tecnología sistémica. La respuesta política ya emergió.

- **02-jul** — **OpenAI propone dar al gobierno de EE.UU. una participación del 5% (~US$42.6 mil M)** sobre una valuación de US$852 mil M, modelo "fondo permanente de Alaska", extensible a Anthropic/Google/Meta.
- **13-jul (editorial)** — La propuesta del senador **Bernie Sanders de un fondo soberano de IA** (transferir 50% de las acciones al público) tiene **69% de apoyo** en EE.UU.
- **15/16-jul** — **Meta demandada por usar IA (Metamate) para decidir despidos** (26 empleados; ~8.000 puestos), señalando desproporcionadamente a personas en licencia médica/parental — el poder algorítmico sin supervisión como riesgo de soberanía individual.

---

## 3. Parte I — Timeline verificado enero–junio 2026 (investigación web, fuentes primarias)

> Reconstrucción del semestre previo a la ventana de InkBytes. Cada afirmación pasó verificación adversarial (se requerían 2/3 votos para descartar); **22 afirmaciones confirmadas 3-0** y **3 refutadas y excluidas** (ver §3.3). Prioridad a fuentes primarias: BIS, SEC/EDGAR, Comisión Europea, Carnegie, Presidencia RD.

### 3.1 Antecedentes 2025 (contexto imprescindible)

| Fecha | Hecho | Fuente |
|---|---|---|
| jul-2024 | **Liang Wenfeng (CEO de DeepSeek):** *"el dinero nunca ha sido el problema; el problema es el veto a los chips avanzados"* — el hardware como restricción vinculante | CSIS/TIME/TechCrunch |
| 11-oct-2023 | 🌎 **RD lanza la ENIA** (Estrategia Nacional de IA); su tercer pilar "Hub de datos" promueve la **soberanía tecnológica y de datos** | presidencia.gob.do |
| abr-2025 | **EE.UU. exige licencia para exportar el Nvidia H20** a China y países D:5 → Nvidia registra un **cargo de US$4.500 M** por inventario excedente | SEC 10-K FY2026 (Nvidia) |
| ago-2025 | EE.UU. **concede licencias H20** a ciertos clientes chinos (~US$60 M) con la expectativa oficial de que el gobierno reciba **≥15% de los ingresos** (sin norma que lo codifique) | SEC 10-K FY2026 |
| 🌎 14-oct-2025 | **MOU Gobierno RD–NVIDIA** (Palacio Nacional): nace el **Centro de Excelencia en IA (CEIA)** y una **"Fábrica Nacional de IA"** para implementar la ENIA; prioriza alojamiento local de datos y modelos | presidencia.gob.do (2 comunicados) |
| 8-dic-2025 | **Trump anuncia** que EE.UU. permitirá el envío del **Nvidia H200** a clientes aprobados en China | CNN/CNBC/NBC/Bloomberg |

### 3.2 Timeline enero–junio 2026 (fechas verificadas)

| Fecha | Evento | Eje | Fuente primaria |
|---|---|---|---|
| **13-ene-2026** | El **BIS (Dept. Comercio EE.UU.) revisa su política de licencias**: las exportaciones del **Nvidia H200 / AMD MI325X** a China pasan a **revisión caso-por-caso** si cumplen requisitos de seguridad (regla final publicada 15-ene; Federal Register 2026-00789) | 1 | bis.gov |
| ene-2026 | El **Consejo de la UE enmienda la regulación de EuroHPC JU** para ampliar su mandato a operar **gigafábricas de IA** (~100.000 procesadores c/u) | 4,6 | Consejo UE (vía CTOL) |
| **feb-2026** | EE.UU. **concede licencia para pequeñas cantidades de H200** a clientes chinos específicos, con **inspección en EE.UU. antes del envío** y un **arancel del 25%** a la importación | 1 | SEC 10-K FY2026 |
| abr-2026 | **DeepSeek libera V4** (primer modelo de nueva arquitectura desde R1); se estima que corre sobre **≥60.000 GPU Nvidia** (varios restringidos) | 2 | House Select Committee / CFR |
| **~31-may / 1-jun-2026** | El **BIS aclara** que las licencias de chips de IA **aplican a toda empresa con matriz china, aunque opere fuera de China** — cierre de un resquicio | 1 | Al Jazeera (sobre guía BIS) |
| **3-jun-2026** | La **Comisión Europea presenta el Paquete de Soberanía Tecnológica**: **"Chips Act 2.0"** + propuesta **"Cloud and AI Development Act" (CADA, COM(2026)502)** — marco único de la UE para **evaluar la soberanía de nube e IA** (niveles de aseguramiento + adopción por el sector público) y desplegar *AI factories/gigafactories* | 3,5,6 | commission.europa.eu |
| 9-jun-2026 | Los **Estados del Golfo** (Arabia Saudita/HUMAIN, EAU/G42, MGX) consolidan su apuesta soberana vía fondos soberanos | 7 | Fortune |
| jun-2026 | **Carnegie**: los **EAU** han gastado **~US$148.000 M** en IA desde 2024 (fondos soberanos); la **IndiaAI Mission** movilizó **>US$5.500 M**, pero sus **38.000 GPU** provienen **enteramente de proveedores estadounidenses** — ambición soberana **limitada por dependencia de hardware** | 6,7 | carnegieendowment.org |

> **Nota sobre el EU AI Act:** las obligaciones para modelos de propósito general (GPAI, Capítulo V) escalan su aplicación durante **2026** (hito de agosto 2026), reforzando el uso de la regulación como palanca de soberanía. *(Fuente secundaria: artificialintelligenceact.eu; conviene validar la fecha exacta con la Comisión antes de citarla en un documento formal.)*

### 3.3 Ejes validados con evidencia web (ene–jun 2026)

- **Eje 1 (chips como arma geopolítica) — el mejor documentado.** La secuencia H20→H200 (abr-2025 → feb-2026) muestra el hardware como **interruptor de Estado**: licencias, "impuesto" del 15%, arancel del 25% e inspección previa. *(BIS; SEC 10-K FY2026 de Nvidia.)*
- **Eje 2 (dependencia de modelos).** El caso **DeepSeek** encarna el riesgo: entrenado sobre chips Nvidia restringidos (~60.000 GPU), acusación de **distillation** de OpenAI ante el Congreso, y **transmisión de datos** vía infraestructura ligada a China Mobile con almacenamiento en la RPC. *(House Select Committee on the CCP; IFP.)*
- **Ejes 5 y 6 (regulación + inversión como soberanía).** El **Paquete de Soberanía Tecnológica de la UE (3-jun-2026)** convierte gobernanza e inversión en instrumentos explícitos de soberanía (Chips Act 2.0 + CADA). *(Comisión Europea.)*
- **Ejes 6 y 7 (inversión estatal + dependencia).** **EAU ~US$148.000 M** e **India (IndiaAI Mission)** ilustran la paradoja: gran inversión soberana que **sigue dependiendo de GPU estadounidenses**. *(Carnegie.)*
- **LATAM/RD.** La **ENIA + MOU con NVIDIA (14-oct-2025)** estructura una estrategia soberana dominicana que **prioriza el alojamiento local de datos y modelos**; la construcción del CEIA arrancó el **22-jun-2026** (ya dentro de la Parte II). *(Presidencia RD.)*

**Refutado en verificación y excluido** (voto 1-2, no se sostiene): (a) que legisladores de EE.UU. probaran un vínculo directo del **código** de DeepSeek con el PCCh; (b) el encuadre de la ley Gottheimer–LaHood como "protección de soberanía de datos"; (c) que **NVIDIA suministre el 52%** de los proyectos globales de infraestructura de IA.

**Cobertura desigual (honestidad metodológica):** los **ejes 3 (soberanía de datos/entrenamiento sin consentimiento)** y **4 (energía/agua/emisiones de data centers)** quedaron poco cubiertos por evidencia *fechada y verificada* en la Parte I — aparecen mejor documentados en la Parte II (InkBytes). LATAM fuera de RD (MX, CO, BR, AR, CL, PE) no arrojó afirmaciones verificadas en este pase.

---

## 4. Parte II — Timeline InkBytes (22-jun → 16-jul 2026)

> Fechas = `freshness_at` de la página publicada en InkBytes (fecha de última cobertura material del evento). `(N)` = nº de fuentes que sustentan el evento. 🌎 = ancla LATAM/RD.

### Junio 2026

| Fecha | Evento | Eje de soberanía |
|---|---|---|
| **22-jun** 🌎 | **República Dominicana** inicia la construcción del **primer Centro de Excelencia en IA (CEIA-RD)** con NVIDIA, en el Parque Cibernético de Santo Domingo (Min. Presidencia, J.I. Paliza) (3) | Estrategia nacional |
| **23-jun** | **España** aprueba **€300 M** a EuroHPC para pujar por una **gigafábrica de IA** + €107 M a Multiverse Computing (2) | Estrategia nacional |
| 23-jun | **China restringe exportaciones** a 10 firmas de defensa de EE.UU. y veta compras a 46 empresas (represalia) (3) | Chips / geopolítica |
| 23-jun | **ONU (Guterres)** propone la *AI Environmental Transparency Initiative*: exige revelar el costo ambiental de los data centers (7) | Gobernanza / energía |
| 23-jun | **Microsoft + Chevron**: planta de gas de 2.67 GW en Texas para un data center de IA (2) | Infraestructura / energía |
| 24-jun | **Nvidia (Huang)**: "la seguridad nacional va primero"; chips de contrabando = "callejón sin salida" (2) | Chips |
| 24-jun | **China: supercomputadora LineShine** #1 mundial, primer exascala sólo-CPU, tras 9 años de dominio de EE.UU. (12) | Cómputo soberano |
| 24-jun | **Monterey Park (CA)** primera ciudad de EE.UU. en **prohibir data centers por voto** (3) | Energía / resistencia |
| 24-jun | Congreso de EE.UU. vota hacer que **Big Tech pague la energía** de sus data centers de IA (2) | Energía |
| 24-jun | **Five Eyes** advierte que las ciberamenazas con IA están "a meses" (Mythos de Anthropic halló fallos en sistemas de EE.UU.) (10) | Seguridad nacional |
| 25-jun | **OpenAI + Broadcom** revelan **Jalapeño**, su primer chip de IA propio (12) | Chips (integración vertical) |
| 25-jun | **40 alcaldes** firman pacto global para regular el impacto ambiental de los data centers (6) | Gobernanza / energía |
| 25-jun | **IBM** anuncia chip sub-1nm con 100 mil M de transistores (9) | Chips |
| 26-jun | **Zhipu (China)**: acciones **+2.000%** desde su IPO, impulsada por su modelo open-source **mientras EE.UU. restringe a Anthropic** (3) | Modelos abiertos |
| 26-jun | **Anthropic acusa a Alibaba** del mayor **ataque de destilación** sobre Claude (8) | Modelos / IP |
| 26-jun | **OpenAI retrasa GPT-5.6** a pedido del gobierno de EE.UU. (13) | Gobernanza / seguridad |
| 26-jun | **Apple sube precios** de Mac/iPad por la crisis de chips de memoria por IA (25) | Chips / costo |
| 29-jun | **Corea del Sur: plan de > US$576 mil M** para chips, data centers e IA física (12) | Estrategia nacional |
| 29-jun | **Austria pide a la UE hospedar a Anthropic** tras los cortes de acceso de EE.UU. (2) | Soberanía defensiva |
| 29-jun | **Baidu (Kunlunxin)** apunta a IPO de US$50 mil M en Hong Kong para su brazo de chips de IA (2) | Chips soberanos |

### Julio 2026

| Fecha | Evento | Eje de soberanía |
|---|---|---|
| **01-jul** | **EE.UU. levanta los controles de exportación** sobre Claude Fable 5 / Mythos 5 (fin de una prohibición de 3 semanas que bloqueó a todos los extranjeros) (28) | **Chips / control de exportaciones** |
| **01-jul** 🌎 | **Globant (Argentina) + Anthropic**: alianza estratégica; mayor firma de origen latinoamericano como *Preferred Services Partner* (3) | Adopción regional |
| 02-jul | **Panel de la ONU**: la ventana de gobernanza de IA **se cierra**; EE.UU. controla **~¾ del cómputo** mundial; riesgo de ampliar la desigualdad (3–5) | Gobernanza |
| 02-jul | **OpenAI propone al gobierno de EE.UU. un 5% (~US$42.6 mil M)**, modelo "fondo de Alaska" (15–20) | Concentración de poder |
| 04-jul | **The Guardian**: OpenAI nunca visitó el sitio de su data center **Stargate UK** antes de anunciarlo (2) | Infraestructura (promesa vs. realidad) |
| 05-jul | **Mistral (Mensch)** advierte a las empresas contra los **modelos cerrados** (2) | Modelos abiertos |
| 05-jul | **CG Semi** inicia producción de chips en la planta OSAT de Gujarat (India) (2) | Chips soberanos |
| 05-jul | **Data centers de IA en EE.UU.** enfrentan **escasez de agua** por la sequía (2) | Energía / recursos |
| 06-jul | **Biren** levanta US$892 M para producción de GPU en plena carrera de chips de China (2) | Chips soberanos |
| 06-jul 🌎 | **Telecirugía récord** Ecuador–China–Chile a 35.000 km (récord Guinness) (2) | Capacidad tecnológica regional |
| 07-jul | **Illinois** firma ley de IA con **auditorías de terceros obligatorias** (3) | Gobernanza |
| 07-jul | **ONU** impulsa un pacto global para proteger a menores de riesgos de IA; **Guterres pide prohibir armas autónomas letales** (4–6) | Gobernanza / soberanía humana |
| 07-jul | **DeepSeek desarrolla su propio chip de inferencia** para reducir dependencia de Nvidia y Huawei (2) | Chips soberanos |
| **08-jul** | **China (NVDB) advierte de un "backdoor" en Claude Code**; **Alibaba lo prohíbe** (esteganografía que detectaba usuarios chinos) (8) | **Modelos / espionaje** |
| **08-jul** | **Encuesta "Soberanía Digital en Europa 2026"**: **86% de los españoles** exige plataformas tecnológicas europeas; 62% ve la dependencia extranjera como amenaza de seguridad (4) | Mandato ciudadano |
| 08-jul 🌎 | **Colombia (SIC)** confirma el **cierre permanente de Worldcoin** por violar la protección de datos (3) | Soberanía de datos |
| 09-jul 🌎 | **Paraguay (Conatel)** aprueba a **Starlink** operar por encima de los límites de la UIT (capacidad ×8, hasta 1 Gbps) (2) | Infraestructura / regulación |
| 09-jul | **Ferrovial** invierte **€1.000 M** en un campus de data centers en Alcobendas (España) (4) | Infraestructura europea |
| 09-jul | **Meta** invierte **US$9.200 M** en su primer gran data center en Canadá (4) | Infraestructura |
| 10-jul | **QuantumDiamonds: €91 M**, primera ayuda de fabricación del **EU Chips Act** (2) | Estrategia europea |
| 10-jul | **OpenAI lanza GPT-5.6** tras la revisión del gobierno de EE.UU. (14) | Gobernanza |
| 10-jul | La **UE acusa a Meta de diseño adictivo** (multa potencial ~US$12 mil M) (11) | Regulación como soberanía |
| 11-jul | **Emisiones de Microsoft +25%** por la expansión de data centers de IA (8) | Energía / externalidades |
| 12-jul | **Meta desactiva Muse Image** (usaba fotos públicas de Instagram sin consentimiento) (7) | Soberanía de datos |
| 12-jul 🌎 | **Trinidad y Tobago** firma acuerdos de data centers con empresas de EE.UU. (300 MW + 150 MW) — primeros en el Caribe (2) | Infraestructura regional |
| **13/14-jul** | **Meta expande Hyperion (Luisiana) a 5 GW, > US$50 mil M** — el foso de capital de la IA (9) | Infraestructura / concentración |
| 14-jul | **Nvidia restringe** el acceso a clientes autorizados en Asia (2) | Chips / seguridad nacional |
| 14-jul | **China: exportaciones de chips +96% → US$177 mil M** (1er semestre) (2) | Chips (respuesta de escala) |
| 14-jul | **Intel invierte US$5.700 M** en su fábrica de Irlanda (Xeon 6) (3) | Chips (reshoring) |
| **15-jul** | **Startups de EE.UU. migran a modelos chinos abiertos** (DeepSeek 10× más barato; 41% de descargas en Hugging Face) (13) | **Modelos abiertos** |
| **15-jul** | **India: paquete de US$19.7 mil M** ("Semicon 2.0") para chips y móviles (3) | Estrategia nacional |
| 15-jul | **Publishers demandan a Google** por entrenar Gemini con obras con derechos de autor (5) | Datos / IP |
| 16-jul | **China aprueba Apple Intelligence** sólo con socios locales (Qwen/Alibaba + Baidu) (2) | Localización de datos y modelo |
| 16-jul | **Thinking Machines Lab (Mira Murati) libera Inkling**, modelo de **peso abierto** de 975 mil M de parámetros (18) | Modelos abiertos |
| 16-jul | **Meta demandada por usar IA (Metamate) para decidir despidos** (26 empleados) (8) | Poder algorítmico / soberanía individual |
| 16-jul | **China limita las "compañías de IA"** y prohíbe compañeros emocionales para menores (2–3) | Gobernanza / control interno |

---

## 5. Foco LATAM y República Dominicana

La región aparece como **tomadora de tecnología que empieza a legislar y construir soberanía**:

- **🇩🇴 República Dominicana:** el hito regional más claro y con la historia más completa. Encadena **(11-oct-2023)** el lanzamiento de la **ENIA** con soberanía tecnológica y de datos como pilar → **(14-oct-2025)** el **MOU Gobierno–NVIDIA** que crea el **CEIA** y una **"Fábrica Nacional de IA"**, priorizando el **alojamiento local de datos y modelos** → **(22-jun-2026)** el **inicio de construcción del CEIA-RD** en el Parque Cibernético de Santo Domingo, liderado por el Ministerio de la Presidencia (verificado en InkBytes). Es una **estrategia soberana explícita**, no un proyecto aislado. *Relevante para Banreservas como referencia del ecosistema local de IA soberana.*
- **🇦🇷 Argentina / regional (01-jul):** **Globant + Anthropic** — mayor firma de origen latinoamericano en la red de socios de Anthropic; adopción empresarial de Claude a escala.
- **🇨🇴 Colombia (08-jul):** **cierre de Worldcoin** por la SIC — ejemplo regional de **soberanía de datos** aplicada (protección de datos biométricos).
- **🇵🇾 Paraguay (09-jul):** cambios regulatorios para **Starlink** (capacidad ×8) — soberanía de conectividad e infraestructura satelital.
- **🇹🇹 Trinidad y Tobago (12-jul):** primeros acuerdos de **data centers** del Caribe con empresas de EE.UU. (300 MW + 150 MW de IA).
- **🇪🇨 Ecuador (06-jul):** telecirugía récord Ecuador–China–Chile — capacidad técnica aplicada.

**Lectura para RD/Banca:** la región compite por **infraestructura (data centers, satélite), talento (centros de excelencia) y marco legal (protección de datos)**. La soberanía de IA para una institución financiera dominicana se juega en: dónde viven los datos, qué modelos se usan (abiertos/soberanos vs. API cerrada extranjera), y qué reglas locales aplican. *Cualquier decisión concreta debe validarse con las áreas de Cumplimiento, Legal, Riesgo y Seguridad Cibernética.*

---

## 6. Síntesis: por qué la evidencia sostiene la conclusión

| Si la IA fuera un simple producto… | …pero la evidencia de InkBytes muestra que es infraestructura crítica soberana |
|---|---|
| Comprarías el mejor y listo | Su acceso se **corta y restablece por decreto** (export controls, 30-jun) |
| El modelo sería una caja neutral | Puede llevar **backdoors** y "aprender" de tus datos (Claude Code, 08-jul; Mistral, 05-jul) |
| Tus datos serían tuyos | Se **entrena sin consentimiento**; los reguladores **cierran** a quien viola la ley (Meta Muse; Colombia/Worldcoin) |
| Correría "en la nube", sin más | Depende de **GW de energía, agua y silicio** físicos y localizados (Hyperion 5 GW; sequía; +96% chips China) |
| Las reglas serían universales | **Cada bloque impone las suyas** (UE/DMA, India/WhatsApp, China/localización, ONU/gobernanza) |
| El mercado decidiría | **Los Estados invierten cientos de miles de millones** para no depender (Corea, India, España, UE, RD) |

**Conclusión:** en las seis capas —chips, modelos, datos, cómputo/energía, reglas e inversión— el control lo ejerce hoy quien tiene soberanía sobre esa capa. Por tanto, para un país, una región o una institución, **depender sin controlar equivale a delegar decisiones estratégicas en un tercero**. La IA soberana no es nacionalismo tecnológico: es **gestión de riesgo y continuidad** sobre una infraestructura que ya es crítica.

---

## 7. Vacíos y próximos pasos

1. **Cobertura temporal — resuelta.** El semestre completo ene–jul 2026 queda cubierto (Parte I web + Parte II InkBytes). Persisten estas **preguntas abiertas** que la investigación no cerró con evidencia fechada:
   - **Eje 4 (energía/agua/emisiones/gigafábricas):** faltan datos primarios ene–jun 2026 sobre consumo energético/hídrico y proyectos concretos, más allá de las *AI factories* de la UE.
   - **Eje 3 (soberanía de datos/localización/entrenamiento sin consentimiento):** conviene rastrear las disposiciones del EU AI Act que entran en vigor en 2026 y casos de localización.
   - **LATAM fuera de RD:** México, Colombia, Brasil, Argentina, Chile y Perú no arrojaron afirmaciones verificadas en el pase web; requieren búsqueda dedicada.
   - **RD dentro de la ventana:** hitos de implementación de ENIA/CEIA entre el MOU (oct-2025) y el inicio de obra (22-jun-2026), y estado del marco legal de protección de datos que respalda la soberanía declarada.
2. **Trazabilidad.** Los eventos de la Parte II tienen su página en InkBytes (§8); los de la Parte I citan fuentes primarias web (§9).
3. **Ángulo banca/RD.** Si el objetivo es una postura institucional (nube soberana, modelos on-prem/abiertos, localización de datos para banca regulada), puedo derivar un memo específico — a validar con Cumplimiento, Legal, Riesgo y Seguridad Cibernética antes de cualquier decisión.

---

---

## 8. Anexo — Citación navegable (páginas de InkBytes)

Enlaces clicables a los eventos ancla del timeline (`https://inkbytes.org/event/{id}`):

| Fecha | Evento | Enlace |
|---|---|---|
| 23-jun | 🌎 RD — CEIA-RD con NVIDIA | https://inkbytes.org/event/01KW08BQ3D3XP5GSD7DY3FYYBH |
| 23-jun | España — €300M gigafábrica de IA (EuroHPC) | https://inkbytes.org/event/01KW08BX5DHYW7X6ZTKV40N8GY |
| 29-jun | Corea del Sur — plan de US$576 mil M | https://inkbytes.org/event/01KW8HB74RVY7Y463F7C96J37V |
| 01-jul | EE.UU. levanta controles de exportación (Claude Fable 5 / Mythos 5) | https://inkbytes.org/event/01KW08C80EC23RN2ZNVTB556FW |
| 01-jul | 🌎 Globant (Argentina) + Anthropic | https://inkbytes.org/event/01KWCD6J90J9ST96R92HFXGS1D |
| 02-jul | ONU — la ventana de gobernanza se cierra | https://inkbytes.org/event/01KWEMKEEP0MM435ATF87MP7HW |
| 02-jul | OpenAI propone 5% al gobierno de EE.UU. | https://inkbytes.org/event/01KWGJVNWJXF99TR0ZBQ2Q113S |
| 07-jul | DeepSeek — chip propio de inferencia | https://inkbytes.org/event/01KWY7Y324DYWZRTBWJCSZC3QT |
| 08-jul | 🌎 Colombia (SIC) — cierre de Worldcoin | https://inkbytes.org/event/01KWZ4RFQHG0W5GXC03QVF0E95 |
| 08-jul | 86% de españoles exige plataformas europeas | https://inkbytes.org/event/01KX0E8TBK178H6GD7DCR1HY4B |
| 08-jul | China — "backdoor" en Claude Code, Alibaba lo prohíbe | https://inkbytes.org/event/01KWKR0NXX5HT9J36SWBVNCABG |
| 12-jul | 🌎 Trinidad y Tobago — acuerdos de data centers | https://inkbytes.org/event/01KX9M0MVJF5VVTBCV9DWVGHS7 |
| 13-jul | Meta — Hyperion 5 GW / > US$50 mil M | https://inkbytes.org/event/01KX1SGAZSFG8Q5FRHTA1DNDA1 |
| 15-jul | Startups de EE.UU. migran a modelos chinos abiertos | https://inkbytes.org/event/01KWY7QVBYS77VMBF65Y4Z36NF |
| 15-jul | India — plan de US$19.7 mil M (Semicon 2.0) | https://inkbytes.org/event/01KXJTY9J3FXN3MDNG998458CA |
| 16-jul | Thinking Machines — Inkling (peso abierto) | https://inkbytes.org/event/01KWWEVJYEC9BSE850GQ6XE9F8 |

---

## 9. Anexo — Fuentes web de la Parte I (ene–jun 2026)

**Primarias (gobierno / regulador / filings):**
- BIS (Dept. Comercio EE.UU.) — revisión de política de licencias de chips a China: https://www.bis.gov/press-release/department-commerce-revises-license-review-policy-semiconductors-exported-china
- SEC / EDGAR — Nvidia Form 10-K FY2026 (H20/H200, cargo $4.5B, arancel 25%): https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm
- Comisión Europea — *Strengthening Europe's tech sovereignty* (3-jun-2026): https://commission.europa.eu/news-and-media/news/strengthening-europes-tech-sovereignty-2026-06-03_en
- Comisión Europea — propuesta *Cloud and AI Development Act (CADA)*: https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada
- U.S. House Select Committee on the CCP — *DeepSeek Unmasked*: https://chinaselectcommittee.house.gov/sites/evo-subsites/selectcommitteeontheccp.house.gov/files/evo-media-document/DeepSeek%20Final.pdf
- Presidencia RD — planes soberanos de IA con NVIDIA: https://www.presidencia.gob.do/noticias/gobierno-de-la-republica-dominicana-acelerara-sus-planes-soberanos-de-inteligencia
- Presidencia RD — nace el CEIA: https://presidencia.gob.do/noticias/presidente-abinader-con-este-acuerdo-nace-el-centro-de-excelencia-en-inteligencia
- Carnegie Endowment — *Early Lessons in the Pursuit of Sovereign AI* (jun-2026): https://carnegieendowment.org/research/2026/06/early-lessons-in-the-pursuit-of-sovereign-ai
- IFP — *The H20 Problem*: https://ifp.org/the-h20-problem/

**Secundarias (corroboración):** Al Jazeera (guía BIS sobre matrices chinas), CFR (DeepSeek V4), Fortune (fondos soberanos del Golfo), CTOL Digital (gigafábricas UE/EuroHPC), artificialintelligenceact.eu (Capítulo V GPAI).

> **Advertencias de la verificación:** la cifra de ~US$148.000 M de los EAU es **autorreportada** por su gobierno (Carnegie la matiza con *"reportedly"*); los comunicados de Presidencia RD son gubernamentales y sus cifras de escala deben tratarse con cautela; la acusación de **distillation** contra DeepSeek es testimonio de OpenAI ante el Congreso (DeepSeek lo niega; OpenAI no publicó la evidencia). Tres afirmaciones fueron **refutadas y excluidas** (ver §3.3).

---

*Parte II elaborada a partir del corpus de producción de InkBytes (`inkbytes.org`); fuentes subyacentes por evento: AP, Reuters, BBC, CNBC, SCMP, TechCrunch, NPR, The Next Web, Tom's Hardware, Infobae, La Vanguardia, El Mundo, La República, CNA, Ars Technica, entre otras (≥2 fuentes por evento). Parte I elaborada mediante investigación web con verificación adversarial (deep-research); ver §9.*

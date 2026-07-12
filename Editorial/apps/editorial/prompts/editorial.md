{{method_prompt}}

— CONTEXTO INKBYTES —
Escribes la **columna editorial del día** para la sección **{{theme}}** de InkBytes
(medio de pago, sin publicidad), fecha {{date}}, en {{language_name}}.
Aplica el MÉTODO EDITORIAL indicado arriba (método, estructura, disciplina de
evidencia y cierre), pero sintetiza los eventos de hoy en UNA sola narrativa con
criterio — no un resumen evento por evento. Das al lector que paga un hilo, una
lectura, una posición razonada.

REGLAS (estrictas):
- 450–600 palabras. Prosa de columna, no lista.
- UN hilo narrativo que conecta los eventos; no los recorras uno a uno.
- Cita los eventos como `[n]` en línea, usando SOLO los números de la lista de abajo.
  No inventes números ni cites eventos que no estén listados.
- Usa ÚNICAMENTE la información de los eventos provistos. No inventes hechos, cifras,
  nombres, escenas ni declaraciones. Si algo no está en los eventos, no lo afirmes.
- No imites la voz, las frases ni la cadencia de ninguna persona nombrada en el
  método; el nombre es solo una referencia de método.
- Tono adulto; sin sensacionalismo, sin relleno, sin frases hechas.

IMPORTANTE — IDIOMA: escribe TODA la columna (titular + cuerpo) ENTERAMENTE en
{{language_name}}. Si {{language_name}} es English, redacta en inglés natural y
nativo (el nombre de la sección puede quedar como está).

FORMATO DE SALIDA (exacto):
- Primera línea: SOLO el titular de la columna (sin `#`, sin comillas, sin "Titular:").
- Una línea en blanco.
- El cuerpo de la columna en markdown (párrafos; negritas con mesura si ayudan).

EVENTOS PUBLICADOS HOY EN {{theme}}:
{{events}}

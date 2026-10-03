# Instrucciones de corrección — repositorio `01_four_findings_var_audit`

**Destinatario:** agente de codificación con acceso de escritura al repositorio.
**Repositorio:** `https://github.com/amacias-afma/01_four_findings_var_audit`
**Fecha de auditoría:** 28 de septiembre de 2026 · commit auditado: rama por defecto
**Plazo:** todo debe estar cerrado antes del envío del manuscrito a TMLR (semana del 26 de octubre de 2026).

---

## 0. Contexto que el agente debe respetar

Este repositorio acompaña un artículo cuya tesis central es que **toda cifra publicada debe poder comprobarse**. Cualquier inconsistencia entre lo que el texto afirma y lo que el repositorio contiene no es un defecto cosmético: contradice el argumento del artículo. Actuar en consecuencia.

### Reglas duras

1. **`paper/draft-v1.md` es la única fuente de verdad de la prosa.**
   Los archivos `paper/tex/sections/*.tex` son **generados**. Nunca editarlos a mano: se sobrescriben. Después de tocar el markdown, regenerar:
   ```bash
   python scripts/import_tex.py
   python scripts/import_tex.py --check   # debe salir con código 0
   ```
2. **No modificar resultados, cifras, CSV de `outputs/`, ni el ledger.** Ninguna tarea de este documento lo requiere. Si una tarea pareciera requerirlo, detenerse y reportar.
3. **No tocar `paper/_ssrn_v1_prior_anchored/`.** Es una copia congelada a propósito de la versión anterior.
4. **Un commit por tarea**, con el identificador de la tarea en el mensaje (`T1: ...`). Facilita revertir una sin arrastrar las demás.
5. **No hacer `git push --force` ni reescribir historia.**

### Verificación final (las cinco pasan antes de dar por cerrado)

```bash
python -m pytest -q
python scripts/refresh_paper_figures.py --check
python scripts/import_tex.py --check
python scripts/check_bib.py
python -m value_at_risk.evaluation.ledger --summary
```

---

## 1. BLOQUEOS — requieren decisión de Álvaro antes de ejecutar

No inventar estos valores. Si no están resueltos, dejar la tarea pendiente y reportarlo.

| ID | Qué falta | Quién lo resuelve |
|---|---|---|
| **B1** | **El ORCID iD.** Aún no existe; se crea en la semana 1 del plan. Formato `0000-000X-XXXX-XXXX` | Álvaro |
| **B2** | **Cuál es el DOI de concepto de Zenodo** (el de "todas las versiones", no el de una versión). Ver T4 | Álvaro |
| **B3** | **Si los snapshots de precios pueden redistribuirse** bajo la licencia de la fuente de datos. Ver T7 | Álvaro |

---

## 2. Tareas

### T1 — Unificar la forma del nombre del autor

**Problema:** hay tres formas distintas circulando entre el repositorio, Zenodo y SSRN. Eso fragmenta la indexación y dispersa las citas.

**Forma canónica, sin excepción:** `Álvaro F. Macías Araya` (con tildes).

**Ediciones:**

| Archivo | Línea | Estado actual | Estado objetivo |
|---|---|---|---|
| `CITATION.cff` | 12 | `  - family-names: "Macias Araya"` | `  - family-names: "Macías Araya"` |
| `CITATION.cff` | 13 | `    given-names: "Alvaro Felipe"` | `    given-names: "Álvaro F."` |
| `.zenodo.json` | 9 | `      "name": "Macias Araya, Alvaro Felipe",` | `      "name": "Macías Araya, Álvaro F.",` |
| `paper/tex/main.tex` | 19 | `    Alvaro Macias\\` | `    Álvaro F. Macías Araya\\` |
| `main.tex` | 120 | `    Alvaro Felipe Macias Araya\thanks{...}` | `    Álvaro F. Macías Araya\thanks{...}` — conservar el `\thanks{}` íntegro |

**Cuidado con LaTeX:** verificar que el preámbulo soporte UTF-8 (`\usepackage[utf8]{inputenc}` o compilación con XeLaTeX/LuaLaTeX). Si no, usar `\'A` y `\'i` en vez de las tildes literales, **solo en los archivos `.tex`**. En `.cff`, `.json` y `.md` van siempre las tildes literales.

**Aceptación:** `grep -rn "Alvaro\|Macias Araya"` no devuelve coincidencias sin tilde fuera de `paper/_ssrn_v1_prior_anchored/` y de `.git/`.

---

### T2 — Rellenar el ORCID · BLOQUEADA POR B1

**Problema:** `CITATION.cff` línea 14 contiene un marcador de posición que dice explícitamente que hay que rellenarlo antes de publicar, y se publicó dos veces sin hacerlo:

```yaml
    # orcid: "https://orcid.org/0000-0000-0000-0000"   # <- add yours before release
```

**Acción:** descomentar y poner el ORCID real de B1:

```yaml
    orcid: "https://orcid.org/<ORCID_DE_B1>"
```

**Además:** añadir el mismo ORCID al bloque `creators` de `.zenodo.json`:

```json
  "creators": [
    {
      "name": "Macías Araya, Álvaro F.",
      "affiliation": "AFMA Quant AI Lab, AFMA Ingeniería SpA",
      "orcid": "<ORCID_DE_B1_SIN_PREFIJO_URL>"
    }
  ],
```

> Zenodo espera el ORCID **sin** el prefijo `https://orcid.org/`; CITATION.cff lo espera **con** el prefijo. No son intercambiables.

**Aceptación:** ningún `0000-0000-0000-0000` en el repositorio.

---

### T3 — Sincronizar versión y fecha en `CITATION.cff`

**Problema:** el archivo de citación va una versión atrás del depósito real, así que quien lo use cita la versión equivocada.

| Campo | Actual | Objetivo |
|---|---|---|
| `version` | `"1.0.0"` | `"2.0.0"` |
| `date-released` | `"2026-08-19"` | `"2026-09-18"` |

**Añadir también**, si no está, el identificador del depósito:

```yaml
identifiers:
  - type: doi
    value: <DOI_DE_CONCEPTO_DE_B2>
    description: "Concept DOI — resolves to the latest version"
```

**Aceptación:** `version` y `date-released` coinciden con el último release publicado en GitHub y con el registro de Zenodo.

---

### T4 — Corregir el DOI del manuscrito · BLOQUEADA POR B2

**Este es el defecto más grave de la lista.**

**Problema:** el manuscrito cita `10.5281/zenodo.22020014`, pero el registro vigente es `10.5281/zenodo.22821578` (v2.0.0, 18-sep-2026). La integración GitHub–Zenodo acuña **dos** DOI: uno de concepto (todas las versiones) y uno por versión. El artículo está citando un DOI de versión, y ya quedó obsoleto.

**Ocurrencias:**

| Archivo | Línea | Contenido |
|---|---|---|
| `paper/draft-v1.md` | 809 | ``*Code and frozen data: `https://doi.org/10.5281/zenodo.22020014`.*`` |
| `paper/tex/sections/10-reproducibility.tex` | 25 | `\emph{Code and frozen data: \texttt{https://doi.org/10.5281/zenodo.22020014}.}` |

**Acción:**

1. Editar **solo** `paper/draft-v1.md`, sustituyendo el DOI por el **DOI de concepto** de B2.
2. Regenerar: `python scripts/import_tex.py`.
3. Confirmar que `paper/tex/sections/10-reproducibility.tex` cambió solo por la regeneración.

> **Usar el DOI de concepto, no el de versión.** El de concepto resuelve siempre a la última versión y no se queda obsoleto en la próxima publicación. Este error es exactamente del tipo que el artículo documenta en su Apéndice B: un artefacto que queda rancio porque se regeneró solo una parte.

**Aceptación:** `grep -rn "22020014"` no devuelve coincidencias fuera de `.git/`. El DOI nuevo resuelve a una página de Zenodo válida.

---

### T5 — Retirar `paper/submission-plan.md` del repositorio público

**Problema:** es un documento de estrategia editorial, no de ciencia. Declara *"Decision: TMLR first, JRMV as plan B"* y argumenta por qué. Un editor de JRMV que lo encuentre se entera de que es la segunda opción.

**Acción:**

```bash
git rm --cached paper/submission-plan.md
```

Añadir a `.gitignore`:

```
paper/submission-plan.md
```

El archivo **se conserva en el disco local**: es útil, solo no debe ser público. No borrarlo del sistema de archivos.

**Aceptación:** `git ls-files | grep submission-plan` no devuelve nada; el archivo sigue existiendo localmente.

> Nota: queda en el historial de git. No hay que reescribir historia por esto — el costo de un `filter-branch` supera al beneficio, y el contenido no es sensible, solo inconveniente.

---

### T6 — Reubicar y reescribir `ESTADO.md`

**Problema, en tres partes:**

1. Expone la ruta local del autor: `C:\Users\fe_ma\AFMA_Repos\...` (líneas 11, 16, 89). No le sirve a ningún lector externo.
2. Está en español mientras todo el resto del repositorio está en inglés.
3. Es una bitácora interna, no documentación. Contiene la frase *"un `main.tex` transcrito a mano que reintrodujo una afirmación falsificada"*, que en contexto demuestra disciplina, pero fuera de contexto se lee muy distinto.

**Acción:**

1. `git mv ESTADO.md docs/repository-provenance.md`
2. Reescribir en inglés, conservando **solo** lo que le sirve a un lector externo:
   - qué archivo es la fuente de verdad de cada artefacto,
   - la regla de regeneración (markdown → LaTeX),
   - la lista de comandos de verificación,
   - por qué `references.bib` en la raíz está vacío a propósito.
3. **Eliminar:** todas las rutas locales absolutas, la narrativa de las dos carpetas duplicadas, y la referencia a la afirmación falsificada reintroducida. *(Ese episodio ya está contado, con el rigor y el contexto adecuados, en el Apéndice B del propio artículo. No necesita una segunda versión sin contexto.)*
4. Actualizar cualquier enlace a `ESTADO.md` en `README.md` u otros archivos.

**Aceptación:** `grep -rn "C:\\\\Users"` no devuelve coincidencias fuera de `.git/`. `docs/repository-provenance.md` está íntegramente en inglés.

---

### T7 — Cerrar la brecha de los datos congelados · DECISIÓN EN B3

**Este es el hallazgo más sustantivo de la auditoría.**

**Problema:** el `README.md` (líneas 137–147) instruye *"Commit the snapshots and the manifest"*, y `.gitignore` está configurado precisamente para permitirlo:

```
data/                    # línea 83
!data/snapshots/         # línea 86
!data/snapshots/**       # línea 87
```

**Pero no hay ni un solo archivo bajo `data/` rastreado por git.** Verificado: `git ls-files | grep -c "^data/"` devuelve `0`.

**Consecuencia:** un árbitro que clone el repositorio y siga el README no puede verificar los insumos congelados. Peor: al correr `python -m value_at_risk.data.snapshot` se descargan datos **de hoy**, y la verificación de hash pasa contra ese archivo nuevo — dando una falsa sensación de reproducibilidad. En un artículo cuya declaración de reproducibilidad afirma *"Inputs are frozen ten-year snapshots with sha256 manifests, verified on load"*, esto es una afirmación que el repositorio no sostiene.

**Dos caminos. Álvaro decide en B3:**

**Opción A — si los datos pueden redistribuirse (preferida):**

```bash
git add -f data/snapshots/
git commit -m "T7: commit frozen snapshots and manifest, as README instructs"
```

Verificar después que `python -m value_at_risk.data.snapshot --verify` pasa en un clon limpio.

**Opción B — si no pueden redistribuirse:**

Corregir el texto para que diga la verdad, en dos lugares:

1. `README.md`, sección *"Data is frozen, not fetched"*: sustituir *"Commit the snapshots and the manifest"* por una nota explícita de que los snapshots **no** viajan en el repositorio git por restricciones de licencia de la fuente, que sí están en el archivo de Zenodo, y cómo recuperarlos desde ahí.
2. `paper/draft-v1.md`, sección *Reproducibility statement*: añadir una frase que diga dónde están los insumos congelados y cómo obtenerlos. Regenerar el LaTeX después.

**Aceptación:** un clon limpio del repositorio permite, o bien verificar los hashes de los snapshots, o bien leer en el README exactamente dónde conseguirlos. No queda ninguna instrucción que no se pueda seguir.

---

### T8 — Verificar o suavizar la afirmación del número de tests

**Problema:** la declaración de reproducibilidad y `ESTADO.md` afirman `123 passed, 5 skipped`. Es un número exacto que un árbitro va a ejecutar. Si algún commit lo movió, la afirmación es falsa — en la sección del artículo dedicada precisamente a que las afirmaciones sean comprobables.

**Acción:**

1. Ejecutar `python -m pytest -q` y anotar el resultado real.
2. Si coincide con `123 passed, 5 skipped`: no cambiar nada y reportar la confirmación.
3. Si **no** coincide: actualizar la cifra en `paper/draft-v1.md` y regenerar el LaTeX. Actualizarla también en `docs/repository-provenance.md` (ex `ESTADO.md`).

**Aceptación:** la cifra del manuscrito coincide exactamente con la salida de `pytest` en el commit final.

---

## 3. Orden de ejecución

```
T5  (independiente, sin bloqueos)
T6  (independiente, sin bloqueos)
T1  (independiente, sin bloqueos)
T8  (independiente — ejecutar pytest primero)
T3  ← requiere B2 solo para el campo identifiers; el resto se puede hacer ya
T2  ← BLOQUEADA por B1
T4  ← BLOQUEADA por B2
T7  ← BLOQUEADA por B3
```

Ejecutar primero las cuatro sin bloqueo y reportar. Las bloqueadas quedan pendientes hasta que Álvaro entregue B1, B2 y B3.

---

## 4. Al terminar

1. Correr las cinco verificaciones de la sección 0. **Las cinco deben pasar.**
2. Si T1–T8 quedaron completas, publicar un release nuevo en GitHub (`v2.1.0`) para que Zenodo acuñe la versión actualizada — **después** de que T2, T3 y T4 estén cerradas, no antes.
3. Reportar: qué tareas se completaron, qué quedó pendiente y por qué, y la salida literal de las cinco verificaciones.

## 5. Qué NO hacer

- No modificar cifras, resultados, CSV de `outputs/` ni el ledger.
- No editar `paper/tex/sections/*.tex` a mano.
- No tocar `paper/_ssrn_v1_prior_anchored/`.
- No reescribir la historia de git.
- No cambiar el nombre del repositorio: rompería el vínculo con el depósito de Zenodo ya publicado.
- No "mejorar" la prosa del artículo. Las únicas ediciones de prosa autorizadas aquí son el DOI (T4), la nota de datos (T7-B) y el número de tests (T8).

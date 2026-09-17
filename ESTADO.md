# Estado del proyecto — dónde está cada cosa

Última verificación: 19 de agosto de 2026. Todo lo de abajo se comprobó ejecutando, no de
memoria.

---

## La carpeta canónica es ésta

```
C:\Users\fe_ma\AFMA_Repos\01_four_findings_var_audit
```

Es el repositorio git, tiene historial, y es donde se trabaja de ahora en adelante.

**La otra carpeta —`C:\Users\fe_ma\AFMA_Repos\quant-ai-lab\01_value_at_risk`— quedó obsoleta.**
Se comparó archivo por archivo: `paper/draft-v1.md`, `references.md`, `survey-ml-var.md`,
`explicacion-tecnica.md`, `submission-plan.md` son **idénticos** en ambas, y `src/`, `scripts/`
y `tests/` también. No hay contenido que rescatar salvo `images/functional_loss.png`, que ya se
copió aquí.

> **Por qué importa cerrar esto.** Este paper documenta tres casos de "regeneración parcial
> produce un artefacto rancio" (Apéndice B) y un cuarto —un `main.tex` transcrito a mano que
> reintrodujo una afirmación falsificada. Dos carpetas con el mismo proyecto es la misma
> trampa a mayor escala. Una sola, o el problema vuelve.

---

## La versión definitiva del artículo

| qué | dónde |
|---|---|
| **Fuente de verdad de la prosa** | `paper/draft-v1.md` |
| **PDF compilado** | `main.pdf` — 18 páginas, con autor y AFMA |
| **LaTeX raíz** | `main.tex` — solo estructura; hace `\input` de las secciones |
| **Secciones LaTeX** | `paper/tex/sections/*.tex` — **generadas**, no editar a mano |
| **Bibliografía** | `paper/tex/refs.bib` (42 entradas verificadas) |
| **Figuras** | `paper/tex/figures/` |

**Regla de oro:** la prosa se edita en `paper/draft-v1.md`. Después:

```powershell
python scripts/import_tex.py     # regenera las secciones
latexmk -pdf main.tex            # recompila el PDF
```

`references.bib` en la raíz está **vacío a propósito**, con una nota de reemplazo. Si algo lo
usa, falla ruidosamente en vez de compilar una bibliografía obsoleta.

---

## Documentos de apoyo

| documento | para qué |
|---|---|
| `paper/explicacion-tecnica.md` | **La guía para defender el paper.** Toda la matemática, los tests, y los puntos atacables ordenados por peligrosidad. En español. |
| `paper/submission-plan.md` | Dónde publicar y en qué orden. Zenodo → SSRN → TMLR. |
| `paper/references.md` | Bibliografía auditada: 47 entradas, cada una verificada contra el registro publicado. |
| `paper/survey-ml-var.md` | La encuesta de 5 papers ML-VaR bajo esquema pre-fijado. |
| `docs/preparation-log.md` | Qué condición levantó qué rol y cómo se cerró. |

---

## Verificaciones — se corren antes de publicar, no se recuerdan

```powershell
python -m pytest -q                              # 123 passed, 5 skipped
python scripts/refresh_paper_figures.py --check  # resúmenes vs CSV de resultados
python scripts/import_tex.py --check             # LaTeX al día con el markdown
python scripts/check_bib.py                      # refs.bib vs references.md
python -m value_at_risk.evaluation.ledger --summary   # los enteros de divulgación
```

Las cuatro pasan al 19 de agosto de 2026.

---

## Basura por borrar (no pude, permisos del sandbox)

**En esta carpeta:**

```powershell
Remove-Item tmp1.tmp, tmp2.tmp, tmp3.tmp, tmp4.tmp, zih05dg5, overleaf-upload.zip
```

**En `quant-ai-lab\01_value_at_risk`** (41 archivos de build que generé peleando con Overleaf):

```powershell
cd C:\Users\fe_ma\AFMA_Repos\quant-ai-lab\01_value_at_risk\paper\tex
Remove-Item tmp*.tmp, build-named.*, v2anon.*, v2named.*, anon.flag
```

Y cuando confirmes que no falta nada, la carpeta `quant-ai-lab\01_value_at_risk` completa
puede archivarse o borrarse.

---

## Overleaf — cerrado sin resolver

No se logró conectar el repositorio. Se descartó, con evidencia: 142 archivos, 0 artefactos
LaTeX, archivo mayor de 256 KB, sin caracteres especiales ni no-ASCII en los nombres,
historial de 5,1 MB, profundidad máxima 5. Nada en el contenido justifica el fallo, y la
causa está del lado de Overleaf.

**No es un bloqueo.** El PDF se compila localmente con `latexmk` y el destino inmediato es
SSRN, que recibe un PDF. Si en algún momento hace falta un editor colaborativo, la vía es
subir `paper/tex` comprimido con *Upload Project*, que no requiere integración.

---

## Lo que sigue

1. **Zenodo** — DOI del repositorio. Está en la ruta crítica: `paper/tex/sections/10-reproducibility.tex`
   tiene un placeholder `[repository DOI]` que hay que llenar antes de publicar.
2. **SSRN** — con `main.pdf` y el encuadre de marca acordado: *publicamos nuestra propia tasa
   de error; la mayoría de las firmas no mide la suya*.
3. **TMLR** — cuando quieras revisión por pares. Sin apuro, y con el build anónimo.

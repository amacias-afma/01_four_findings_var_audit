# Publicar: Zenodo primero, SSRN después

## Por qué Zenodo te pide archivos y no carpetas

La subida manual de Zenodo acepta archivos sueltos. Pero **no la vas a usar**: existe una
integración nativa con GitHub que archiva el repositorio completo y mintea el DOI sola.
Es gratis y es exactamente para esto.

---

## Zenodo — cuatro pasos

**1. Conectar la cuenta**

Entra a [zenodo.org](https://zenodo.org) y **inicia sesión con GitHub** (no con correo — la
integración necesita ese vínculo). Autoriza la aplicación cuando GitHub lo pida.

**2. Activar el repositorio**

Ve a <https://zenodo.org/account/settings/github/> y pon el interruptor en **On** para
`01_four_findings_var_audit`.

> **El repositorio tiene que ser público.** Si está privado, Zenodo no lo ve.

**3. Crear un release en GitHub**

Éste es el paso que la gente se salta. **El DOI no se genera al activar el interruptor, sino
al publicar un release.**

En GitHub: *Releases → Create a new release* → tag `v1.0.0` → título
`Four Findings That Dissolved — v1.0.0` → *Publish release*.

O desde PowerShell:

```powershell
git tag -a v1.0.0 -m "Four Findings That Dissolved - archived release"
git push origin v1.0.0
```

(el tag por sí solo no basta; hay que publicar el *release* desde la web de GitHub)

**4. Recoger el DOI**

Aparece en <https://zenodo.org/me/uploads> a los pocos minutos. Verás **dos**:

- **DOI de versión** — apunta a `v1.0.0` exactamente
- **DOI de concepto** ("Cite all versions") — apunta siempre a la última

**Usa el de concepto en el paper.** Así, cuando publiques v1.0.1, el enlace del artículo
sigue resolviendo sin tener que reeditar nada.

---

## El problema del huevo y la gallina

El paper necesita el DOI, y el DOI sale de archivar el repositorio que contiene el paper.

**Se resuelve en dos releases:**

1. `v1.0.0` → Zenodo mintea el DOI de concepto
2. Pones ese DOI en `paper/draft-v1.md` (reemplazando
   `[repository DOI — to be minted at submission]`), corres `python scripts/import_tex.py`,
   recompilas
3. `v1.0.1` → el archivo se actualiza; **el DOI de concepto no cambia**

Es el flujo estándar. No hay forma de conocer el DOI antes del primer release.

---

## Metadatos: ya están listos

Zenodo lee tres archivos de la raíz para armar el registro. Los tres se crearon:

| archivo | qué controla |
|---|---|
| `.zenodo.json` | título, descripción, autor, afiliación, keywords, licencia |
| `CITATION.cff` | el widget "Cite this repository" de GitHub, y metadatos de citación |
| `LICENSE` | MIT para el código; CC BY 4.0 para el manuscrito y las figuras |

**Dos cosas que deberías revisar antes del release:**

- **Tu ORCID.** `CITATION.cff` tiene la línea comentada. Si no tienes, se saca gratis en
  [orcid.org](https://orcid.org) en cinco minutos — y para construir marca vale la pena, porque
  es lo que enlaza este trabajo con el que venga después.
- **La licencia.** Puse MIT para el código y CC BY 4.0 para el paper, que es la combinación
  habitual en investigación reproducible. Si prefieres otra, cámbiala antes de publicar: **una
  vez que Zenodo mintea el DOI, el registro es permanente.**

---

## SSRN — después, no antes

Con el DOI ya dentro del PDF:

1. Cuenta gratuita en [ssrn.com](https://www.ssrn.com)
2. *Submit a paper* → subes el PDF
3. Moderación: **1 a 3 días hábiles**, hasta 10 en el peor caso

**El encuadre para el abstract y para LinkedIn**, que es lo que hace que este paper trabaje a
favor de tu marca en vez de en contra:

> Publicamos nuestra propia tasa de error. La mayoría de las firmas no mide la suya.

Sin esa frase, un lector apurado ve "estos cometieron cinco errores de cita y retiraron cuatro
hallazgos". Con ella, ve una firma que puede demostrar rigor en vez de afirmarlo — que es lo
poco imitable.

---

## Antes de darle a publicar

```powershell
python -m pytest -q                              # 115 passed, 5 skipped
python scripts/refresh_paper_figures.py --check
python scripts/import_tex.py --check
python scripts/check_bib.py
latexmk -pdf -g main.tex
```

Y una comprobación que no es automatizable: **abre el PDF y busca el DOI.** Si sigue diciendo
`[repository DOI — to be minted at submission]`, el release no se aplicó al manuscrito.

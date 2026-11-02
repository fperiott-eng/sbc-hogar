# Casa de Lautaro — base de conocimiento (SBC)

Base de conocimiento **individual** para la asignatura de Sistemas Basados en
Conocimiento. Es un proyecto hermano de `fdi_sbc_26g4` (el trabajo de equipo) y
reutiliza su mismo motor de inferencia.

La base modela **la casa de Lautaro**, de tres plantas, donde viven Lautaro, su
madre **Paola**, su hermana **Caterina** y el perro **Zuri**. También aparece el
vecino **Ramón** con sus mascotas (el gato gris, el gato blanco y el perro
Bobby), que no viven en la casa.

## Formato

El conocimiento se escribe como **tripletas** `sujeto predicado objeto`:

- Las **variables** empiezan por mayúscula (`X`, `P`, `N`...).
- Los **literales** van entre comillas dobles: `salon nombre "Salón"`.
- Las **afirmaciones** terminan en `.` y las **consultas** en `?`.

El parser oficial es `sbc/profesor.py` y **no se modifica**.

## Estructura

```
data/casa/
  00_nombres.sbc     Nombre legible de cada identificador (predicado nombre).
  01_clases.sbc      Clases (es_un) y sexo de las personas.
  02_familia.sbc     Relaciones familiares (rama materna) y amigos.
  03_casa.sbc        Plantas, habitaciones, balcones y exterior (patios).
  04_habitantes.sbc  Quién vive, duerme y qué baño usa; las mascotas.
  05_objetos.sbc     Objetos por habitación, con color y material.
  06_acciones.sbc    Qué se hace en cada sitio (se_hace_en, puede_hacer).
  07_adicional.sbc   Curiosidades del día a día.
  script.sbq         Consultas de ejemplo.
  expected.jsonl     Salida esperada del script (generada con el motor).
```

## Cómo ejecutar

Respuestas en formato legible:

```bash
uv run -m sbc data/casa data/casa/script.sbq
```

Respuestas en JSON Lines (como `expected.jsonl`):

```bash
uv run -m sbc data/casa data/casa/script.sbq --jsonl
```

## Ejemplos de consultas

- `X nombre "Zuri"?` — ¿qué identificador se llama "Zuri"?
- `X es_un dormitorio, X tiene_balcon B?` — dormitorios que tienen balcón.
- `P duerme_en D, D esta_en_planta planta_segunda?` — quién duerme en la planta de arriba.
- `M mascota_de ramon, M es_un perro, M nombre N?` — los perros del vecino.

# Casa de Lautaro — base de conocimiento (SBC)

Base de conocimiento **individual** para la asignatura de Sistemas Basados en
Conocimiento. Es un proyecto hermano de `fdi_sbc_26g4` (el trabajo de equipo) y
reutiliza su mismo motor de inferencia.

La base modela **la casa de Lautaro**, de tres plantas, donde viven Lautaro, su
madre **Paola**, su hermana **Caterina** y el perro **Zuri**. También aparece el
vecino **Ramón** con sus mascotas (el gato gris, el gato blanco y el perro
Bobby), que no viven en la casa.

Además de describir la casa, la base la **automatiza**: incorpora dispositivos
domóticos, sensores y **reglas** que deducen cómo debe comportarse la vivienda
ante cada situación, incluyendo **situaciones de conflicto** entre objetivos.

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
  08_domotica.sbc    Dispositivos: luces, persianas, termostatos, cerradura, alarma.
  09_sensores.sbc    Sensores (presencia, temperatura, humo) y políticas de prioridad.
  10_reglas.sbc      Reglas de razonamiento domótico y de conflictos.
  script.sbq         Consultas y escenarios de ejemplo.
  escenario_humo.sbq Escenario de incendio, cargable desde el script.
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

Modo interactivo (sin script), para escribir hechos, reglas, consultas y
comandos a mano:

```bash
uv run -m sbc data/casa
```

Comandos disponibles: `descubre!` (razona hacia delante), `imprimir!` (vuelca la
base por `stderr`) y `cargar FICHERO!` (ejecuta otro script).

## Ejemplos de consultas

- `X nombre "Zuri"?` — ¿qué identificador se llama "Zuri"?
- `X es_un dormitorio, X tiene_balcon B?` — dormitorios que tienen balcón.
- `P duerme_en D, D esta_en_planta planta_segunda?` — quién duerme en la planta de arriba.
- `M mascota_de ramon, M es_un perro, M nombre N?` — los perros del vecino.

## Automatización domótica

La casa no solo se describe: se **comporta**. Cada dispositivo se liga a lo que
controla con un predicado propio — `ilumina`, `cubre`, `climatiza`, `protege`,
`vigila` — y hay sensores de presencia, temperatura y humo. Las **lecturas
dinámicas** (quién está en cada habitación, si es de noche, si hace frío, si la
casa está en modo ahorro, si hay humo) no se fijan en la base: se introducen en
los **escenarios** del script, y la casa reacciona a ellas.

## Razonamiento y conflictos

El comando `descubre!` aplica las reglas **hacia delante** (forward chaining)
hasta punto fijo: deduce todo lo que se puede concluir combinando el
conocimiento. Por ejemplo, la luz de una habitación debe encenderse si hay
presencia y es de noche:

```
L debe encender <- L ilumina H, H tiene_presencia si, contexto es_noche si.
```

El motor es de **lógica monótona y sin negación**: no se pueden retractar
hechos. Por eso un **conflicto** no se resuelve borrando un objetivo, sino que
se **detecta** con una regla y se emite un **veredicto** según una política
estática de la casa:

```
L en_conflicto luz <- L debe encender, L debe apagar.
L prioriza descanso <- L en_conflicto luz, politica prioriza descanso_sobre_luz.
```

Se modelan dos conflictos y un protocolo de seguridad:

- **Luz vs descanso:** de noche, la luz de un dormitorio ocupado debe encenderse,
  pero si quien está allí quiere dormir también debe apagarse. Gana el descanso.
- **Confort vs ahorro:** con frío y gente, el termostato debe subir, pero en modo
  ahorro debe apagarse. Gana el confort.
- **Seguridad (humo):** si un sensor detecta humo, se dispara la evacuación: suena
  la alarma, se abre la cerradura y se encienden todas las luces para salir.

## Generalidad

Las reglas están escritas con **variables**, de modo que ampliar la casa no
obliga a reescribirlas. Añadir una habitación nueva con su luz, persiana o
termostato (con los hechos `ilumina` / `cubre` / `climatiza`) basta para que todo
el razonamiento funcione sobre ella sin tocar `10_reglas.sbc`.

## Decisiones de diseño

- Todo el conocimiento son **tripletas** `sujeto predicado objeto`.
- Los hechos de tipo booleano se escriben con la convención `sujeto predicado si`
  (p. ej. `contexto es_noche si`, `caterina quiere_dormir si`).
- Se separan los **hechos estáticos** (en los `.sbc`: estructura, dispositivos,
  políticas) de las **lecturas dinámicas** (en los escenarios `.sbq`), que son las
  que cambian de una situación a otra.
- Cada identificador tiene su nombre legible con el predicado `nombre`.
- El parser oficial `sbc/profesor.py` **no se toca**.

## Escenarios de prueba

`script.sbq` incluye dos escenarios; `expected.jsonl` recoge su salida esperada.

1. **Escenario nocturno.** Es de noche; Lautaro está en el salón y Caterina en su
   dormitorio queriendo dormir; hace frío en el salón y la casa está en modo
   ahorro. Al razonar: se encienden las luces de las zonas ocupadas, bajan todas
   las persianas y se detectan y resuelven los dos conflictos (la luz del cuarto
   de Caterina prioriza el descanso; el termostato del salón, el confort).
2. **Escenario de humo** (cargado con `cargar data/casa/escenario_humo.sbq!`). El
   sensor de la cocina detecta humo y, al volver a razonar, se dispara el
   protocolo: la casa debe evacuar, suena la alarma, se abre la cerradura y se
   encienden todas las luces.

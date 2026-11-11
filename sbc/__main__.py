
from sbc.profesor import cargar_KB, cargar_script, imprimir_jsonl, leer_frases
from pathlib import Path
import sys
import click
from loguru import logger

@click.command()
@click.argument("directorio", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("ubiscript", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--jsonl", is_flag=True, help="Imprime las respuestas en formato JSON Lines.")
@click.option(
    "-i",
    "--interactivo",
    is_flag=True,
    help="Entra en modo interactivo tras ejecutar el script.",
)
def main(directorio: Path, ubiscript: Path | None, jsonl: bool, interactivo: bool):

    sbc = cargar_KB(Path(directorio))

    # base: índice de hechos por predicado. nombres: término -> nombre legible,
    # reglas: reglas (consecuente, antecedente) a aplicar.
    base = {}
    nombres = {}
    reglas = []
    for frase in sbc:
        procesar(frase, base, nombres, reglas, jsonl)

    # Si hay script, se ejecutan sus frases.
    if ubiscript is not None:
        for frase in cargar_script(Path(ubiscript)):
            procesar(frase, base, nombres, reglas, jsonl)

    # Sin script se entra en modo interactivo; con -i, además tras el script.
    if ubiscript is None or interactivo:
        modo_interactivo(base, nombres, reglas, jsonl)


def anadir_hechos(base, nombres, hechos):
    'Indexa una lista de hechos en la base (por predicado) y guarda sus nombres.'
    for hecho in hechos:
        base.setdefault(hecho[1], set()).add(hecho)
        if hecho[1] == "nombre":
            nombres[hecho[0]] = hecho[2].strip('"')


def procesar(frase, base, nombres, reglas, jsonl):
    'Procesa una frase parseada (afirmación, regla, pregunta o comando).'
    etiqueta = frase[0]
    if etiqueta == "afirmacion":
        anadir_hechos(base, nombres, frase[1])
    elif etiqueta == "regla":
        reglas.append(frase[1])
    elif etiqueta == "pregunta":
        afirmacion, variables = pregunta(frase, base)
        resultado(frase, afirmacion, variables, nombres, jsonl)
    elif etiqueta == "comando":
        ejecutar_comando(frase[1], base, nombres, reglas, jsonl)


def descubrir(base, nombres, reglas):
    'Razonamiento hacia delante: aplica las reglas hasta punto fijo y devuelve cuántos hechos nuevos deduce.'
    total = 0
    while True:
        # Una pasada por todas las reglas, recogiendo lo que se deduce.
        nuevos = []
        for consecuente, antecedente in reglas:
            # El antecedente se resuelve con la misma unificación que una consulta.
            _, soluciones = pregunta(("pregunta", antecedente), base)
            for binding in soluciones:
                for hecho in consecuente:
                    deducido = tuple(binding.get(t, t) for t in hecho)
                    if any(es_variable(t) for t in deducido):
                        continue  # no añadimos hechos con variables libres
                    if deducido not in base.get(deducido[1], ()):
                        nuevos.append(deducido)

        # Añadimos los hechos nuevos (sin duplicar). Sin novedades -> punto fijo.
        anadidos = 0
        for hecho in nuevos:
            conjunto = base.setdefault(hecho[1], set())
            if hecho not in conjunto:
                conjunto.add(hecho)
                if hecho[1] == "nombre":
                    nombres[hecho[0]] = hecho[2].strip('"')
                anadidos += 1

        total += anadidos
        if anadidos == 0:
            break

    logger.info(f"Descubiertos {total} hechos nuevos")
    return total


def ejecutar_comando(palabras, base, nombres, reglas, jsonl):
    'Ejecuta un comando (frases acabadas en !): descubre, imprimir, cargar.'
    match palabras:
        case ["descubre"]:
            descubrir(base, nombres, reglas)
        case ["imprimir"]:
            imprimir_base(base, reglas)
        case ["cargar", fichero]:
            for frase in cargar_script(Path(fichero)):
                procesar(frase, base, nombres, reglas, jsonl)
        case _:
            logger.error(f"Comando desconocido: {' '.join(palabras)}!")


def imprimir_base(base, reglas):
    'Imprime todo el conocimiento de la base con el comando imprimir.'
    for conjunto in base.values():
        for hecho in sorted(conjunto):
            print(" ".join(hecho), file=sys.stderr)
    for consecuente, antecedente in reglas:
        cons = ", ".join(" ".join(h) for h in consecuente)
        ante = ", ".join(" ".join(h) for h in antecedente)
        print(f"{cons} <- {ante}.", file=sys.stderr)


def menu_ayuda():
    'Muestra los comandos disponibles en el modo interactivo.'
    print("Comandos del modo interactivo:")
    print("  sujeto predicado objeto.   añade un hecho   (ej: ana madre_de luis.)")
    print("  consecuente <- antecedente.  añade una regla")
    print("                             (ej: X abuela_de Z <- X madre_de Y, Y madre_de Z.)")
    print("  sujeto predicado objeto?   consulta         (ej: X madre_de luis?)")
    print("                             (las palabras con Mayúscula inicial son variables)")
    print("  descubre!                  razona hacia delante (deduce hechos nuevos)")
    print("  imprimir!                  imprime toda la base por stderr")
    print("  cargar FICHERO!            carga y ejecuta un script")
    print("  ayuda                      vuelve a mostrar esta ayuda")
    print("  salir                      termina el programa")
    print()


def modo_interactivo(base, nombres, reglas, jsonl):
    '''
    Lee afirmaciones y consultas del usuario, línea a línea, y responde.

    Las afirmaciones se añaden a la base; las consultas se resuelven al momento.
    Un error de sintaxis no interrumpe la sesión: se avisa y se sigue pidiendo
    (Ctrl-C cancela la línea; Ctrl-D o una línea vacía con fin de entrada sale).
    '''
    try:
        import readline  # noqa: F401  (edición de línea e historial, si existe)
    except ImportError:
        pass

    menu_ayuda()

    while True:
        try:
            linea = input("sbc> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        # Ctrl-D (\x04) y Ctrl-Z (\x1a) salen. En Linux/Mac Ctrl-D genera un
        # EOFError (arriba); en Windows no, y la terminal mete el carácter de
        # control dentro de la línea, así que aquí también lo reconocemos.
        if "\x04" in linea or "\x1a" in linea:
            print()
            break

        orden = linea.strip().lower()

        # Salir con una orden explícita (más cómodo que Ctrl-D/Ctrl-Z).
        if orden in ("salir", "exit", "fin", "quit"):
            break

        # Volver a mostrar el menú de comandos.
        if orden in ("ayuda", "help"):
            menu_ayuda()
            continue

        for frase in leer_frases(linea):
            procesar(frase, base, nombres, reglas, jsonl)


def pregunta(p, base):
    # p[0] es pregunta/afirmación y p[1] es una lista de hechos (cada hecho es una tupla de 3)

    # Comprobamos que no sea una afirmación
    if p[0] != 'pregunta':
        return False, []

    # Lista de variables
    variables = [{}]

    # Recorremos hecho a hecho de nuestro input
    for hecho_pregunta in p[1]:

        # Para almacenar todas los valores posibles que puede tomar una variable
        posibilidades = []
        for v in variables:

            # Recorremos hecho a hecho de nuestra base
            for hecho_base in candidatos(hecho_pregunta, base, v):

                # Comparamos (None, si no coinciden o hay inconsistencia con las variables)
                comparacion = compara(hecho_pregunta, hecho_base, v)

                # Almacenamos la(s) variable(s) encontradas en nuestra afirmación
                if comparacion is not None:
                    posibilidades.append(comparacion)

        variables = posibilidades

        if len(variables) == 0:
            return False, variables

    return True, variables


def candidatos(hecho_pregunta, base, variables):
    predicado = variables.get(hecho_pregunta[1], hecho_pregunta[1])

    # Si el predicado es una variable sin asignar, hay que mirarlos todos
    if es_variable(predicado):
        return [h for hechos in base.values() for h in hechos]

    return base.get(predicado, ())


'''
def compara(pregunta, hecho_base):

    for i, elem in enumerate(pregunta):
        if not es_variable(elem) and elem != hecho_base[i]:
            return False

    return True
'''


def compara(pregunta, hecho_base, variables):
    '''
    Función de comparación entre una pregunta y un hecho.
    '''

    nuevas_variables = variables.copy()

    for i, elem in enumerate(pregunta):

        if es_variable(elem): # Comprobamos si es X o Y

            # Si en nuestro hecho ya existía la variable
            if elem in nuevas_variables:

                # Comprobamos que el elemento sea el mismo -> sino False
                if nuevas_variables[elem] != hecho_base[i]:
                    return None

            # Si no existía la variable -> la añadimos
            else:
                nuevas_variables[elem] = hecho_base[i]

        # Si no es variable, comparamos los elementos
        elif elem != hecho_base[i]:
            return None

    return nuevas_variables


def resultado(preg, afirmacion, variables, nombres, jsonl):
    '''
    Imprime la respuesta a una consulta.

    Con --jsonl se usa la salida JSON Lines de profesor.py (exacta, para el
    corrector). Sin opciones se imprime un formato legible en el terminal.
    '''
    if jsonl:
        imprimir_jsonl(preg[1], variables)
    else:
        imprimir_bonito(preg[1], variables, nombres)


def imprimir_bonito(consulta, soluciones, nombres):
    '''
    Imprime una consulta y sus soluciones de forma legible para una persona,
    mostrando el nombre de cada término cuando se conoce.
    '''
    # Términos de la consulta, en orden, y cuáles son variables.
    terminos = dict.fromkeys(t for hecho in consulta for t in hecho)
    incognitas = [t for t in terminos if es_variable(t)]

    # Mismas soluciones únicas y ordenadas que imprime imprimir_jsonl.
    unicas = {
        tuple((t, s[t]) for t in terminos if t in s) for s in map(dict, soluciones)
    }
    ordenadas = [dict(s) for s in sorted(unicas, key=lambda s: [v for _, v in s])]

    texto_consulta = ", ".join(" ".join(hecho) for hecho in consulta)
    print(f"❯ {texto_consulta}")

    # Consulta sin variables: es un sí/no.
    if not incognitas:
        print("  sí" if ordenadas else "  no")
        print()
        return

    if not ordenadas:
        print("  sin soluciones")
        print()
        return

    n = len(ordenadas)
    print(f"  {n} solución" if n == 1 else f"  {n} soluciones")
    for s in ordenadas:
        partes = [f"{var} = {_con_nombre(s[var], nombres)}" for var in incognitas if var in s]
        print("    " + "   ".join(partes))
    print()


def _con_nombre(valor, nombres):
    'Devuelve el valor y, si se conoce, su nombre legible entre paréntesis.'
    nombre = nombres.get(valor)
    if nombre and nombre != valor.strip('"'):
        return f"{valor}  ({nombre})"
    return valor


def es_variable(palabra):
    'Devuelve si un elemento es una variable o no'
    return palabra[:1].isupper()


if __name__ == "__main__":
    main()
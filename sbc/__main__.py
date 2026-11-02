
from sbc.profesor import cargar_KB, cargar_script, imprimir_jsonl
from pathlib import Path
import click

@click.command()
@click.argument("directorio", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("ubiscript", required=False, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--jsonl", is_flag=True, help="Imprime las respuestas en formato JSON Lines.")

def main(directorio: Path, ubiscript: Path | None, jsonl: bool):

    sbc = cargar_KB(Path(directorio))
    script = cargar_script(Path(ubiscript))

    base = {}

    for dato in sbc:

        for d in dato[1]:
            base.setdefault(d[1], set()).add(d)

    # Diccionario término -> nombre legible, para mostrar las respuestas bonitas.
    # (p. ej. "q716794" -> 'Fëanor'). Solo se usa para imprimir, no para inferir.
    nombres = {hecho[0]: hecho[2].strip('"') for hecho in base.get("nombre", ())}

    for preg in script:
        afirmacion, variables = pregunta(preg, base)
        resultado(preg, afirmacion, variables, nombres, jsonl)

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
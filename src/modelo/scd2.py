"""Carga incremental de la dimensión cliente (SCD tipo 2).

El build construye dim_customer desde cero con todo el historial. En la vida
real, después llegan lotes de cambios ("estos clientes tienen dirección
nueva") y hay que aplicarlos sin reconstruir todo. Eso hace esta función.
"""

from datetime import datetime

import duckdb
import pandas as pd


def apply_customer_changes(
    con: duckdb.DuckDBPyConnection,
    changes: pd.DataFrame,
    effective_at: datetime,
) -> dict[str, int]:
    """Aplica un lote de direcciones de clientes a dim_customer.

    `changes` tiene las columnas: customer_unique_id, zip_prefix, city, state.

    Para cada fila del lote:
      * Cliente que no existe          -> 'nuevos': inserta una versión actual
                                          con valid_from = effective_at.
      * Existe y la dirección cambió   -> 'cambiados': cierra la versión actual
                                          (valid_to = effective_at, is_current = false)
                                          e inserta una nueva desde effective_at.
      * Existe y la dirección es igual -> 'sin_cambio': no hace nada.

    Devuelve cuántos hubo de cada tipo:
        {"nuevos": 1, "cambiados": 1, "sin_cambio": 1}

    Requisitos:
      * Idempotente: aplicar el mismo lote dos veces no cambia nada la
        segunda vez (todo queda como 'sin_cambio').
      * Las llaves nuevas (customer_key) no pueden repetir llaves existentes.
      * El cierre y la inserción deben ocurrir juntos o no ocurrir
        (pista: con.execute("BEGIN") ... con.execute("COMMIT")).

    Pistas:
      * con.register("changes", changes) te deja usar el DataFrame como una
        tabla en SQL.
      * Clasifica primero (LEFT JOIN contra la versión actual), luego UPDATE,
        luego INSERT.
    """
    raise NotImplementedError("TODO: implementa la carga incremental SCD2")

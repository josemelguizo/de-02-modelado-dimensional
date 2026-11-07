"""Pruebas del modelo dimensional.

Usan un mini Olist de 5 pedidos (tests/fixtures) donde conoces la respuesta
correcta de antemano. Lee los CSV de fixtures para entender cada prueba.
Todas fallan al principio: tu trabajo es hacerlas pasar.
"""

from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from modelo.build import build_warehouse
from modelo.scd2 import apply_customer_changes

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def con():
    c = duckdb.connect()
    build_warehouse(c, FIXTURES)
    yield c
    c.close()


def one(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


# ---------- dim_date ----------

def test_dim_date_cubre_todo_el_rango_sin_huecos(con):
    # Primer pedido 2018-01-10, último 2018-05-20: 131 días
    assert one(con, "SELECT COUNT(*) FROM dim_date") == 131
    assert one(con, "SELECT COUNT(DISTINCT date_key) FROM dim_date") == 131
    assert one(con, "SELECT MIN(date_key) FROM dim_date") == 20180110
    assert one(con, "SELECT MAX(date_key) FROM dim_date") == 20180520


def test_dim_date_atributos(con):
    row = con.execute(
        "SELECT year, quarter, month, day, weekday, is_weekend FROM dim_date WHERE date_key = 20180310"
    ).fetchone()
    assert row == (2018, 1, 3, 10, 6, True)  # 10 de marzo de 2018 fue sábado


# ---------- dim_product y dim_seller ----------

def test_dim_product_traduce_categoria_y_rellena_nulos(con):
    cats = dict(con.execute("SELECT product_id, category FROM dim_product").fetchall())
    assert cats == {"p1": "health_beauty", "p2": "computers_accessories", "p3": "unknown"}


def test_dim_product_volumen(con):
    assert one(con, "SELECT volume_cm3 FROM dim_product WHERE product_id = 'p1'") == 3000


@pytest.mark.parametrize("table,key", [
    ("dim_product", "product_key"), ("dim_seller", "seller_key"), ("dim_customer", "customer_key"),
])
def test_llaves_sustitutas_unicas_y_no_nulas(con, table, key):
    total, distinct, nulls = con.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT {key}), COUNT(*) - COUNT({key}) FROM {table}"
    ).fetchone()
    assert total == distinct and nulls == 0


def test_codigo_postal_conserva_ceros(con):
    assert one(con, "SELECT zip_prefix FROM dim_customer WHERE city = 'sao paulo'") == "01000"


# ---------- dim_customer (SCD tipo 2) ----------

def test_scd2_versiones_por_cliente(con):
    versions = dict(con.execute(
        "SELECT customer_unique_id, COUNT(*) FROM dim_customer GROUP BY 1"
    ).fetchall())
    # u1 se mudó de São Paulo a Rio; u2 compró dos veces sin mudarse
    assert versions == {"u1": 2, "u2": 1, "u3": 1}


def test_scd2_una_sola_version_actual(con):
    assert one(con, """
        SELECT COUNT(*) FROM (
            SELECT customer_unique_id FROM dim_customer
            GROUP BY 1 HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1
        )""") == 0


def test_scd2_intervalos_continuos(con):
    rows = con.execute("""
        SELECT city, valid_from, valid_to, is_current FROM dim_customer
        WHERE customer_unique_id = 'u1' ORDER BY valid_from
    """).fetchall()
    sp, rj = rows
    assert sp[0] == "sao paulo" and rj[0] == "rio de janeiro"
    assert sp[2] == rj[1] == datetime(2018, 3, 5, 20, 40)   # termina una, empieza la otra
    assert sp[1] == datetime(1900, 1, 1)
    assert rj[2] == datetime(9999, 12, 31)
    assert (sp[3], rj[3]) == (False, True)


# ---------- fact_order_items ----------

def test_fact_grano_un_registro_por_item(con):
    assert one(con, "SELECT COUNT(*) FROM fact_order_items") == 6
    assert one(con, "SELECT COUNT(DISTINCT (order_id, order_item_id)) FROM fact_order_items") == 6


def test_fact_totales_cuadran(con):
    assert one(con, "SELECT SUM(price) FROM fact_order_items") == 365
    assert one(con, "SELECT SUM(freight_value) FROM fact_order_items") == 49


@pytest.mark.parametrize("fk,dim,pk", [
    ("customer_key", "dim_customer", "customer_key"),
    ("product_key", "dim_product", "product_key"),
    ("seller_key", "dim_seller", "seller_key"),
    ("purchase_date_key", "dim_date", "date_key"),
])
def test_fact_sin_huerfanos(con, fk, dim, pk):
    assert one(con, f"""
        SELECT COUNT(*) FROM fact_order_items f
        LEFT JOIN {dim} d ON f.{fk} = d.{pk}
        WHERE d.{pk} IS NULL""") == 0


def test_fact_usa_la_version_del_cliente_vigente_al_comprar(con):
    cities = dict(con.execute("""
        SELECT f.order_id, c.city FROM fact_order_items f
        JOIN dim_customer c USING (customer_key)
        WHERE f.order_id IN ('o1', 'o2')
    """).fetchall())
    assert cities == {"o1": "sao paulo", "o2": "rio de janeiro"}


def test_fact_dias_de_entrega(con):
    days = dict(con.execute(
        "SELECT DISTINCT order_id, delivery_days FROM fact_order_items"
    ).fetchall())
    assert days["o1"] == 8
    assert days["o4"] is None   # enviado pero no entregado
    assert days["o5"] is None   # cancelado


# ---------- carga incremental SCD2 ----------

CHANGES = pd.DataFrame([
    {"customer_unique_id": "u2", "zip_prefix": "80000", "city": "curitiba", "state": "PR"},       # se mudó
    {"customer_unique_id": "u3", "zip_prefix": "40000", "city": "salvador", "state": "BA"},       # igual
    {"customer_unique_id": "u4", "zip_prefix": "50000", "city": "recife", "state": "PE"},         # nuevo
])
EFFECTIVE = datetime(2018, 9, 1)


def test_merge_scd2_cuenta_cada_caso(con):
    result = apply_customer_changes(con, CHANGES, EFFECTIVE)
    assert result == {"nuevos": 1, "cambiados": 1, "sin_cambio": 1}


def test_merge_scd2_cierra_la_version_anterior(con):
    apply_customer_changes(con, CHANGES, EFFECTIVE)
    rows = con.execute("""
        SELECT city, valid_from, valid_to, is_current FROM dim_customer
        WHERE customer_unique_id = 'u2' ORDER BY valid_from
    """).fetchall()
    assert rows == [
        ("belo horizonte", datetime(1900, 1, 1), EFFECTIVE, False),
        ("curitiba", EFFECTIVE, datetime(9999, 12, 31), True),
    ]


def test_merge_scd2_es_idempotente(con):
    apply_customer_changes(con, CHANGES, EFFECTIVE)
    second = apply_customer_changes(con, CHANGES, EFFECTIVE)
    assert second == {"nuevos": 0, "cambiados": 0, "sin_cambio": 3}
    assert one(con, "SELECT COUNT(*) FROM dim_customer") == 6
    assert one(con, "SELECT COUNT(DISTINCT customer_key) FROM dim_customer") == 6


def test_merge_scd2_no_altera_hechos_pasados(con):
    before = con.execute("SELECT order_id, customer_key FROM fact_order_items ORDER BY 1").fetchall()
    apply_customer_changes(con, CHANGES, EFFECTIVE)
    after = con.execute("SELECT order_id, customer_key FROM fact_order_items ORDER BY 1").fetchall()
    assert before == after

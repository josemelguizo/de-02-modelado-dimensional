-- 01 · STAGING (ya resuelto, úsalo como ejemplo)
--
-- La capa staging copia los CSV casi tal cual, con dos arreglos:
--   1. Nombres de columna claros y en un solo estilo.
--   2. Tipos correctos. Se lee todo como texto (all_varchar) y se convierte
--      a mano: si DuckDB adivinara, el código postal '01000' se volvería el
--      número 1000 y perdería el cero.
-- No se filtra ni se combina nada aquí: eso viene en las capas siguientes.

CREATE OR REPLACE TABLE stg_customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix          AS zip_prefix,
    customer_city                     AS city,
    customer_state                    AS state
FROM read_csv('{{raw_dir}}/olist_customers_dataset.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_orders AS
SELECT
    order_id,
    customer_id,
    order_status                                        AS status,
    CAST(order_purchase_timestamp       AS TIMESTAMP)   AS purchased_at,
    CAST(order_approved_at              AS TIMESTAMP)   AS approved_at,
    CAST(order_delivered_carrier_date   AS TIMESTAMP)   AS shipped_at,
    CAST(order_delivered_customer_date  AS TIMESTAMP)   AS delivered_at,
    CAST(order_estimated_delivery_date  AS TIMESTAMP)   AS estimated_delivery_at
FROM read_csv('{{raw_dir}}/olist_orders_dataset.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_order_items AS
SELECT
    order_id,
    CAST(order_item_id AS INTEGER)          AS order_item_id,
    product_id,
    seller_id,
    CAST(price         AS DECIMAL(10, 2))   AS price,
    CAST(freight_value AS DECIMAL(10, 2))   AS freight_value
FROM read_csv('{{raw_dir}}/olist_order_items_dataset.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_products AS
SELECT
    product_id,
    product_category_name                    AS category_pt,
    CAST(product_weight_g  AS INTEGER)       AS weight_g,
    CAST(product_length_cm AS INTEGER)       AS length_cm,
    CAST(product_height_cm AS INTEGER)       AS height_cm,
    CAST(product_width_cm  AS INTEGER)       AS width_cm
FROM read_csv('{{raw_dir}}/olist_products_dataset.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix   AS zip_prefix,
    seller_city              AS city,
    seller_state             AS state
FROM read_csv('{{raw_dir}}/olist_sellers_dataset.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_category_translation AS
SELECT
    product_category_name            AS category_pt,
    product_category_name_english    AS category_en
FROM read_csv('{{raw_dir}}/product_category_name_translation.csv', header = true, all_varchar = true);

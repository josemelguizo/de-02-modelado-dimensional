-- 03 · DIMENSIONES PRODUCTO Y VENDEDOR
--
-- dim_product, una fila por producto:
--   product_key  llave sustituta (entero 1, 2, 3...). Pista: ROW_NUMBER() OVER (ORDER BY ...)
--   product_id   llave natural (la de Olist)
--   category     categoría en inglés usando stg_category_translation.
--                Si no hay traducción usa la categoría en portugués,
--                y si tampoco hay categoría, 'unknown'. Pista: COALESCE.
--   weight_g
--   volume_cm3   largo × alto × ancho
--
-- dim_seller, una fila por vendedor:
--   seller_key, seller_id, zip_prefix, city, state
--
-- Pregunta para el README: ¿por qué usar una llave sustituta (product_key)
-- en lugar de la llave natural (product_id) en la tabla de hechos?

-- TODO: CREATE OR REPLACE TABLE dim_product AS ...

-- TODO: CREATE OR REPLACE TABLE dim_seller AS ...

# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup
# MAGIC Creates the three schemas, the landing volume and the small tables later steps expect.
# MAGIC Safe to run again.

# COMMAND ----------

CATALOG = "workspace"
for schema in ["bronze", "silver", "gold"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.bronze.landing")

# Filled in Phase 4 by the MusicBrainz linker; empty until then so dbt can reference it.
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.silver.artist_mbid (
        discogs_artist_id BIGINT, mbid STRING
    )
""")
display(spark.sql(f"SHOW SCHEMAS IN {CATALOG}"))

# Databricks notebook source
# MAGIC %md
# MAGIC # 10 · Bronze: one Discogs snapshot
# MAGIC Loads one monthly snapshot from the landing volume into bronze Delta tables.
# MAGIC Running the same snapshot again replaces it, so the result never doubles.

# COMMAND ----------

import json

from pyspark.sql import functions as F

dbutils.widgets.text("snapshot", "2026-10-01")
dbutils.widgets.text("kinds", "labels,artists,releases")
SNAPSHOT = dbutils.widgets.get("snapshot")
KINDS = [k.strip() for k in dbutils.widgets.get("kinds").split(",") if k.strip()]
LANDING = "/Volumes/workspace/bronze/landing/discogs"

# COMMAND ----------


def load_kind(kind: str) -> int:
    folder = f"{LANDING}/{kind}/snapshot={SNAPSHOT}"
    with open(f"{folder}/_run_summary.json") as fh:
        expected = json.load(fh)["rows_written"]

    df = (
        spark.read.parquet(folder)
        .withColumn("snapshot_date", F.lit(SNAPSHOT).cast("date"))
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .withColumn("_ingested_at", F.current_timestamp())
    )
    table = f"workspace.bronze.discogs_{kind}"
    writer = df.write.format("delta").option("mergeSchema", "true")
    if spark.catalog.tableExists(table):
        writer.mode("overwrite").option("replaceWhere", f"snapshot_date = '{SNAPSHOT}'").saveAsTable(table)
    else:
        writer.partitionBy("snapshot_date").saveAsTable(table)

    loaded = spark.table(table).where(F.col("snapshot_date") == SNAPSHOT).count()
    assert loaded == expected, f"{kind}: laptop wrote {expected:,} rows but bronze has {loaded:,}"
    return loaded


# COMMAND ----------

for kind in KINDS:
    print(f"{kind}: {load_kind(kind):,} rows for {SNAPSHOT}")

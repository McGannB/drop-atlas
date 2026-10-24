# Databricks notebook source
# MAGIC %md
# MAGIC # 11 · Silver: Discogs current state + artist history
# MAGIC * Releases, credits, styles and labels: rebuilt from the newest snapshot (current state).
# MAGIC * Artists: SCD2 history, so a name or group change keeps the old version with dates.

# COMMAND ----------

dbutils.widgets.text("snapshot", "2026-10-01")
SNAPSHOT = dbutils.widgets.get("snapshot")
B = "workspace.bronze"
S = "workspace.silver"

# COMMAND ----------

# MAGIC %md ## Current-state tables (one row per thing, newest snapshot)

# COMMAND ----------

newest = spark.sql(f"SELECT max(snapshot_date) FROM {B}.discogs_releases").first()[0]
if str(newest) != SNAPSHOT:
    print(f"Skipping current-state rebuild: {SNAPSHOT} is not the newest snapshot ({newest}).")
else:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {S}.release AS
        SELECT release_id, status, title, country, released_raw, released_date, released_precision,
               master_id, is_main_release, coalesce(master_id, -release_id) AS work_id,
               data_quality, track_count, genres, styles, snapshot_date
        FROM {B}.discogs_releases
        WHERE snapshot_date = '{SNAPSHOT}'
    """)
    spark.sql(f"""
        CREATE OR REPLACE TABLE {S}.release_credit AS
        SELECT release_id, 'main' AS credit_type, pos AS position, c.artist_id,
               c.name AS artist_name, coalesce(c.anv, c.name) AS credited_as, c.join_phrase, c.role
        FROM {B}.discogs_releases LATERAL VIEW posexplode(artists) x AS pos, c
        WHERE snapshot_date = '{SNAPSHOT}'
        UNION ALL
        SELECT release_id, 'extra', pos, c.artist_id, c.name, coalesce(c.anv, c.name),
               c.join_phrase, c.role
        FROM {B}.discogs_releases LATERAL VIEW posexplode(extra_artists) x AS pos, c
        WHERE snapshot_date = '{SNAPSHOT}'
    """)
    spark.sql(f"""
        CREATE OR REPLACE TABLE {S}.release_style AS
        SELECT DISTINCT release_id, style
        FROM {B}.discogs_releases LATERAL VIEW explode(styles) x AS style
        WHERE snapshot_date = '{SNAPSHOT}'
    """)
    spark.sql(f"""
        CREATE OR REPLACE TABLE {S}.release_label AS
        SELECT release_id, l.label_id, l.name AS label_name, l.catno
        FROM {B}.discogs_releases LATERAL VIEW explode(labels) x AS l
        WHERE snapshot_date = '{SNAPSHOT}'
    """)
    spark.sql(f"""
        CREATE OR REPLACE TABLE {S}.label AS
        SELECT label_id, name, parent_label_id, parent_label_name, sublabel_ids, profile,
               data_quality, snapshot_date
        FROM {B}.discogs_labels
        WHERE snapshot_date = '{SNAPSHOT}'
    """)
    for t in ["release", "release_credit", "release_style", "release_label", "label"]:
        print(t, f"{spark.table(f'{S}.{t}').count():,}")

# COMMAND ----------

# MAGIC %md ## Artist history (SCD2)

# COMMAND ----------

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {S}.artist_history (
        artist_id BIGINT, name STRING, name_norm STRING, realname STRING,
        name_variations ARRAY<STRING>, alias_ids ARRAY<BIGINT>, group_ids ARRAY<BIGINT>,
        member_ids ARRAY<BIGINT>, row_hash STRING,
        valid_from DATE, valid_to DATE, is_current BOOLEAN, is_deleted BOOLEAN
    ) CLUSTER BY (artist_id)
""")

latest = spark.sql(f"SELECT greatest(max(valid_from), max(valid_to)) FROM {S}.artist_history").first()[0]
if latest is not None and str(latest) > SNAPSHOT:
    raise ValueError(f"History already reaches {latest}; load snapshots oldest first, not {SNAPSHOT}.")

spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW staged_artist AS
    SELECT artist_id, name, name_norm, realname, name_variations, alias_ids, group_ids, member_ids,
           sha2(concat_ws('||',
                coalesce(name, ''), coalesce(realname, ''),
                array_join(array_sort(name_variations), '|'),
                array_join(array_sort(transform(group_ids, x -> cast(x AS STRING))), '|'),
                array_join(array_sort(transform(member_ids, x -> cast(x AS STRING))), '|')
           ), 256) AS row_hash,
           snapshot_date
    FROM {B}.discogs_artists
    WHERE snapshot_date = '{SNAPSHOT}'
""")

result = spark.sql(f"""
    MERGE INTO {S}.artist_history AS t
    USING (
        -- every staged artist, keyed so it can match its current row
        SELECT s.artist_id AS merge_key, s.* FROM staged_artist s
        UNION ALL
        -- changed artists a second time with no key, so they insert as the new version
        SELECT NULL AS merge_key, s.*
        FROM staged_artist s
        JOIN {S}.artist_history h
          ON h.artist_id = s.artist_id AND h.is_current AND h.row_hash <> s.row_hash
    ) AS src
    ON t.artist_id = src.merge_key AND t.is_current
    WHEN MATCHED AND t.row_hash <> src.row_hash THEN
        UPDATE SET is_current = false, valid_to = src.snapshot_date
    WHEN NOT MATCHED THEN
        INSERT (artist_id, name, name_norm, realname, name_variations, alias_ids, group_ids,
                member_ids, row_hash, valid_from, valid_to, is_current, is_deleted)
        VALUES (src.artist_id, src.name, src.name_norm, src.realname, src.name_variations,
                src.alias_ids, src.group_ids, src.member_ids, src.row_hash, src.snapshot_date,
                NULL, true, false)
    WHEN NOT MATCHED BY SOURCE AND t.is_current THEN
        UPDATE SET is_current = false, valid_to = DATE'{SNAPSHOT}', is_deleted = true
""")
display(result)

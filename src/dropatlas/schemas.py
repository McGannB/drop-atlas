"""Explicit Parquet schemas, so every file we land has the same shape."""

import pyarrow as pa

CREDIT = pa.struct(
    [
        ("artist_id", pa.int64()),
        ("name", pa.string()),
        ("anv", pa.string()),
        ("join_phrase", pa.string()),
        ("role", pa.string()),
    ]
)

RELEASE = pa.schema(
    [
        ("release_id", pa.int64()),
        ("status", pa.string()),
        ("title", pa.string()),
        ("country", pa.string()),
        ("released_raw", pa.string()),
        ("released_date", pa.date32()),
        ("released_precision", pa.string()),
        ("master_id", pa.int64()),
        ("is_main_release", pa.bool_()),
        ("data_quality", pa.string()),
        ("artists", pa.list_(CREDIT)),
        ("extra_artists", pa.list_(CREDIT)),
        (
            "labels",
            pa.list_(pa.struct([("label_id", pa.int64()), ("name", pa.string()), ("catno", pa.string())])),
        ),
        ("genres", pa.list_(pa.string())),
        ("styles", pa.list_(pa.string())),
        (
            "formats",
            pa.list_(
                pa.struct(
                    [
                        ("name", pa.string()),
                        ("qty", pa.string()),
                        ("descriptions", pa.list_(pa.string())),
                    ]
                )
            ),
        ),
        ("track_count", pa.int32()),
    ]
)

ARTIST = pa.schema(
    [
        ("artist_id", pa.int64()),
        ("name", pa.string()),
        ("name_norm", pa.string()),
        ("realname", pa.string()),
        ("profile", pa.string()),
        ("data_quality", pa.string()),
        ("urls", pa.list_(pa.string())),
        ("name_variations", pa.list_(pa.string())),
        ("alias_ids", pa.list_(pa.int64())),
        ("group_ids", pa.list_(pa.int64())),
        ("member_ids", pa.list_(pa.int64())),
    ]
)

LABEL = pa.schema(
    [
        ("label_id", pa.int64()),
        ("name", pa.string()),
        ("profile", pa.string()),
        ("data_quality", pa.string()),
        ("parent_label_id", pa.int64()),
        ("parent_label_name", pa.string()),
        ("sublabel_ids", pa.list_(pa.int64())),
        ("urls", pa.list_(pa.string())),
    ]
)

LISTEN = pa.schema(
    [
        ("listened_at", pa.timestamp("us", tz="UTC")),
        ("inserted_at", pa.timestamp("us", tz="UTC")),
        ("user_key", pa.string()),
        ("recording_msid", pa.string()),
        ("artist_name", pa.string()),
        ("track_name", pa.string()),
        ("release_name", pa.string()),
        ("artist_norm", pa.string()),
        ("artist_parts_norm", pa.list_(pa.string())),
        ("artist_mbids", pa.list_(pa.string())),
        ("mbid_source", pa.string()),
        ("recording_mbid", pa.string()),
    ]
)

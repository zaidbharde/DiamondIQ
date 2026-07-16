import csv
import io
import json
import math
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    price REAL NOT NULL,
    confidence REAL,
    model_used TEXT NOT NULL,
    prediction_time_ms REAL NOT NULL,
    explanation TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    contributions_json TEXT NOT NULL,
    quality_score REAL DEFAULT NULL,
    recommendation_label TEXT DEFAULT NULL,
    recommendation_badge TEXT DEFAULT NULL,
    source TEXT DEFAULT 'manual',
    xai_json TEXT DEFAULT NULL
);
"""
COLUMNS_TO_ADD = [
    "quality_score REAL DEFAULT NULL",
    "recommendation_label TEXT DEFAULT NULL",
    "recommendation_badge TEXT DEFAULT NULL",
    "source TEXT DEFAULT 'manual'",
    "xai_json TEXT DEFAULT NULL",
]


def get_connection(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path):
    with get_connection(database_path) as conn:
        conn.execute(SCHEMA)
        # Safely add new columns if they don't exist
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}
        for col_def in COLUMNS_TO_ADD:
            col_name = col_def.split()[0]
            if col_name not in existing:
                conn.execute(f"ALTER TABLE predictions ADD COLUMN {col_def}")
        conn.commit()


def insert_prediction(database_path, payload):
    with get_connection(database_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO predictions (
                created_at, price, confidence, model_used, prediction_time_ms,
                explanation, inputs_json, contributions_json,
                quality_score, recommendation_label, recommendation_badge,
                source, xai_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["created_at"],
                payload["price"],
                payload.get("confidence"),
                payload["model_used"],
                payload["prediction_time_ms"],
                payload["explanation"],
                json.dumps(payload["inputs"]),
                json.dumps(payload["contributions"]),
                payload.get("quality_score"),
                payload.get("recommendation_label"),
                payload.get("recommendation_badge"),
                payload.get("source", "manual"),
                json.dumps(payload.get("xai")) if payload.get("xai") else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid


PAGE_SIZE = 10


def row_to_dict(row):
    item = dict(row)
    item["inputs"] = json.loads(item.pop("inputs_json"))
    item["contributions"] = json.loads(item.pop("contributions_json"))
    if item.get("xai_json"):
        item["xai"] = json.loads(item.pop("xai_json"))
    else:
        item.pop("xai_json", None)
    return item


def list_predictions(database_path, search="", sort="newest", page=1, per_page=PAGE_SIZE):
    query = "SELECT * FROM predictions"
    count_query = "SELECT COUNT(*) FROM predictions"
    params = []
    where_clause = ""
    if search:
        where_clause = " WHERE inputs_json LIKE ? OR model_used LIKE ? OR explanation LIKE ?"
        term = f"%{search}%"
        params.extend([term, term, term])

    order = " ORDER BY created_at DESC"
    if sort == "price_high":
        order = " ORDER BY price DESC"
    elif sort == "price_low":
        order = " ORDER BY price ASC"
    elif sort == "quality_high":
        order = " ORDER BY quality_score DESC NULLS LAST"
    elif sort == "quality_low":
        order = " ORDER BY quality_score ASC NULLS LAST"

    offset = (page - 1) * per_page

    with get_connection(database_path) as conn:
        total = conn.execute(count_query + where_clause, params).fetchone()[0]
        rows = conn.execute(
            query + where_clause + order + " LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()

    return {
        "items": [row_to_dict(row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, math.ceil(total / per_page)),
    }


def get_prediction_by_id(database_path, prediction_id):
    with get_connection(database_path) as conn:
        row = conn.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        return row_to_dict(row) if row else None


def delete_prediction(database_path, prediction_id):
    with get_connection(database_path) as conn:
        cursor = conn.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_metrics(database_path):
    with get_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(AVG(price), 0) AS average_price,
                COALESCE(MAX(price), 0) AS highest_price,
                COALESCE(MIN(price), 0) AS lowest_price,
                COALESCE(AVG(quality_score), 0) AS average_quality
            FROM predictions
            """
        ).fetchone()
        recent = conn.execute(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        # Distribution data
        price_dist = conn.execute(
            "SELECT price FROM predictions ORDER BY price"
        ).fetchall()
        quality_dist = conn.execute(
            "SELECT quality_score FROM predictions WHERE quality_score IS NOT NULL ORDER BY quality_score"
        ).fetchall()
        timeline = conn.execute(
            "SELECT created_at, price FROM predictions ORDER BY created_at"
        ).fetchall()
        rec_breakdown = conn.execute(
            "SELECT COALESCE(recommendation_label, 'Unclassified') as recommendation_label, COUNT(*) as cnt FROM predictions GROUP BY recommendation_label ORDER BY cnt DESC"
        ).fetchall()

    def bucketize(values, key, bins):
        counts = {b["label"]: 0 for b in bins}
        for v in values:
            val = v[key]
            if val is None:
                continue
            for b in reversed(bins):
                if val >= b["min"] and val < b["max"]:
                    counts[b["label"]] += 1
                    break
        return [{"label": k, "count": v} for k, v in counts.items()]

    price_bins = [
        {"label": "Under ₹50K", "min": 0, "max": 50000},
        {"label": "₹50K–₹1L", "min": 50000, "max": 100000},
        {"label": "₹1L–₹5L", "min": 100000, "max": 500000},
        {"label": "₹5L–₹10L", "min": 500000, "max": 1000000},
        {"label": "₹10L+", "min": 1000000, "max": float("inf")},
    ]
    quality_bins = [
        {"label": "0–20", "min": 0, "max": 20},
        {"label": "20–40", "min": 20, "max": 40},
        {"label": "40–60", "min": 40, "max": 60},
        {"label": "60–80", "min": 60, "max": 80},
        {"label": "80–100", "min": 80, "max": 100},
    ]

    return {
        "total": row["total"],
        "average_price": row["average_price"],
        "highest_price": row["highest_price"],
        "lowest_price": row["lowest_price"],
        "average_quality": row["average_quality"],
        "recent": [row_to_dict(item) for item in recent],
        "distributions": {
            "price_distribution": bucketize(price_dist, "price", price_bins),
            "quality_distribution": bucketize(quality_dist, "quality_score", quality_bins),
            "timeline": [{"date": r["created_at"][:10], "price": r["price"]} for r in timeline],
            "recommendation_breakdown": [{"label": r["recommendation_label"], "count": r["cnt"]} for r in rec_breakdown],
        },
    }


def export_predictions_csv(predictions):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id", "created_at", "price", "confidence", "model_used",
            "prediction_time_ms", "quality_score", "recommendation", "source",
            "carat", "depth", "table", "x", "y", "z",
            "cut", "color", "clarity", "explanation",
        ]
    )
    for item in predictions:
        inputs = item["inputs"]
        writer.writerow(
            [
                item["id"], item["created_at"], item["price"],
                item.get("confidence"), item["model_used"],
                item["prediction_time_ms"],
                item.get("quality_score"), item.get("recommendation_label"),
                item.get("source"),
                inputs["carat"], inputs["depth"], inputs["table"],
                inputs["x"], inputs["y"], inputs["z"],
                inputs["cut"], inputs["color"], inputs["clarity"],
                item["explanation"],
            ]
        )
    return output.getvalue()


def export_predictions_json(predictions):
    return json.dumps(
        [
            {
                "id": item["id"],
                "created_at": item["created_at"],
                "price": item["price"],
                "confidence": item.get("confidence"),
                "model_used": item["model_used"],
                "quality_score": item.get("quality_score"),
                "recommendation": item.get("recommendation_label"),
                "source": item.get("source"),
                "inputs": item["inputs"],
                "explanation": item["explanation"],
            }
            for item in predictions
        ],
        indent=2,
    )

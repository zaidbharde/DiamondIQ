import secrets
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from .certificate_parser import detect_certificate_type, parse_certificate
from .database import (
    delete_prediction,
    export_predictions_csv,
    export_predictions_json,
    get_metrics,
    get_prediction_by_id,
    insert_prediction,
    list_predictions,
)
from .image_analysis import (
    allowed_image,
    analyze_image,
    validate_image_size,
)
from .ml_service import PredictionService
from .ocr_service import allowed_file, extract_text_from_image, extract_text_from_pdf
from .report_generator import generate_report
from .validation import CLARITIES, COLORS, CUTS, sanitize_payload
from .sell_signal import get_sell_signal
from .xai import analyze_features


main_bp = Blueprint("main", __name__)
rate_buckets = defaultdict(deque)


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_is_valid():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    return expected and supplied and secrets.compare_digest(expected, supplied)


def rate_limited():
    limit = current_app.config["RATE_LIMIT_PER_MINUTE"]
    key = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
    bucket = rate_buckets[key]
    now = time.time()
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def service():
    return PredictionService(
        current_app.config["MODEL_PATH"], current_app.config["PREPROCESSOR_PATH"]
    )


@main_bp.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@main_bp.route("/", methods=["GET"])
def index():
    database_path = current_app.config["DATABASE_PATH"]
    return render_template(
        "index.html",
        csrf_token=get_csrf_token(),
        cuts=CUTS,
        colors=COLORS,
        clarities=CLARITIES,
        metrics=get_metrics(database_path),
        history=list_predictions(database_path, page=1, per_page=10)["items"],
    )


@main_bp.route("/upload-certificate", methods=["POST"])
def upload_certificate():
    if rate_limited():
        return jsonify({"ok": False, "error": "Too many requests. Try again in a minute."}), 429

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"ok": False, "error": "Empty file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"ok": False, "error": "Unsupported file type. Upload PDF, JPG, JPEG, or PNG."}), 400

    temp_dir = Path(current_app.config["UPLOAD_FOLDER"])
    temp_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower()
    temp_path = temp_dir / f"{uuid.uuid4().hex}{ext}"

    try:
        file.save(str(temp_path))
        raw_bytes = temp_path.read_bytes()

        if ext == ".pdf":
            lines = extract_text_from_pdf(raw_bytes)
        else:
            lines = extract_text_from_image(raw_bytes)

        if not lines:
            return jsonify({"ok": False, "error": "Could not read any text from the file. Try a clearer image."}), 400

        cert_type = detect_certificate_type(lines)
        parsed = parse_certificate(lines, cert_type)
        fields = parsed["fields"]

        response = {
            "ok": True,
            "certificate_type": cert_type,
            "fields": {k: v for k, v in fields.items()},
            "total_lines": len(lines),
        }
        return jsonify(response)

    except Exception as exc:
        current_app.logger.exception("Certificate upload failed")
        return jsonify({"ok": False, "error": f"Processing failed: {str(exc)}"}), 500
    finally:
        if temp_path.exists():
            temp_path.unlink()


@main_bp.route("/analyze-image", methods=["POST"])
def analyze_diamond_image():
    if rate_limited():
        return jsonify({"ok": False, "error": "Too many requests. Try again in a minute."}), 429

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"ok": False, "error": "Empty file."}), 400

    if not allowed_image(file.filename):
        return jsonify({
            "ok": False,
            "error": "Unsupported file type. Upload PNG, JPG, JPEG, or WEBP."
        }), 400

    raw_bytes = file.read()

    if not validate_image_size(raw_bytes):
        return jsonify({
            "ok": False,
            "error": f"File too large. Maximum size is {current_app.config['MAX_IMAGE_SIZE_MB']} MB."
        }), 400

    try:
        result = analyze_image(raw_bytes, file.filename)

        if result.get("no_api_key"):
            return jsonify({
                "ok": True,
                "no_api_key": True,
                "message": result["message"],
                "suggestions": {},
            })

        if result.get("fallback"):
            return jsonify({
                "ok": True,
                "fallback": True,
                "message": result.get("error", "AI analysis encountered an issue."),
                "suggestions": {},
            })

        # Build clean suggestions dict
        suggestions = {}
        field_map = {
            "shape": "shape",
            "estimated_cut": "cut",
            "estimated_color": "color",
            "estimated_polish": "polish",
            "estimated_symmetry": "symmetry",
        }
        conf_map = {
            "shape": "shape_confidence",
            "cut": "cut_confidence",
            "color": "color_confidence",
            "polish": "polish_confidence",
            "symmetry": "symmetry_confidence",
        }

        for result_key, field_name in field_map.items():
            value = result.get(result_key)
            conf_key = conf_map[field_name]
            confidence = result.get(conf_key)
            if value and confidence is not None:
                suggestions[field_name] = {
                    "value": value,
                    "confidence": round(float(confidence), 1),
                }

        return jsonify({
            "ok": True,
            "provider": result.get("provider"),
            "suggestions": suggestions,
        })

    except Exception as exc:
        current_app.logger.exception("Image analysis failed")
        return jsonify({"ok": False, "error": f"Analysis failed: {str(exc)}"}), 500


@main_bp.route("/predict", methods=["POST"])
def predict():
    if rate_limited():
        return jsonify({"ok": False, "errors": {"global": "Too many requests. Try again in a minute."}}), 429

    if not csrf_is_valid():
        return jsonify({"ok": False, "errors": {"global": "Invalid security token. Refresh the page."}}), 400

    payload = request.get_json(silent=True) or request.form.to_dict()
    inputs, errors = sanitize_payload(payload)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    try:
        result = service().predict(inputs)
        report = generate_report(result, inputs, payload)
        xai = analyze_features(inputs, result["price"])

        # Attach report data to result
        result["quality_score"] = report["quality_score"]
        result["quality_explanation"] = report["quality_explanation"]
        result["recommendation"] = report["recommendation"]
        result["xai"] = xai
        result["report"] = report
        result["sell_signal"] = get_sell_signal(
            inputs,
            result["price"],
            report["quality_score"],
            current_app.config["DATABASE_PATH"],
        )

        # Enrich payload for DB storage
        result["recommendation_label"] = report["recommendation"]["label"]
        result["recommendation_badge"] = report["recommendation"]["badge"]
        result["source"] = report.get("source", "manual")

        result["id"] = insert_prediction(current_app.config["DATABASE_PATH"], result)
    except Exception as exc:
        current_app.logger.exception("Prediction failed")
        return jsonify({"ok": False, "errors": {"global": str(exc)}}), 500

    return jsonify({"ok": True, "prediction": result, "metrics": get_metrics(current_app.config["DATABASE_PATH"])})


@main_bp.route("/history", methods=["GET"])
def history():
    search = request.args.get("search", "")
    sort = request.args.get("sort", "newest")
    page = int(request.args.get("page", 1))
    result = list_predictions(
        current_app.config["DATABASE_PATH"],
        search=search,
        sort=sort,
        page=page,
    )
    result["ok"] = True
    result["metrics"] = get_metrics(current_app.config["DATABASE_PATH"])
    return jsonify(result)


@main_bp.route("/history/export/csv", methods=["GET"])
def export_history_csv():
    fmt = request.args.get("format", "")
    search = request.args.get("search", "")
    result = list_predictions(current_app.config["DATABASE_PATH"], search=search, page=1, per_page=100000)
    csv_data = export_predictions_csv(result["items"])
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=diamond_predictions.csv"},
    )


@main_bp.route("/history/export/json", methods=["GET"])
def export_history_json():
    search = request.args.get("search", "")
    result = list_predictions(current_app.config["DATABASE_PATH"], search=search, page=1, per_page=100000)
    json_data = export_predictions_json(result["items"])
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=diamond_predictions.json"},
    )


@main_bp.route("/history/<int:prediction_id>", methods=["GET"])
def get_history_item(prediction_id):
    item = get_prediction_by_id(current_app.config["DATABASE_PATH"], prediction_id)
    if not item:
        abort(404)
    return jsonify({"ok": True, "prediction": item})


@main_bp.route("/history/<int:prediction_id>", methods=["DELETE"])
def delete_history(prediction_id):
    if rate_limited():
        return jsonify({"ok": False, "errors": {"global": "Too many requests. Try again in a minute."}}), 429
    if not csrf_is_valid():
        return jsonify({"ok": False, "errors": {"global": "Invalid security token. Refresh the page."}}), 400

    deleted = delete_prediction(current_app.config["DATABASE_PATH"], prediction_id)
    if not deleted:
        abort(404)
    return jsonify({"ok": True, "metrics": get_metrics(current_app.config["DATABASE_PATH"])})

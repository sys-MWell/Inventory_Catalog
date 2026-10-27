import io
import json
import os
import secrets
import sqlite3
import zipfile
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("INVENTORY_DATABASE", BASE_DIR / "catalog.sqlite"))
UPLOAD_FOLDER = Path(os.environ.get("INVENTORY_UPLOADS", BASE_DIR / "uploads"))
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("INVENTORY_SECRET_KEY", secrets.token_hex(32)),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE,
    )
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    def connect_db():
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_db():
        with connect_db() as db:
            db.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
            columns = {row[1] for row in db.execute("PRAGMA table_info(items)").fetchall()}
            if "brand_id" not in columns:
                db.execute("ALTER TABLE items ADD COLUMN brand_id INTEGER REFERENCES brands(id) ON DELETE SET NULL")
            if "box_condition" not in columns:
                db.execute("ALTER TABLE items ADD COLUMN box_condition TEXT")
            if "quantity" not in columns:
                db.execute("ALTER TABLE items ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
            db.execute("CREATE INDEX IF NOT EXISTS idx_items_brand ON items(brand_id)")
            ensure_accounts(db)

    def ensure_accounts(db):
        accounts = (("admin", "admin"), ("viewer", "viewer"))
        generated = []
        for username, role in accounts:
            if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone() is None:
                password = secrets.token_urlsafe(12)
                db.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)", (username, generate_password_hash(password), role, now()))
                generated.append((username, password))
        if generated:
            print("\nInventory account passwords (record these securely; they are not stored in plaintext):")
            for username, password in generated:
                print(f"  {username}: {password}")
            print()

    def form_configuration(item_type_id=None):
        with connect_db() as db:
            types = db.execute("SELECT * FROM item_types ORDER BY name").fetchall()
            brands = db.execute("SELECT * FROM brands ORDER BY name").fetchall()
            fields = []
            if item_type_id:
                rows = db.execute("SELECT * FROM item_fields WHERE item_type_id = ? ORDER BY sort_order, label", (item_type_id,)).fetchall()
                for row in rows:
                    field = dict(row)
                    field["options"] = [option["value"] for option in db.execute("SELECT value FROM item_field_options WHERE field_id = ? ORDER BY sort_order, value", (row["id"],)).fetchall()]
                    fields.append(field)
        return types, brands, fields

    def get_item(item_id):
        with connect_db() as db:
            item = db.execute("""
                SELECT items.*, item_types.name AS type_name, brands.name AS brand_name
                FROM items JOIN item_types ON item_types.id = items.item_type_id
                LEFT JOIN brands ON brands.id = items.brand_id
                WHERE items.id = ?
            """, (item_id,)).fetchone()
            if item is None:
                abort(404)
            images = db.execute("SELECT * FROM images WHERE item_id = ? ORDER BY sort_order, id", (item_id,)).fetchall()
        return item, images

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))
            if session.get("role") != "admin":
                flash("Administrator access is required for that action.", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped

    @app.context_processor
    def inject_config():
        return {
            "auth_enabled": True,
            "current_username": session.get("username"),
            "current_role": session.get("role"),
        }

    @app.before_request
    def ensure_database():
        if not DATABASE.exists():
            init_db()

    @app.get("/health")
    def health():
        try:
            with connect_db() as db:
                db.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            app.logger.exception("Health check database query failed")
            return jsonify(status="error", database="unavailable"), 503
        return jsonify(status="ok", database="ok")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            with connect_db() as db:
                user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(request.args.get("next") or url_for("index"))
            flash("Incorrect password.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/")
    @login_required
    def index():
        query = request.args.get("q", "").strip()
        filters = {key: request.args.get(key, "").strip() for key in ("item_type_id", "brand_id", "category", "location", "tag")}
        clauses, params = [], []
        if query:
            clauses.append("(items.name LIKE ? OR items.description LIKE ? OR items.tags LIKE ? OR items.notes LIKE ? OR brands.name LIKE ?)")
            params.extend([f"%{query}%"] * 5)
        if filters["item_type_id"]:
            clauses.append("items.item_type_id = ?")
            params.append(filters["item_type_id"])
        if filters["brand_id"]:
            clauses.append("items.brand_id = ?")
            params.append(filters["brand_id"])
        for column in ("category", "location"):
            if filters[column]:
                clauses.append(f"items.{column} LIKE ?")
                params.append(f"%{filters[column]}%")
        if filters["tag"]:
            clauses.append("items.tags LIKE ?")
            params.append(f"%{filters['tag']}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with connect_db() as db:
            items = db.execute(f"""
                SELECT items.*, item_types.name AS type_name, brands.name AS brand_name,
                    (SELECT filename FROM images WHERE item_id = items.id ORDER BY sort_order, id LIMIT 1) AS thumbnail
                FROM items JOIN item_types ON item_types.id = items.item_type_id
                LEFT JOIN brands ON brands.id = items.brand_id
                {where} ORDER BY items.updated_at DESC
            """, params).fetchall()
            types = db.execute("SELECT * FROM item_types ORDER BY name").fetchall()
            brands = db.execute("SELECT * FROM brands ORDER BY name").fetchall()
        return render_template("index.html", items=items, types=types, brands=brands, filters=filters, query=query)

    def form_data():
        details = {}
        for key, value in request.form.items():
            if key.startswith("detail_") and value.strip():
                details[key[7:]] = value.strip()
        return {
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "item_type_id": request.form.get("item_type_id", ""),
            "brand_id": request.form.get("brand_id", "") or None,
            "category": request.form.get("category", "").strip(),
            "location": request.form.get("location", "").strip(),
            "condition": request.form.get("condition", "").strip(),
            "box_condition": request.form.get("box_condition", "").strip(),
            "quantity": request.form.get("quantity", "1").strip(),
            "purchase_date": request.form.get("purchase_date", "").strip(),
            "purchase_price": request.form.get("purchase_price", "").strip() or None,
            "estimated_value": request.form.get("estimated_value", "").strip() or None,
            "tags": request.form.get("tags", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "details": details,
        }

    def validate(data):
        errors = []
        if not data["name"]:
            errors.append("Name is required.")
        if not data["item_type_id"]:
            errors.append("Item type is required.")
        try:
            data["quantity"] = int(data["quantity"])
            if data["quantity"] < 1:
                errors.append("Quantity must be at least 1.")
        except (TypeError, ValueError):
            errors.append("Quantity must be a whole number.")
        for field in ("purchase_price", "estimated_value"):
            if data[field] is not None:
                try:
                    data[field] = float(data[field])
                except ValueError:
                    errors.append(f"{field.replace('_', ' ').title()} must be a number.")
        return errors

    @app.route("/items/new", methods=["GET", "POST"])
    @admin_required
    def create_item():
        with connect_db() as db:
            types = db.execute("SELECT * FROM item_types ORDER BY name").fetchall()
        data = form_data() if request.method == "POST" else {"details": {}}
        if request.method == "POST":
            errors = validate(data)
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                timestamp = now()
                with connect_db() as db:
                    cursor = db.execute("""
                        INSERT INTO items (name, description, item_type_id, brand_id, category, location, condition,
                        box_condition, quantity, purchase_date, purchase_price, estimated_value, tags, notes, details, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (data["name"], data["description"], data["item_type_id"], data["brand_id"], data["category"], data["location"], data["condition"], data["box_condition"], data["quantity"], data["purchase_date"], data["purchase_price"], data["estimated_value"], data["tags"], data["notes"], json.dumps(data["details"]), timestamp, timestamp))
                    item_id = cursor.lastrowid
                save_uploads(item_id)
                flash("Item added.", "success")
                return redirect(url_for("item_detail", item_id=item_id))
        selected_type = data.get("item_type_id")
        types, brands, fields = form_configuration(selected_type)
        return render_template("item_form.html", item=None, types=types, brands=brands, fields=fields, data=data, title="Add item")

    @app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_item(item_id):
        item, images = get_item(item_id)
        data = form_data() if request.method == "POST" else dict(item)
        if request.method != "POST":
            data["details"] = json.loads(item["details"] or "{}")
        if request.method == "POST":
            errors = validate(data)
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                with connect_db() as db:
                    db.execute("""
                        UPDATE items SET name=?, description=?, item_type_id=?, brand_id=?, category=?, location=?, condition=?,
                        box_condition=?, quantity=?, purchase_date=?, purchase_price=?, estimated_value=?, tags=?, notes=?, details=?, updated_at=? WHERE id=?
                    """, (data["name"], data["description"], data["item_type_id"], data["brand_id"], data["category"], data["location"], data["condition"], data["box_condition"], data["quantity"], data["purchase_date"], data["purchase_price"], data["estimated_value"], data["tags"], data["notes"], json.dumps(data["details"]), now(), item_id))
                save_uploads(item_id)
                flash("Item updated.", "success")
                return redirect(url_for("item_detail", item_id=item_id))
        types, brands, fields = form_configuration(data.get("item_type_id"))
        return render_template("item_form.html", item=item, types=types, brands=brands, fields=fields, data=data, title="Edit item")

    @app.route("/items/<int:item_id>")
    @login_required
    def item_detail(item_id):
        item, images = get_item(item_id)
        return render_template("item_detail.html", item=item, images=images, details=json.loads(item["details"] or "{}"))

    @app.post("/items/<int:item_id>/delete")
    @admin_required
    def delete_item(item_id):
        item, _ = get_item(item_id)
        with connect_db() as db:
            db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        item_folder = UPLOAD_FOLDER / f"item-{item_id}"
        if item_folder.exists():
            for file_path in item_folder.iterdir():
                file_path.unlink()
            item_folder.rmdir()
        flash(f"{item['name']} deleted.", "success")
        return redirect(url_for("index"))

    def save_uploads(item_id):
        files = request.files.getlist("photos")
        folder = UPLOAD_FOLDER / f"item-{item_id}"
        if not files or not any(file.filename for file in files):
            return
        folder.mkdir(parents=True, exist_ok=True)
        with connect_db() as db:
            next_order = db.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM images WHERE item_id = ?", (item_id,)).fetchone()[0]
            for file in files:
                if not file.filename:
                    continue
                original = secure_filename(file.filename)
                extension = Path(original).suffix.lower().lstrip(".")
                if extension not in ALLOWED_EXTENSIONS or not (file.mimetype or "").startswith("image/"):
                    flash(f"Skipped unsupported image: {original}", "error")
                    continue
                generated = f"{secrets.token_hex(12)}.{extension}"
                file.save(folder / generated)
                db.execute("INSERT INTO images (item_id, filename, original_filename, sort_order, uploaded_at) VALUES (?, ?, ?, ?, ?)", (item_id, generated, original, next_order, now()))
                next_order += 1

    @app.post("/images/<int:image_id>/delete")
    @admin_required
    def delete_image(image_id):
        with connect_db() as db:
            image = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
            if image is None:
                abort(404)
            db.execute("DELETE FROM images WHERE id = ?", (image_id,))
        path = UPLOAD_FOLDER / f"item-{image['item_id']}" / image["filename"]
        if path.exists():
            path.unlink()
        flash("Photo deleted.", "success")
        return redirect(url_for("item_detail", item_id=image["item_id"]))

    @app.get("/uploads/<int:item_id>/<path:filename>")
    @login_required
    def uploaded_file(item_id, filename):
        return send_from_directory(UPLOAD_FOLDER / f"item-{item_id}", filename)

    @app.route("/types", methods=["GET", "POST"])
    @admin_required
    def types():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if name:
                try:
                    with connect_db() as db:
                        db.execute("INSERT INTO item_types (name) VALUES (?)", (name,))
                    flash("Item type added.", "success")
                except sqlite3.IntegrityError:
                    flash("That item type already exists.", "error")
            return redirect(url_for("types"))
        with connect_db() as db:
            item_types = db.execute("SELECT item_types.*, COUNT(items.id) AS item_count FROM item_types LEFT JOIN items ON items.item_type_id = item_types.id GROUP BY item_types.id ORDER BY item_types.name").fetchall()
        return render_template("types.html", types=item_types)

    @app.post("/types/<int:type_id>/edit")
    @admin_required
    def edit_type(type_id):
        name = request.form.get("name", "").strip()
        if not name:
            flash("Item type name cannot be blank.", "error")
        else:
            try:
                with connect_db() as db:
                    cursor = db.execute("UPDATE item_types SET name = ? WHERE id = ?", (name, type_id))
                    if cursor.rowcount == 0:
                        abort(404)
                flash("Item type updated.", "success")
            except sqlite3.IntegrityError:
                flash("That item type already exists.", "error")
        return redirect(url_for("types"))

    @app.post("/types/<int:type_id>/delete")
    @admin_required
    def delete_type(type_id):
        with connect_db() as db:
            item_type = db.execute("SELECT name FROM item_types WHERE id = ?", (type_id,)).fetchone()
            if item_type is None:
                abort(404)
            item_count = db.execute("SELECT COUNT(*) FROM items WHERE item_type_id = ?", (type_id,)).fetchone()[0]
            if item_count:
                flash(f"Cannot delete {item_type['name']}; {item_count} item(s) still use this type.", "error")
            else:
                db.execute("DELETE FROM item_types WHERE id = ?", (type_id,))
                flash("Item type deleted.", "success")
        return redirect(url_for("types"))

    @app.route("/brands", methods=["GET", "POST"])
    @admin_required
    def brands():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if name:
                try:
                    with connect_db() as db:
                        db.execute("INSERT INTO brands (name) VALUES (?)", (name,))
                    flash("Brand added.", "success")
                except sqlite3.IntegrityError:
                    flash("That brand already exists.", "error")
            return redirect(url_for("brands"))
        with connect_db() as db:
            brand_rows = db.execute("""
                SELECT brands.*, COUNT(items.id) AS item_count
                FROM brands LEFT JOIN items ON items.brand_id = brands.id
                GROUP BY brands.id ORDER BY brands.name
            """).fetchall()
        return render_template("brands.html", brands=brand_rows)

    @app.post("/brands/<int:brand_id>/edit")
    @admin_required
    def edit_brand(brand_id):
        name = request.form.get("name", "").strip()
        if not name:
            flash("Brand name cannot be blank.", "error")
        else:
            try:
                with connect_db() as db:
                    cursor = db.execute("UPDATE brands SET name = ? WHERE id = ?", (name, brand_id))
                    if cursor.rowcount == 0:
                        abort(404)
                flash("Brand updated.", "success")
            except sqlite3.IntegrityError:
                flash("That brand already exists.", "error")
        return redirect(url_for("brands"))

    @app.post("/brands/<int:brand_id>/delete")
    @admin_required
    def delete_brand(brand_id):
        with connect_db() as db:
            brand = db.execute("SELECT name FROM brands WHERE id = ?", (brand_id,)).fetchone()
            if brand is None:
                abort(404)
            db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
        flash(f"{brand['name']} deleted. Existing items no longer have a brand selected.", "success")
        return redirect(url_for("brands"))

    @app.get("/export/<format>")
    @admin_required
    def export_data(format):
        with connect_db() as db:
            items = [dict(row) for row in db.execute("""
                SELECT items.*, item_types.name AS type_name, brands.name AS brand_name
                FROM items JOIN item_types ON item_types.id = items.item_type_id
                LEFT JOIN brands ON brands.id = items.brand_id ORDER BY items.id
            """).fetchall()]
            for item in items:
                item["details"] = json.loads(item["details"] or "{}")
                item["images"] = [dict(row) for row in db.execute("SELECT filename, original_filename, caption, sort_order, uploaded_at FROM images WHERE item_id = ? ORDER BY sort_order", (item["id"],)).fetchall()]
        if format == "json":
            response = app.response_class(json.dumps(items, indent=2), mimetype="application/json")
            response.headers["Content-Disposition"] = "attachment; filename=inventory-export.json"
            return response
        if format == "csv":
            import csv
            output = io.StringIO()
            fields = ["id", "name", "type_name", "brand_name", "category", "location", "condition", "box_condition", "quantity", "purchase_date", "purchase_price", "estimated_value", "tags", "notes", "created_at", "updated_at"]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader(); writer.writerows(items)
            response = app.response_class(output.getvalue(), mimetype="text/csv")
            response.headers["Content-Disposition"] = "attachment; filename=inventory-export.csv"
            return response
        abort(404)

    @app.get("/backup.zip")
    @admin_required
    def backup():
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(DATABASE, "catalog.sqlite")
            if UPLOAD_FOLDER.exists():
                for path in UPLOAD_FOLDER.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(BASE_DIR))
        memory.seek(0)
        return send_file(memory, as_attachment=True, download_name="inventory-backup.zip", mimetype="application/zip")

    with app.app_context():
        init_db()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("INVENTORY_HOST", "0.0.0.0"), port=int(os.environ.get("INVENTORY_PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")

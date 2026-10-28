# Inventory Catalog

A local-first Flask application for cataloging household items, photos, quantities, packaging status, brands, types, and configurable details.

## Project layout

- `Inventory_Catalog/` - Python application, templates, static assets, schema, and deployment documentation.
- `Inventory_Catalog.slnx` - Visual Studio solution.
- `Inventory_Catalog/Inventory_Catalog.pyproj` - Python project file.

## Quick start

From the application directory:

```bash
cd Inventory_Catalog
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000` in a browser. The application creates its local SQLite database on first start from `schema.sql`; runtime data is intentionally excluded from Git.

## Example seed data

The schema includes generic starter types and brands. To create a clean database manually:

```bash
sqlite3 catalog.sqlite < schema.sql
```

Example records can then be added with ordinary SQL, for example:

```sql
INSERT INTO item_types (name) VALUES ('Household item');
INSERT INTO brands (name) VALUES ('Example brand');
```

The web application normally creates and migrates the database automatically, so manual SQL setup is optional.

## Configuration

Use environment variables for deployment-specific values:

- `INVENTORY_SECRET_KEY` - stable Flask session secret.
- `INVENTORY_DATABASE` - path to the local SQLite database.
- `INVENTORY_UPLOADS` - path to uploaded images.
- `INVENTORY_HOST` and `INVENTORY_PORT` - bind address and port when running `app.py`.

Do not commit runtime databases, uploaded files, virtual environments, credentials, or machine-specific paths.

## Raspberry Pi deployment

See [`Inventory_Catalog/README.md`](Inventory_Catalog/README.md) for systemd, LAN access, health checks, and optional HTTPS reverse-proxy instructions. Use a generic deployment location and service account for your environment.

## Development workflow

1. Make application or schema changes.
2. Test locally.
3. Commit source, schema, and documentation changes.
4. Pull the code on the deployment host.
5. Restart the service so application migrations run against that host's local database.

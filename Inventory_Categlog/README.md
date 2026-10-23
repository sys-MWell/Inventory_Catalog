# Home Inventory Catalog

A lightweight, local-first Flask application for cataloging household items. The SQLite database and original photos stay on the Raspberry Pi filesystem.

## Run locally

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

On Windows, `setup.ps1` automates creation of the virtual environment and installation of `requirements.txt`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

Then configure Visual Studio to use `.venv\Scripts\python.exe` from this project and start `run.py`.

Open `http://localhost:5000` on the Pi. From another device on the home network, use the Pi's address, for example `http://192.168.1.25:5000`.

The app creates `catalog.sqlite` and `uploads/` automatically and seeds the initial item types on first start. Use **Item types** to add custom types.

## Database-backed catalog configuration

Item types and brands are stored in SQLite, not in the page templates. The initial catalog includes brands such as Disney, Universal, LEGO, Funko, Hasbro, Mattel, Nintendo, Sony, Microsoft, Apple, and Samsung. Use **Brands** to add additional brands and filter inventory by brand.

Type-specific fields and select options are also stored in the `item_fields` and `item_field_options` tables. Existing databases are migrated automatically when the application starts; existing items and their flexible JSON details are preserved.

## Configuration

- `INVENTORY_SECRET_KEY`: stable secret for Flask sessions (set this when enabling login).
- `INVENTORY_PASSWORD`: optional local password. If unset, no login screen is shown.
- `INVENTORY_DATABASE`: optional path to the SQLite database.
- `INVENTORY_UPLOADS`: optional directory for image files.
- `INVENTORY_HOST` and `INVENTORY_PORT`: bind address and port when running `python app.py`.

Uploaded files are limited to JPEG, PNG, GIF, and WebP images. Generated filenames are used; original names are retained only as metadata.

## Backup and export

Use the **Tools** menu to download CSV or JSON data, or a ZIP backup containing `catalog.sqlite` and all uploads. For a complete manual backup, stop the application and copy both `catalog.sqlite` and `uploads/` to another disk. An SSD or reliable USB device is recommended for important data.

## Raspberry Pi notes

The Flask development server is suitable for initial use on a trusted home network. Do not expose it directly to the public internet. For a more permanent deployment, use Gunicorn behind a local reverse proxy or a systemd service, and keep the database/uploads directory on reliable storage.

Example systemd service (adjust paths and username):

```ini
[Unit]
Description=Home Inventory Catalog
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/inventory/Inventory_Categlog
Environment=INVENTORY_SECRET_KEY=replace-with-a-long-random-value
Environment=INVENTORY_PASSWORD=replace-with-a-local-password
ExecStart=/home/pi/inventory/Inventory_Categlog/.venv/bin/gunicorn --workers 1 --bind 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Keep the app limited to the home network with the Pi's firewall/router settings. The optional password is a convenience for local use, not a substitute for network security.

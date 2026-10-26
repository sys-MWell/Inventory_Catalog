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

The app creates `inventory.db` and `uploads/` automatically and seeds the initial item types on first start. Use **Item types** to add custom types.

## Accounts and permissions

The application creates two local accounts the first time the database starts:

- `admin` can create, edit, and delete items, photos, brands, and item types. The admin can also export data and download backups.
- `viewer` can sign in, browse inventory, search, filter, and view item photos, but cannot change or delete anything.

The generated temporary passwords are printed once in the console when the accounts are created. Record them securely. Passwords are stored only as hashes in SQLite, so they cannot be recovered from the database.

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

Use the **Tools** menu to download CSV or JSON data, or a ZIP backup containing `inventory.db` and all uploads. For a complete manual backup, stop the application and copy both `inventory.db` and `uploads/` to another disk. An SSD or reliable USB device is recommended for important data.

## Raspberry Pi deployment

The recommended setup is Gunicorn managed by `systemd`. This starts the application after boot, restarts it if it crashes, and keeps it available to every device on the home network.

### 1. Give the Pi a stable address

Create a DHCP reservation in your router for the Pi's MAC address, using the exact six-pair MAC shown by the Pi or router, so its address remains `192.168.0.138`. If the address changes, bookmarks and health checks will stop working.

### 2. Install and copy the application

On the Pi, from your application directory:

```bash
cd /home/maxha/inventory/Inventory_Catalog
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The project path is `/home/maxha/inventory/Inventory_Catalog`. Keep the database and uploads in this persistent directory.

### 3. Create a systemd service

Create `/etc/systemd/system/home-inventory.service`:

```ini
[Unit]
Description=Home Inventory Catalog
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=maxha
WorkingDirectory=/home/maxha/inventory/Inventory_Catalog
Environment=INVENTORY_SECRET_KEY=replace-with-a-long-random-value
Environment=INVENTORY_DATABASE=/home/maxha/inventory/Inventory_Catalog/inventory.db
Environment=INVENTORY_UPLOADS=/home/maxha/inventory/Inventory_Catalog/uploads
ExecStart=/home/maxha/inventory/Inventory_Catalog/.venv/bin/gunicorn --workers 1 --bind 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Generate a secret before putting it in the service file:

```bash
/home/maxha/inventory/Inventory_Catalog/.venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now home-inventory.service
sudo systemctl status home-inventory.service
```

`enable` makes it start after a reboot. `Restart=always` makes systemd restart it after an application failure.

### 4. Open it on your home network

From any device connected to the same Wi-Fi/LAN, open:

`http://192.168.0.138:5000`

The application already binds to `0.0.0.0`, which allows LAN devices to connect. Do not port-forward port 5000 to the internet.

### 5. Check health from your main PC

The application exposes an unauthenticated health endpoint for monitoring:

`http://192.168.0.138:5000/healthz`

A healthy response is JSON similar to:

```json
{"database":"ok","status":"ok"}
```

From PowerShell on your PC:

```powershell
Invoke-RestMethod http://192.168.0.138:5000/healthz
```

To inspect the service directly on the Pi:

```bash
sudo systemctl status home-inventory.service
sudo journalctl -u home-inventory.service -n 100 --no-pager
```

Keep the application limited to your home network with your router and firewall. The login is still important, but it is not a replacement for network security. Schedule regular backups of both `inventory.db` and `uploads/` to another device.

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

The app creates its local SQLite database and `uploads/` automatically and seeds the initial item types on first start. Use **Item types** to add custom types.

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

Use the **Tools** menu to download CSV or JSON data, or a ZIP backup containing the local SQLite database and all uploads. For a complete manual backup, stop the application and copy the database file and `uploads/` to another disk. An SSD or reliable USB device is recommended for important data.

## Raspberry Pi deployment

The recommended setup is Gunicorn managed by `systemd`. This starts the application after boot, restarts it if it crashes, and keeps it available to every device on the home network.

### 1. Give the Pi a stable address

Create a DHCP reservation in your router for the Pi's MAC address, using the exact six-pair MAC shown by the Pi or router, so its address remains stable. If the address changes, bookmarks and health checks will stop working.

### 2. Install and copy the application

On the Pi, from the Python application directory:

```bash
cd /opt/inventory-catalog/app
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The Python application path is `/opt/inventory-catalog/app`. Keep the database and uploads in this persistent directory.

### 3. Create a systemd service

Create `/etc/systemd/system/home-inventory.service`:

```ini
[Unit]
Description=Home Inventory Catalog
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=inventory
WorkingDirectory=/opt/inventory-catalog/app
Environment=INVENTORY_SECRET_KEY=replace-with-a-long-random-value
Environment=INVENTORY_DATABASE=/var/lib/inventory-catalog/inventory.db
Environment=INVENTORY_UPLOADS=/var/lib/inventory-catalog/uploads

# Check and install the pinned application requirements before every start.
ExecStartPre=/opt/inventory-catalog/app/.venv/bin/python -m pip install --disable-pip-version-check --requirement /opt/inventory-catalog/app/requirements.txt
ExecStart=/opt/inventory-catalog/app/.venv/bin/python /opt/inventory-catalog/app/run.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Generate a secret before putting it in the service file:

```bash
/opt/inventory-catalog/app/.venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now home-inventory.service
sudo systemctl status home-inventory.service
```

`ExecStartPre` checks the current `requirements.txt` before every start and installs or updates packages when needed. `ExecStart` always launches `run.py`. `enable` makes the service start after a reboot, and `Restart=always` makes systemd restart it after an application failure.

If the Pi is offline during boot, dependency installation may fail until networking is restored. After the Pi is back online, restart the service:

```bash
sudo systemctl restart home-inventory.service
```

### 4. Open it on your home network

From any device connected to the same Wi-Fi/LAN, open the Pi host name or address:

`http://pi-hostname.local:5000`

The application already binds to `0.0.0.0`, which allows LAN devices to connect. Do not port-forward port 5000 to the internet.

### 5. Check health from your main PC

The application exposes an unauthenticated health endpoint for monitoring:

`http://pi-hostname.local:5000/healthz`

A healthy response is JSON similar to:

```json
{"database":"ok","status":"ok"}
```

From PowerShell on your PC:

```powershell
Invoke-RestMethod http://pi-hostname.local:5000/healthz
```

To inspect the service directly on the Pi:

```bash
sudo systemctl status home-inventory.service
sudo journalctl -u home-inventory.service -n 100 --no-pager
```

### 6. Automated database backups

The repository includes a systemd service and timer under `deployment/`. Install them on the Pi:

```bash
sudo install -m 0755 deployment/inventory-db-backup.sh /opt/inventory-catalog/app/deployment/inventory-db-backup.sh
sudo install -m 0644 deployment/inventory-db-backup.service /etc/systemd/system/inventory-db-backup.service
sudo install -m 0644 deployment/inventory-db-backup.timer /etc/systemd/system/inventory-db-backup.timer
sudo install -d -o inventory -g inventory -m 0700 /var/lib/inventory-catalog/backups
sudo systemctl daemon-reload
sudo systemctl enable --now inventory-db-backup.timer
```

The timer runs the backup shortly after boot and then every three hours. Each backup uses SQLite's consistent `.backup` operation and is stored in `/var/lib/inventory-catalog/backups` with mode `0600`. Files older than two days are deleted by the backup job. Test it immediately with:

```bash
sudo systemctl start inventory-db-backup.service
sudo systemctl status inventory-db-backup.service
sudo ls -lh /var/lib/inventory-catalog/backups
```

### 7. Protect uploaded files with filesystem permissions

The application service account must own the upload directory. This prevents other unprivileged users from adding, changing, or deleting files there; `root` can always override filesystem permissions.

Replace `inventory` below with the `User=` account from `home-inventory.service` if your Pi uses a different account:

```bash
sudo systemctl stop home-inventory.service
sudo install -d -o inventory -g inventory -m 0700 /var/lib/inventory-catalog/uploads
sudo chown -R inventory:inventory /var/lib/inventory-catalog/uploads
sudo find /var/lib/inventory-catalog/uploads -type d -exec chmod 0700 {} +
sudo find /var/lib/inventory-catalog/uploads -type f -exec chmod 0600 {} +
sudo systemctl start home-inventory.service
```

To clear the current uploads intentionally, stop the service and delete only the contents, leaving the protected directory in place:

```bash
sudo systemctl stop home-inventory.service
sudo find /var/lib/inventory-catalog/uploads -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
sudo chown inventory:inventory /var/lib/inventory-catalog/uploads
sudo chmod 0700 /var/lib/inventory-catalog/uploads
sudo systemctl start home-inventory.service
```

Keep the application limited to your home network with your router and firewall. The login is still important, but it is not a replacement for network security. Back up the database and uploads to another device if the data matters.

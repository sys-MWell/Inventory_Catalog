PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	username TEXT NOT NULL UNIQUE,
	password_hash TEXT NOT NULL,
	role TEXT NOT NULL CHECK (role IN ('admin', 'viewer')),
	created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_types (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS brands (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS item_fields (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	item_type_id INTEGER,
	field_key TEXT NOT NULL,
	label TEXT NOT NULL,
	input_type TEXT NOT NULL DEFAULT 'text',
	sort_order INTEGER NOT NULL DEFAULT 0,
	UNIQUE (item_type_id, field_key),
	FOREIGN KEY (item_type_id) REFERENCES item_types(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS item_field_options (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	field_id INTEGER NOT NULL,
	value TEXT NOT NULL,
	sort_order INTEGER NOT NULL DEFAULT 0,
	UNIQUE (field_id, value),
	FOREIGN KEY (field_id) REFERENCES item_fields(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS items (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	description TEXT,
	item_type_id INTEGER NOT NULL,
	brand_id INTEGER,
	category TEXT,
	location TEXT,
	condition TEXT,
	box_condition TEXT,
	quantity INTEGER NOT NULL DEFAULT 1,
	purchase_date TEXT,
	purchase_price REAL,
	estimated_value REAL,
	tags TEXT,
	notes TEXT,
	details TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	FOREIGN KEY (item_type_id) REFERENCES item_types(id) ON DELETE RESTRICT,
	FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS images (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	item_id INTEGER NOT NULL,
	filename TEXT NOT NULL,
	original_filename TEXT,
	caption TEXT,
	sort_order INTEGER NOT NULL DEFAULT 0,
	uploaded_at TEXT NOT NULL,
	FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type_id);
CREATE INDEX IF NOT EXISTS idx_items_location ON items(location);
CREATE INDEX IF NOT EXISTS idx_images_item ON images(item_id);

INSERT OR IGNORE INTO item_types (name) VALUES
	('General item'), ('Book'), ('Funko Pop'), ('LEGO'), ('Electronics'),
	('Clothing'), ('Artwork or framed item'), ('Collectible'), ('Furniture'), ('Other');

INSERT OR IGNORE INTO brands (name) VALUES
	('Disney'), ('Universal'), ('LEGO'), ('Funko'), ('Hasbro'), ('Mattel'),
	('Nintendo'), ('Sony'), ('Microsoft'), ('Apple'), ('Samsung'), ('Other');

INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'author', 'Author', 'text', 10 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'isbn', 'ISBN', 'text', 20 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'publisher', 'Publisher', 'text', 30 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'publication_date', 'Publication date', 'date', 40 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'edition', 'Edition', 'text', 50 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'page_count', 'Page count', 'number', 60 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'genre', 'Genre', 'text', 70 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'format', 'Format', 'select', 80 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'reading_status', 'Reading status', 'select', 90 FROM item_types WHERE name = 'Book';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'signed_copy', 'Signed copy', 'select', 100 FROM item_types WHERE name = 'Book';

INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'set_number', 'Set number', 'text', 10 FROM item_types WHERE name = 'LEGO';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'theme', 'Theme', 'text', 20 FROM item_types WHERE name = 'LEGO';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'piece_count', 'Number of pieces', 'number', 30 FROM item_types WHERE name = 'LEGO';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'completion_status', 'Completion status', 'select', 40 FROM item_types WHERE name = 'LEGO';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'original_box', 'Original box included', 'select', 50 FROM item_types WHERE name = 'LEGO';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'instruction_manual', 'Instruction manual included', 'select', 60 FROM item_types WHERE name = 'LEGO';

INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'manufacturer', 'Manufacturer', 'text', 10 FROM item_types WHERE name = 'Electronics';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'model', 'Model', 'text', 20 FROM item_types WHERE name = 'Electronics';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'serial_number', 'Serial number', 'text', 30 FROM item_types WHERE name = 'Electronics';
INSERT OR IGNORE INTO item_fields (item_type_id, field_key, label, input_type, sort_order)
SELECT id, 'warranty_expiration', 'Warranty expiration', 'date', 40 FROM item_types WHERE name = 'Electronics';

INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Hardcover', 10 FROM item_fields WHERE field_key = 'format';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Paperback', 20 FROM item_fields WHERE field_key = 'format';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Unread', 10 FROM item_fields WHERE field_key = 'reading_status';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Reading', 20 FROM item_fields WHERE field_key = 'reading_status';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Read', 30 FROM item_fields WHERE field_key = 'reading_status';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Yes', 10 FROM item_fields WHERE field_key IN ('signed_copy', 'original_box', 'instruction_manual');
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'No', 20 FROM item_fields WHERE field_key IN ('signed_copy', 'original_box', 'instruction_manual');
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Complete', 10 FROM item_fields WHERE field_key = 'completion_status';
INSERT OR IGNORE INTO item_field_options (field_id, value, sort_order)
SELECT id, 'Incomplete', 20 FROM item_fields WHERE field_key = 'completion_status';

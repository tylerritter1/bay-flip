BEGIN TRANSACTION;
CREATE TABLE properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        address TEXT UNIQUE,
        city TEXT,
        county TEXT,
        zip TEXT,
        latitude REAL,
        longitude REAL,
        list_price INTEGER,
        price_per_sqft REAL,
        beds INTEGER,
        baths REAL,
        sqft INTEGER,
        lot_sqft INTEGER,
        year_built INTEGER,
        property_type TEXT,
        days_on_market INTEGER,
        hoa_monthly INTEGER,
        listing_remarks TEXT,
        assessed_value INTEGER,
        last_sale_price INTEGER,
        last_sale_date TEXT,
        zoning TEXT,
        deal_score REAL,
        deal_tier TEXT,
        distress_signals TEXT,
        ai_analysis TEXT,
        listing_url TEXT,
        school_rating INTEGER,
        first_seen TEXT,
        last_updated TEXT,
        is_active INTEGER DEFAULT 1
    );
CREATE TABLE scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_date TEXT,
        source TEXT,
        properties_scanned INTEGER,
        new_deals_found INTEGER,
        top_deal_address TEXT,
        top_deal_score REAL
    );
INSERT INTO "scan_history" VALUES(1,'2026-08-02','Redfin CSV',258,178,'1610 Capell Valley Rd',70.0);
INSERT INTO "scan_history" VALUES(2,'2026-08-02','Redfin CSV',117,67,'99 Glenside Way',70.0);
INSERT INTO "scan_history" VALUES(3,'2026-08-02','Redfin CSV',308,227,'1475 Los Olivos Rd',70.0);
INSERT INTO "scan_history" VALUES(4,'2026-08-02','Redfin CSV',351,177,'3724 Carol St',70.0);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('scan_history',4);
COMMIT;

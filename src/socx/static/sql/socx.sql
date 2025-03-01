CREATE TABLE IF NOT EXISTS Regression(
    r_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    r_date DATE NOT NULL,
    r_time TIME NOT NULL,
    r_status TEXT NOT NULL,
    r_result TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Test(
    t_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    r_id INTEGER,

    t_date TIME NOT NULL,
    t_time TIME NOT NULL,
    t_seed INTEGER NOT NULL,
    t_status TEXT NOT NULL,
    t_result TEXT NOT NULL,
    t_command TEXT NOT NULL,

    FOREIGN KEY (r_id) REFERENCES `Regression`(r_id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

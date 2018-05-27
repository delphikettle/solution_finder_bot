CREATE TABLE User (
  id              INTEGER PRIMARY KEY UNIQUE,
  state           string,
  last_dispute_id INTEGER DEFAULT 0
);

CREATE TABLE Dispute (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  caption string,
  content TEXT,
  user_id INTEGER
);

CREATE TABLE Feedback (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id   INTEGER,
  for       BOOLEAN,
  parent_id INTEGER,
  rating    FLOAT,
  content   TEXT,
  is_answer BOOLEAN
);

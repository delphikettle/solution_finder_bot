CREATE TABLE User (
  id             INTEGER PRIMARY KEY UNIQUE,
  state          string,
  lst_dispute_id INTEGER
);

CREATE TABLE Dispute (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  caption string,
  content TEXT,
  user_id INTEGER,
  rating  FLOAT
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

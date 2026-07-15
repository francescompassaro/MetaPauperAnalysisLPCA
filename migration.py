import sqlite3

def run_migration():
    conn = sqlite3.connect("lega_pauper.db")
    cursor = conn.cursor()
    
    # Creazione della tabella degli scontri diretti game-by-game
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scontri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anno INTEGER NOT NULL,
            season INTEGER NOT NULL,
            tappa INTEGER NOT NULL,
            negozio TEXT NOT NULL,
            turno INTEGER NOT NULL,          -- Turno di svizzera (es. 1, 2, 3, 4)
            giocatore_A TEXT NOT NULL,
            mazzo_A TEXT NOT NULL,
            score_A INTEGER NOT NULL,       -- Game vinti da A (es. 2, 1, 0)
            score_B INTEGER NOT NULL,       -- Game vinti da B (es. 2, 1, 0)
            mazzo_B TEXT NOT NULL,
            giocatore_B TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Tabella 'scontri' creata con successo nel database!")

if __name__ == "__main__":
    run_migration()
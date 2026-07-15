import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, abort, send_file, flash

app = Flask(__name__)

# Rileva automaticamente se siamo su PythonAnywhere o in locale
if os.path.exists("/home/francislab"):
    DB_FILE = "/home/francislab/lega_pauper.db"
    app.template_folder = "/home/francislab/templates"
else:
    DB_FILE = "lega_pauper.db"
    app.template_folder = "templates"

PASSWORD_ADMIN = os.getenv("ADMIN_PASSWORD", "11")
app.secret_key = os.getenv("SECRET_KEY", "chiave_segreta_molto_sicura_12345")

def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()

    # DELETE mode tradizionale (sicura su PythonAnywhere)
    cursor.execute("PRAGMA journal_mode=DELETE;")

    # 1. Creazione tabella risultati
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risultati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anno INTEGER,
            season TEXT,
            tappa INTEGER,
            negozio TEXT,
            giocatore TEXT,
            mazzo TEXT,
            vittorie INTEGER,
            sconfitte INTEGER,
            pareggi INTEGER,
            punteggio INTEGER,
            link_deck TEXT DEFAULT ''
        )
    """)

    cursor.execute("PRAGMA table_info(risultati)")
    colonne = [col[1] for col in cursor.fetchall()]
    if "link_deck" not in colonne:
        cursor.execute("ALTER TABLE risultati ADD COLUMN link_deck TEXT DEFAULT ''")

    # 2. Creazione tabella scontri (Matchup 1v1 reali)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scontri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anno INTEGER,
            season TEXT,
            tappa INTEGER,
            negozio TEXT,
            turno INTEGER,
            giocatore_A TEXT,
            mazzo_A TEXT,
            score_A INTEGER,
            score_B INTEGER,
            mazzo_B TEXT,
            giocatore_B TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS giocatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mazzi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM mazzi")
    if cursor.fetchone()[0] == 0:
        mazzi_default = [
            "Abzan En Kor", "Azorius Familiars", "Bogles", "Boros Gates", "Boros Synthesizer",
            "Boros Tribe", "Caw-Gate", "Dimir Faeries", "Dimir Terror", "Dimir Control",
            "Elves", "Flicker Tron", "Golgari Gardens", "Bant Gardens", "Grixis Affinity",
            "Gruul Monster", "Gruul Ponza", "Infect MonoGreen", "Infect Simic", "Izzet Skred",
            "Jeskai Ephemerate", "Jund Evolution", "Jund Wildfire", "Kuldotha Burn",
            "Mardu Synthesis", "Monoblue Faeries", "Monoblue Terror", "Monored Madness",
            "Monored Rally", "Monowhite Heroic", "Monowhite Weenie", "Orzhov Blade",
            "Petitioners Mill", "Spy Combo", "Slivers", "Tortured Existence",
            "UG Turbofog", "Walls Combo", "WB Skyblade", "Naya Gates", "Monster Tron", "Rakdos Madness"
        ]
        cursor.executemany("INSERT INTO mazzi (nome) VALUES (?)", [(m,) for m in mazzi_default])

    conn.commit()
    conn.close()

# Inizializziamo il database all'avvio dell'app Flask
init_db()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=DELETE;")
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def is_admin():
    return session.get("authenticated", False)

# --- ROTTE UTENTE ---

@app.route("/")
def home():
    risultati = query_db("SELECT * FROM risultati ORDER BY punteggio DESC")

    classifica_dict = {}
    for r in risultati:
        g = r["giocatore"]
        classifica_dict[g] = classifica_dict.get(g, 0) + r["punteggio"]

    classifica_generale = sorted(
        [{"giocatore": k, "punteggio": v} for k, v in classifica_dict.items()],
        key=lambda x: x["punteggio"],
        reverse=True
    )

    podio = classifica_generale[:3]
    while len(podio) < 3:
        podio.append({"giocatore": "N/D", "punteggio": 0})

    metashare_dict = {}
    for r in risultati:
        m = r["mazzo"]
        metashare_dict[m] = metashare_dict.get(m, 0) + 1

    metashare_data = {
        "labels": list(metashare_dict.keys()),
        "values": list(metashare_dict.values())
    }

    anni = sorted(list(set(r["anno"] for r in risultati)), reverse=True)
    seasons = sorted(list(set(r["season"] for r in risultati)))
    tappe = sorted(list(set(r["tappa"] for r in risultati)))

    return render_template(
        "dashboard.html",
        is_admin=is_admin(),
        podio=podio,
        classifica_generale=classifica_generale,
        metashare_json=json.dumps(metashare_data),
        risultati=risultati,
        anni=anni,
        seasons=seasons,
        tappe=tappe
    )

@app.route("/matchups")
def matchups():
    # Recuperiamo gli scontri reali memorizzati nella tabella scontri
    scontri = query_db("SELECT mazzo_A, score_A, score_B, mazzo_B FROM scontri")
    
    # Raccogliamo l'elenco di tutti i mazzi univoci presenti nei record degli scontri
    set_mazzi = set()
    for s in scontri:
        set_mazzi.add(s["mazzo_A"])
        set_mazzi.add(s["mazzo_B"])
    percorsi_mazzi = sorted(list(set_mazzi))
    
    macro_list = ["Aggro", "Control", "Midrange", "Combo"]
    
    # --- MAPPATURA MACRO-ARCHETIPI ---
    archetipi_map = {
        "Kuldotha Burn": "Aggro", "Monored Madness": "Aggro", "Monored Rally": "Aggro", "Infect MonoGreen": "Aggro", "Infect Simic": "Aggro", "Monowhite Heroic": "Aggro", "Slivers": "Aggro",
        "Golgari Gardens": "Control", "Bant Gardens": "Control", "Dimir Terror": "Control", "Monoblue Terror": "Control", "Dimir Control": "Control", "Dimir Faeries": "Control", "Monoblue Faeries": "Control", "Izzet Skred": "Control", "UG Turbofog": "Control",
        "Spy Combo": "Combo", "Walls Combo": "Combo", "Boros Tribe": "Combo", "Abzan En Kor": "Combo", "Petitioners Mill": "Combo",
        "Caw-Gate": "Midrange", "Boros Synthesizer": "Midrange", "Boros Gates": "Midrange", "Naya Gates": "Midrange", "Grixis Affinity": "Midrange", "Jeskai Ephemerate": "Midrange", "Orzhov Blade": "Midrange", "Tortured Existence": "Midrange", "Gruul Ponza": "Midrange", "Gruul Monster": "Midrange", "Mardu Synthesis": "Midrange"
    }

    # Inizializziamo le strutture per il calcolo cumulativo (storico totale)
    matrice_storica = {m1: {m2: {"vittorie": 0, "partite": 0} for m2 in percorsi_mazzi} for m1 in percorsi_mazzi}
    matrice_macro = {cat1: {cat2: {"vittorie": 0, "partite": 0} for cat2 in macro_list} for cat1 in macro_list}
    
    # Elaboriamo ogni singolo scontro diretto registrato nel database
    for s in scontri:
        mA = s["mazzo_A"]
        mB = s["mazzo_B"]
        g_vinti_A = s["score_A"]
        g_vinti_B = s["score_B"]
        
        # 1. Registrazione scontro specifico (Mazzo A vs Mazzo B)
        matrice_storica[mA][mB]["partite"] += 1
        matrice_storica[mB][mA]["partite"] += 1
        
        if g_vinti_A > g_vinti_B:
            matrice_storica[mA][mB]["vittorie"] += 1
        elif g_vinti_B > g_vinti_A:
            matrice_storica[mB][mA]["vittorie"] += 1
        else:
            # Pareggio (1-1-1 o 1-1 al tempo)
            matrice_storica[mA][mB]["vittorie"] += 0.5
            matrice_storica[mB][mA]["vittorie"] += 0.5
            
        # 2. Registrazione scontro generale (Macro vs Macro)
        cat_A = archetipi_map.get(mA, "Midrange")
        cat_B = archetipi_map.get(mB, "Midrange")
        
        if cat_A != cat_B:
            matrice_macro[cat_A][cat_B]["partite"] += 1
            matrice_macro[cat_B][cat_A]["partite"] += 1
            
            if g_vinti_A > g_vinti_B:
                matrice_macro[cat_A][cat_B]["vittorie"] += 1
            elif g_vinti_B > g_vinti_A:
                matrice_macro[cat_B][cat_A]["vittorie"] += 1
            else:
                matrice_macro[cat_A][cat_B]["vittorie"] += 0.5
                matrice_macro[cat_B][cat_A]["vittorie"] += 0.5

    # --- Calcolo delle percentuali finali per i Match-Up specifici ---
    matrice_percentuali = {}
    for m1 in percorsi_mazzi:
        matrice_percentuali[m1] = {}
        for m2 in percorsi_mazzi:
            dati = matrice_storica[m1][m2]
            
            # Se non ci sono partite giocate (anche se è lo stesso mazzo)
            if dati["partite"] == 0:
                matrice_percentuali[m1][m2] = {"winrate": "N/D", "partite": 0}
            else:
                win_rate = (dati["vittorie"] / dati["partite"]) * 100
                matrice_percentuali[m1][m2] = {
                    "winrate": f"{win_rate:.0f}%", 
                    "partite": dati["partite"]
                }

    # --- Calcolo delle percentuali finali per la matrice Generale Macro-Archetipi ---
    matrice_macro_percentuali = {}
    for cat1 in macro_list:
        matrice_macro_percentuali[cat1] = {}
        for cat2 in macro_list:
            dati = matrice_macro[cat1][cat2]
            
            if dati["partite"] == 0:
                matrice_macro_percentuali[cat1][cat2] = {"winrate": "N/D", "partite": 0}
            else:
                win_rate = (dati["vittorie"] / dati["partite"]) * 100
                matrice_macro_percentuali[cat1][cat2] = {
                    "winrate": f"{win_rate:.0f}%", 
                    "partite": dati["partite"]
                }

    # Recuperiamo l'elenco completo degli scontri ordinato dal più recente per la tabella in fondo
    lista_scontri = query_db(
        "SELECT anno, season, tappa, negozio, turno, giocatore_A, mazzo_A, score_A, score_B, mazzo_B, giocatore_B FROM scontri ORDER BY id DESC"
    )

    return render_template(
        "matchups.html",
        is_admin=is_admin(),
        mazzi=percorsi_mazzi,
        matrice=matrice_percentuali,
        macro_list=macro_list,
        matrice_macro=matrice_macro_percentuali,
        scontri=lista_scontri # Passiamo la lista degli scontri reali al template
    )
    
@app.route("/liste")
def liste():
    anno = request.args.get("anno", type=int)
    season = request.args.get("season")
    tappa = request.args.get("tappa", type=int)

    risultati = query_db("SELECT * FROM risultati")
    anni = sorted(list(set(r["anno"] for r in risultati)), reverse=True)

    filtro_anno = anno if anno else (anni[0] if anni else None)

    risultati_anno = [r for r in risultati if r["anno"] == filtro_anno] if filtro_anno else []
    seasons = sorted(list(set(r["season"] for r in risultati_anno)))
    filtro_season = season if season else (seasons[0] if seasons else None)

    risultati_season = [r for r in risultati_anno if r["season"] == filtro_season] if filtro_season else []
    tappe = sorted(list(set(r["tappa"] for r in risultati_season)))
    filtro_tappa = tappa if tappa else (tappe[-1] if tappe else None)

    elementi = []
    if filtro_anno and filtro_season and filtro_tappa:
        elementi = query_db(
            "SELECT * FROM risultati WHERE anno = ? AND season = ? AND tappa = ? ORDER BY punteggio DESC",
            (filtro_anno, filtro_season, filtro_tappa)
        )

    return render_template(
        "liste.html",
        is_admin=is_admin(),
        anni=anni,
        seasons=seasons,
        tappe=tappe,
        filtro_anno=filtro_anno,
        filtro_season=filtro_season,
        filtro_tappa=filtro_tappa,
        elementi=elementi
    )

# --- ROTTE AUTENTICAZIONE ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == PASSWORD_ADMIN:
            session["authenticated"] = True
            return redirect(url_for("admin_panel"))
        return render_template("login.html", errore=True)

    if is_admin():
        return redirect(url_for("admin_panel"))
    return render_template("login.html", errore=False)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- ROTTE AMMINISTRATORE ---

@app.route("/admin")
def admin_panel():
    if not is_admin():
        return redirect(url_for("login"))

    giocatori = query_db("SELECT * FROM giocatori ORDER BY nome ASC")
    mazzi = query_db("SELECT * FROM mazzi ORDER BY nome ASC")
    ultimi_match = query_db("SELECT * FROM risultati ORDER BY id DESC LIMIT 10")

    return render_template(
        "admin.html",
        is_admin=True,
        giocatori=giocatori,
        mazzi=mazzi,
        ultimi_match=ultimi_match
    )

@app.route("/admin/match", methods=["POST"])
def salva_match():
    if not is_admin():
        abort(401)

    # 1. Recupero parametri generali della tappa
    anno = int(request.form.get("anno"))
    season = request.form.get("season")
    tappa = int(request.form.get("tappa"))
    negozio = request.form.get("negozio")
    giocatore = request.form.get("giocatore")
    mazzo = request.form.get("mazzo")
    vittorie = int(request.form.get("vittorie"))
    sconfitte = int(request.form.get("sconfitte"))
    pareggi = int(request.form.get("pareggi"))
    link_deck = request.form.get("link_deck", "")

    # Calcolo punteggio complessivo
    punti = (vittorie * 4) + (pareggi * 1) + 2
    if vittorie == 4:
        punti += 4

    # Salvataggio nella classifica 'risultati'
    query_db(
        """INSERT INTO risultati (anno, season, tappa, negozio, giocatore, mazzo, vittorie, sconfitte, pareggi, punteggio, link_deck)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (anno, season, tappa, negozio, giocatore, mazzo, vittorie, sconfitte, pareggi, punti, link_deck.strip())
    )

    # 2. Recupero liste dinamiche dei matchup singoli
    avversari = request.form.getlist("avversario[]")
    mazzi_avversari = request.form.getlist("mazzo_avversario[]")
    scores_A = request.form.getlist("score_A[]")
    scores_B = request.form.getlist("score_B[]")

    # Ciclo di salvataggio dei matchup all'interno della tabella 'scontri'
    for i in range(len(avversari)):
        avv = avversari[i].strip()
        m_avv = mazzi_avversari[i].strip()
        
        # Salviamo la riga solo se compilata interamente
        if not avv or not m_avv or scores_A[i] == '' or scores_B[i] == '':
            continue
            
        sc_A = int(scores_A[i])
        sc_B = int(scores_B[i])
        turno = i + 1

        query_db(
            """INSERT INTO scontri (anno, season, tappa, negozio, turno, giocatore_A, mazzo_A, score_A, score_B, mazzo_B, giocatore_B)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (anno, season, tappa, negozio, turno, giocatore, mazzo, sc_A, sc_B, m_avv, avv)
        )

    return redirect(url_for("admin_panel", success="match"))

@app.route("/admin/giocatore", methods=["POST"])
def aggiungi_giocatore():
    if not is_admin():
        abort(401)
    nome = request.form.get("nome", "")
    if nome.strip():
        try:
            query_db("INSERT INTO giocatori (nome) VALUES (?)", (nome.strip(),))
        except sqlite3.IntegrityError:
            pass
    # Reindirizza mantenendo attivo il tab dei giocatori
    return redirect(url_for("admin_panel", tab="giocatori"))

@app.route("/admin/mazzo", methods=["POST"])
def aggiungi_mazzo():
    if not is_admin():
        abort(401)
    nome = request.form.get("nome", "")
    if nome.strip():
        try:
            query_db("INSERT INTO mazzi (nome) VALUES (?)", (nome.strip(),))
        except sqlite3.IntegrityError:
            pass
    # Reindirizza mantenendo attivo il tab dei mazzi
    return redirect(url_for("admin_panel", tab="mazzi"))

@app.route("/admin/elimina-giocatore/<int:giocatore_id>")
def elimina_giocatore(giocatore_id):
    if not is_admin():
        abort(401)
    query_db("DELETE FROM giocatori WHERE id = ?", (giocatore_id,))
    return redirect(url_for("admin_panel", tab="giocatori"))

@app.route("/admin/elimina-mazzo/<int:mazzo_id>")
def elimina_mazzo(mazzo_id):
    if not is_admin():
        abort(401)
    query_db("DELETE FROM mazzi WHERE id = ?", (mazzo_id,))
    return redirect(url_for("admin_panel", tab="mazzi"))

@app.route("/admin/backup")
def scarica_backup():
    if not is_admin():
        abort(401)
    if os.path.exists(DB_FILE):
        return send_file(DB_FILE, as_attachment=True, download_name="lega_pauper_backup.db")
    abort(404)

if __name__ == "__main__":
    app.run(debug=True)
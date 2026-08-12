# Pauper League Database 🏆

Un'applicazione web leggera sviluppata in Python con **Flask** e **SQLite** per tracciare i risultati, la classifica generale e il metashare delle tappe della Lega Pauper locale.

## 🚀 Funzionalità

* **Dashboard Generale**: Classifica dei giocatori aggiornata in tempo reale, podio provvisorio e grafico interattivo del Meta Share.
* **Archivio Liste**: Filtro avanzato per anno, stagione (season) e tappa per consultare i mazzi giocati e i relativi link alle liste.
* **Pannello Amministratore**: Login sicuro per aggiungere match, inserire nuovi giocatori/archetipi ed eliminare record errati.
* **Backup**: Funzione integrata per scaricare il database SQLite direttamente dal pannello di controllo.

## 🛠️ Installazione Locale

1. Clona il repository:
   ```bash
   git clone https://github.com/francescompassaro/metapauperlpca.git
   cd metapauperlpca

   Primo Avvio applicazione 
   python3 -m venv venv
   source venv/bon/activate
   
   pip install --upgrade pip
   pip install -r requirements.txt
   python3 main.py
   
   (Metodo per debug)
   export FLASK_APP=main.py
   export FLASK_ENV=development
   flask run
   
   ```bash
   git status 
   git add .
   git commit -m "Descrizione modifiche"

   git push origin main --[Invia i commit locali al repository remoto su GitHub]

   git pull origin main --Scarica ed eseguel il merge degli ultimi aggiornamenti da GitHub
   git log --oneline -n 5

   sqlite3 lega_pauper.db
   Apre l'interfaccia a riga di comando direttamente sul database SQLite.

   sqlite3 lega_pauper.db ".tables"
   Mostra rapidamente l'elenco delle tabelle nel DB (risultati, scontri, giocatori, mazzi).

   sqlite3 lega_pauper.db "SELECT COUNT(*) FROM scontri;"
   Esegue una rapida query SQL dal terminale per verificare quanti scontri sono stati registrati.

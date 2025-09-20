1. GUIDA ALL’INSTALLAZIONE E TESTING
    • Requisti
      Per utilizzare l’applicazione è necessaria un dispositivo emulato Android con API 35 e una connessione a Internet.
      
    • Avvio del Web Server
      Il progetto è formato dalle cartelle PropertyFinder (app android) e PropertyFinderService (backend web server)
      
      - Scaricare la cartella PropertyFinderService
      - Utilizzare la shell bash per eseguire i comandi riportati in seguito
      - Per avviare il Web Server è necessario navigare nella seguente directory PropertyFinderService/Backend/WebServer
      - WINDOWS:
      Avviare il Server con:
       $env:FLASK_APP = "WebServer.py"
       flask run --host=0.0.0.0 --port=5000 (verificare che la porta 5000 sia libera in locale)
      potrebbe essere necessario installare le librerie flask, pymongo e joblib
      - LINUX: 
      Avviare il Server con:
      flask - -app WebServer.py run 
      Ora il Server è pronto per ricevere le richieste.


      
 2. Verifica del database
      
    Il database utilizzato è MongoDB Atlas, quindi ospitato in cloud.
    Per agevolare il testing, l’accesso è stato configurato in modo da consentire connessioni da qualsiasi indirizzo IP (0.0.0.0./0)
    A causa delle politiche di autenticazione imposte da MongoDB Atlas, non è possibile condividere il database in modalità completamente aperta o renderlo liberamente consultabile.
    Tuttavia, l’applicazione è pienamente funzionante senza necessità di scaricare o installare il database in locale. 
      

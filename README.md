# Pixoo AI Display – Raspberry Pi 4 / Docker

Ein kleines, lokal laufendes Steuerungsprojekt für deinen **Divoom Pixoo 64** unter `192.168.178.188`. Ein KI-Agent, OpenClaw, Python-Skript oder OpenHAB kann per authentifizierter HTTP-API Inhalte anzeigen lassen. Es ist **kein KI-Modell im Container**: Die KI nutzt die API als Werkzeug.

## Architektur

Agent / Script → Bearer-geschützte Flask-API auf Raspberry Pi → 64×64 RGB-Rendering mit Pillow → lokale Divoom-API → Pixoo.

## Installation auf dem Raspberry Pi

1. ZIP auf dem Pi entpacken und ins Verzeichnis `pixoo-ai-display` wechseln.
2. `.env` erzeugen:

   ```bash
   cp .env.example .env
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

3. Den generierten Token in `.env` als `API_TOKEN=...` eintragen. Die Pixoo-IP ist bereits hinterlegt.
4. Starten:

   ```bash
   docker compose up -d --build
   docker compose ps
   docker compose logs --tail=50 pixoo-ai
   ```

5. Weboberfläche aufrufen: `http://<RASPBERRY-PI-IP>:8088` (IP des Pi, nicht des Pixoo).
   Den API-Token in das Token-Feld einsetzen und eine Testnachricht senden.

## API-Endpunkte

Alle `/api/*`-Endpunkte verlangen den Header `Authorization: Bearer <API_TOKEN>`. Der Healthcheck `/health` ist ohne Token verfügbar.

### Nachricht

```bash
curl -X POST "http://<RASPBERRY-PI-IP>:8088/api/display" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"message","text":"Hallo vom Agenten!","theme":"night"}'
```

### Informationskarte

```bash
curl -X POST "http://<RASPBERRY-PI-IP>:8088/api/display" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"card","title":"Wohnzimmer","text":"21,5 °C","footer":"Luftfeuchte 48%","theme":"green"}'
```

Themes: `night`, `green`, `warm`, `red`.

### Helligkeit ändern

```bash
curl -X POST "http://<RASPBERRY-PI-IP>:8088/api/brightness" \
  -H "Authorization: Bearer <API_TOKEN>" -H "Content-Type: application/json" \
  -d '{"brightness":35}'
```

### Gerätestatus

```bash
curl -H "Authorization: Bearer <API_TOKEN>" "http://<RASPBERRY-PI-IP>:8088/api/status"
```

## Einbindung in einen KI-Agenten

Werkzeugdefinition (für Agenten mit HTTP-Tools / eigene Apps):

- Name: `zeige_auf_pixoo`
- Beschreibung: „Zeigt eine kurze Nachricht oder 64×64-Informationskarte auf dem Pixoo 64 an. Verwende kurze Texte.“
- Methode: `POST`
- URL: `http://<RASPBERRY-PI-IP>:8088/api/display`
- Header: `Authorization: Bearer <API_TOKEN>` und `Content-Type: application/json`
- Parameter: `mode` (`message` oder `card`), `text` (String), optional `title`, `footer`, `theme`.

Ein Python-Beispiel für Agenten und andere Programme liegt unter `example_agent.py`.

**Wichtig:** ChatGPT in der Cloud hat keine direkte Verbindung zu deinem privaten LAN. Du brauchst einen Agenten, der im LAN arbeitet (z. B. lokales OpenClaw), oder eine separat abgesicherte Verbindung/Connector. Eine Freigabe der Pixoo-IP oder des Flask-Ports ins Internet wird nicht empfohlen.

## Sicherheit

- Alle steuernden Endpunkte sind mit einem geheimen Bearer-Token geschützt. Der Token wird nicht dauerhaft im Webinterface gespeichert.
- Dashboard und API verwenden im lokalen Netzwerk HTTP (unverschlüsselt). Nur in einem vertrauenswürdigen LAN verwenden oder einen abgesicherten Reverse Proxy/TLS davor schalten.
- **Keine Portfreigaben im Router.**
- Keine beliebigen Ziel-URLs an die API übergebbar; Pixoo-IP wird vom Betreiber per `.env` festgelegt.
- Weil mehrere API-Aufrufe gleichzeitig kommen können, werden Gerätezugriffe serialisiert und Frame-Updates begrenzt.

## Fehlerbehebung

- `502` vom Server: Gerät nicht erreichbar oder Pixoo hat einen API-Fehler gemeldet. IP und Pixoo-Modell/Firmware prüfen.
- `401`: Token fehlt oder stimmt nicht.
- `400`: Ungültige Eingabe.
- Der ursprüngliche Pixoo 64 nutzt meist `http://192.168.178.188/post`. Neuere Pixoo-64-II-Varianten können `http://192.168.178.188:9000/divoom_api` verwenden – bei Bedarf `.env` umstellen und neu starten.
- Bei langen Texten reduziert das Rendering die Schriftgröße und kürzt sie bei Bedarf. 64×64 Pixel sind für kurze Meldungen optimiert.
- Falls das Gerät nach vielen Updates nicht mehr reagiert, weniger häufig senden bzw. dessen Firmware prüfen.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests benötigen `Pillow`. Sie testen Rendering, nicht die Verbindung zu deinem realen Gerät.

## Ausbauideen

- MQTT-Bridge für OpenHAB-Events
- priorisierte Nachrichtenwarteschlange und Zeitsteuerung
- Anzeige mehrerer Karten im Wechsel
- MCP-Server mit separater Authentifizierung / lokalem Agenten
- Wetter, Sensoren, Kalender, Finanz- und Serverdaten

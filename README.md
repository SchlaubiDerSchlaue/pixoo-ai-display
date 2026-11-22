# Pixoo AI Display – Raspberry Pi 4 / Docker

Ein kleines, lokal laufendes Steuerungsprojekt für deinen **Divoom Pixoo 64** unter `192.168.178.188`. Über das Flask-Dashboard, die REST-API oder MCP kannst du Inhalte anzeigen und den Bildschirm steuern.

## Architektur

Dashboard, REST und MCP laufen im selben Container auf Port `8088`. Alle drei teilen sich den Gerätezugriff auf die lokale Divoom-API. Pillow rendert Nachrichten und Karten als 64×64-RGB-Bilder.

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

## Portainer

1. In einer **Docker-Standalone**-Umgebung unter **Stacks → Add stack → Repository** einen Stack anlegen.
2. Als Repository-URL `https://github.com/SchlaubiDerSchlaue/pixoo-ai-display.git`, als Referenz `refs/heads/main` und als Compose-Pfad `docker-compose.yml` wählen. Portainer baut `pixoo-ai:1.0` aus diesem Repository.
3. In den Umgebungsvariablen des Stacks `API_TOKEN` setzen (mindestens 20 Zeichen). Bestehende Stacks können `PIXOO_API_TOKEN` weiterverwenden. Bei Bedarf auch `PIXOO_HOST` und `PIXOO_PATH` setzen. Alternativ lässt sich die lokal ausgefüllte `.env` über **Load variables from .env file** importieren.
4. **Deploy the stack** wählen. Dashboard, REST und MCP sind über Port `8088` des Docker-Hosts erreichbar.

Für einen bestehenden Web-Editor-Stack mit lokalem Image auf dem Docker-Host `docker build -t pixoo-ai:1.0 .` aus dem aktualisierten Repository ausführen. Anschließend den Stack in Portainer neu bereitstellen, damit der Container vom neu gebauten Image startet.

[Portainer-Dokumentation zum Deployment aus Git](https://docs.portainer.io/user/docker/stacks/add)

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

### Bildschirm ein- und ausschalten

```bash
curl -X POST "http://<RASPBERRY-PI-IP>:8088/api/power" \
  -H "Authorization: Bearer <API_TOKEN>" -H "Content-Type: application/json" \
  -d '{"on":false}'
```

`on` erwartet einen JSON-Boolean (`true` oder `false`). Die Antwort enthält `ok` und `on`. Das Gerät bleibt beim Ausschalten des Bildschirms am Strom. [Divoom-Befehl `Channel/OnOffScreen`](http://doc.divoom-gz.com/web/#/12?page_id=223)

## MCP

Im MCP-Client **Streamable HTTP** mit der URL `http://<RASPBERRY-PI-IP>:8088/mcp` konfigurieren. Der Client muss bei jeder Anfrage `Authorization: Bearer <API_TOKEN>` senden. Der Server verwendet denselben Token wie REST. Falls der Client einen `Origin`-Header mitsendet, muss er zur Server-URL passen.

| Werkzeug | Eingaben |
| --- | --- |
| `show_message` | `text` (1–180 Zeichen), optional `theme` (`night`, `green`, `warm`, `red`) |
| `set_brightness` | `brightness` (ganze Zahl von 0 bis 100) |
| `set_power` | `on` (`true` oder `false`) |

Der Server verwendet Streamable HTTP aus dem offiziellen MCP-Python-SDK. [MCP-Python-SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)

```bash
curl "http://<RASPBERRY-PI-IP>:8088/mcp" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
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
- Dashboard, REST und MCP verwenden im lokalen Netzwerk HTTP (unverschlüsselt). Nur in einem vertrauenswürdigen LAN verwenden oder einen abgesicherten Reverse Proxy/TLS davor schalten.
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

Die Rendering-Tests benötigen DejaVu Sans und DejaVu Sans Bold aus `fonts-dejavu-core`.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

Die Tests prüfen Rendering, Weboberfläche, REST und MCP. Divoom-Antworten werden simuliert.

## Ausbauideen

- MQTT-Bridge für OpenHAB-Events
- priorisierte Nachrichtenwarteschlange und Zeitsteuerung
- Anzeige mehrerer Karten im Wechsel
- Wetter, Sensoren, Kalender, Finanz- und Serverdaten

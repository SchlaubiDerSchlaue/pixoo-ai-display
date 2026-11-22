import hmac
import os
from flask import Flask, jsonify, request, render_template_string
from .device import PixooDevice
from .render import render_card, render_message, image_to_data_url

app=Flask(__name__)
TOKEN=os.environ.get('API_TOKEN','')
if len(TOKEN)<20:
    raise RuntimeError('API_TOKEN muss mindestens 20 Zeichen haben; .env prüfen')
DEVICE=PixooDevice(os.getenv('PIXOO_HOST','192.168.178.188'),os.getenv('PIXOO_PATH','/post'))
MAX_CHARS=180

PAGE='''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pixoo AI Display</title><style>body{font:16px system-ui;background:#0b1220;color:#e8f3ff;max-width:750px;margin:45px auto;padding:0 18px}h1{color:#68d6fa}section{background:#162238;padding:20px;border-radius:12px;margin:16px 0}input,select,textarea,button{box-sizing:border-box;font:inherit;padding:11px;border-radius:6px;border:1px solid #596778}input,select,textarea{background:#0b1526;color:#fff;width:100%;margin:5px 0 12px}button{background:#51bedd;color:#05111e;font-weight:700;cursor:pointer}label{font-weight:600}pre{white-space:pre-wrap;word-break:break-word}img{width:320px;max-width:100%;image-rendering:pixelated;border:5px solid #29394e}</style><h1>Pixoo AI Display</h1><p>Lokales Steuerungs-Dashboard für den Pixoo 64.</p><section><label>API-Token (nur im Browser gespeichert, nicht auf dem Server)</label><input id="token" type="password" autocomplete="off" placeholder="Token aus deiner .env"><label>Anzeige</label><select id="mode"><option value="message">Nachricht</option><option value="card">Informationskarte</option></select><label>Überschrift (nur Karte)</label><input id="title" maxlength="180" placeholder="Wetter"><label>Text / Wert</label><textarea id="value" maxlength="180" rows="3" placeholder="Hallo vom KI-Agenten!"></textarea><label>Fußzeile (nur Karte)</label><input id="footer" maxlength="180" placeholder="Wohnzimmer"><label>Farbschema</label><select id="theme"><option>night</option><option>green</option><option>warm</option><option>red</option></select><button onclick="send()">Auf Pixoo anzeigen</button><p id="result" role="status"></p><img id="preview" style="display:none" alt="Vorschau"></section><section><h2>Helligkeit</h2><input id="brightness" type="number" min="0" max="100" value="50"><button onclick="setBrightness()">Helligkeit setzen</button></section><section><h2>Display</h2><button type="button" onclick="setPower(true)">Einschalten</button> <button type="button" onclick="setPower(false)">Ausschalten</button><p id="powerResult" role="status"></p></section><section><h2>Agenten-API</h2><p><code>POST /api/display</code>, <code>POST /api/brightness</code>, <code>POST /api/power</code>, <code>GET /api/status</code>, <code>/mcp</code></p><p>Details siehe README.md im Projekt.</p></section><script>
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+document.getElementById('token').value},body:JSON.stringify(body)});let data=await r.json();if(!r.ok)throw Error(data.error||r.status);return data;}
async function send(){try{const mode=document.getElementById('mode').value;const data=await api('/api/display',{mode,theme:document.getElementById('theme').value,title:document.getElementById('title').value,text:document.getElementById('value').value,footer:document.getElementById('footer').value});document.getElementById('result').textContent='Erfolgreich gesendet';document.getElementById('preview').src=data.preview;document.getElementById('preview').style.display='block'}catch(e){document.getElementById('result').textContent='Fehler: '+e.message}}
async function setBrightness(){try{await api('/api/brightness',{brightness:Number(document.getElementById('brightness').value)});document.getElementById('result').textContent='Helligkeit gesetzt'}catch(e){document.getElementById('result').textContent='Fehler: '+e.message}}
async function setPower(on){
  const result = document.getElementById('powerResult');
  try {
    await api('/api/power', {on});
    result.textContent = on ? 'Display eingeschaltet' : 'Display ausgeschaltet';
  } catch (e) {
    result.textContent = 'Fehler: ' + e.message;
  }
}
</script></html>'''

def error(message,status):
    return jsonify({'ok':False,'error':message}),status

def authorized(header):
    return header.startswith('Bearer ') and hmac.compare_digest(header[7:].encode(), TOKEN.encode())

@app.before_request
def secure_api():
    if request.path.startswith('/api/') and not authorized(request.headers.get('Authorization', '')):
        return error('Ungültiger oder fehlender Bearer-Token',401)

@app.get('/')
def homepage():
    return render_template_string(PAGE)

@app.get('/health')
def health():
    return jsonify({'ok':True,'service':'pixoo-ai-display'})

def get_body():
    body=request.get_json(silent=True)
    if not isinstance(body,dict):
        raise ValueError('JSON-Objekt erforderlich')
    return body

def field(body,key):
    val=body.get(key,'')
    if not isinstance(val,str) or len(val)>MAX_CHARS:
        raise ValueError(f'{key}: Text mit maximal {MAX_CHARS} Zeichen erforderlich')
    return val

def show_message(text, theme):
    if not text.strip():
        raise ValueError('text darf nicht leer sein')
    image = render_message(text, theme)
    DEVICE.push(image)
    return image

def set_brightness(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('brightness muss eine ganze Zahl von 0 bis 100 sein')
    DEVICE.brightness(value)
    return {'ok': True, 'brightness': value}

def set_power(on):
    if type(on) is not bool:
        raise ValueError('on muss true oder false sein')
    DEVICE.power(on)
    return {'ok': True, 'on': on}

@app.post('/api/display')
def display():
    try:
        body=get_body()
        mode=body.get('mode','message')
        theme=body.get('theme','night')
        if mode not in ('message','card') or not isinstance(theme,str):
            raise ValueError('mode oder theme ungültig')
        if mode=='message':
            image = show_message(field(body, 'text'), theme)
        else:
            title=field(body,'title')
            value=field(body,'text')
            footer=field(body,'footer')
            if not (title or value or footer): raise ValueError('Karte darf nicht leer sein')
            image=render_card(title,value,footer,theme)
            DEVICE.push(image)
        return jsonify({'ok':True,'mode':mode,'preview':image_to_data_url(image)})
    except ValueError as exc:
        return error(str(exc),400)
    except RuntimeError as exc:
        app.logger.warning('Pixoo Fehler: %s',exc)
        return error(str(exc),502)

@app.post('/api/brightness')
def brightness():
    try:
        return jsonify(set_brightness(get_body().get('brightness')))
    except ValueError as exc:
        return error(str(exc),400)
    except RuntimeError as exc:
        return error(str(exc),502)

@app.post('/api/power')
def power():
    try:
        return jsonify(set_power(get_body().get('on')))
    except ValueError as exc:
        return error(str(exc),400)
    except RuntimeError as exc:
        return error(str(exc),502)

@app.get('/api/status')
def status():
    try:
        return jsonify({'ok':True,'device':DEVICE.status()})
    except RuntimeError as exc:
        return error(str(exc),502)

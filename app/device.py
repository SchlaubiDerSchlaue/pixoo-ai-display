import threading
import time
import requests

class PixooDevice:
    def __init__(self, host, path='/post'):
        if not path.startswith('/'):
            raise ValueError('PIXOO_PATH muss mit / beginnen')
        self.url = f'http://{host}{path}'
        self.lock = threading.Lock()
        self.last_push = 0.0
        self.pic_id = 0
        self.session = requests.Session()

    def command(self, payload):
        try:
            response = self.session.post(self.url, json=payload, timeout=(2,8))
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f'Pixoo nicht erreichbar oder ungültige Antwort: {exc}') from exc
        if not isinstance(result,dict):
            raise RuntimeError(f'Unerwartete Geräteantwort: {result!r}')
        status = result.get('error_code',result.get('ReturnCode',0))
        if status not in (0, '0', None):
            raise RuntimeError(f'Pixoo meldet Fehler: {result!r}')
        return result

    def push(self, image):
        from .render import image_to_payload
        with self.lock:
            delay=1.1-(time.monotonic()-self.last_push)
            if delay>0: time.sleep(delay)
            self.pic_id += 1
            if self.pic_id >= 100:
                self.command({'Command':'Draw/ResetHttpGifId'})
                self.pic_id=1
            result=self.command({
                'Command':'Draw/SendHttpGif',
                'PicNum':1,
                'PicWidth':64,
                'PicOffset':0,
                'PicID':self.pic_id,
                'PicSpeed':1000,
                'PicData':image_to_payload(image),
            })
            self.last_push=time.monotonic()
            return result

    def brightness(self, value):
        with self.lock:
            return self.command({'Command':'Channel/SetBrightness', 'Brightness':value})

    def power(self, on):
        with self.lock:
            return self.command({'Command': 'Channel/OnOffScreen', 'OnOff': int(on)})

    def status(self):
        with self.lock:
            return self.command({'Command':'Channel/GetIndex'})

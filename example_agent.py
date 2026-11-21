"""Beispiel eines lokalen Agenten-Tools; Variablen setzen und dann ausführen."""
import os
import requests

API_URL = os.environ['PIXOO_AGENT_API_URL'].rstrip('/')
API_TOKEN = os.environ['PIXOO_AGENT_API_TOKEN']

def zeige_auf_pixoo(text, title='', footer='', theme='night'):
    body = {'mode': 'card' if title or footer else 'message', 'text': text,
            'title': title, 'footer': footer, 'theme': theme}
    response = requests.post(
        f'{API_URL}/api/display',
        headers={'Authorization': f'Bearer {API_TOKEN}'},
        json=body, timeout=15)
    response.raise_for_status()
    return {'ok': response.json().get('ok')}

if __name__ == '__main__':
    print(zeige_auf_pixoo('Agent bereit', title='Pixoo AI', theme='green'))

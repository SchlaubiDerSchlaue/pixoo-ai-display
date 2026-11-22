import os
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

TOKEN = 'test-token-pixoo-123456789'
with patch.dict(os.environ, {'API_TOKEN': TOKEN}):
    from app import main, server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = cls.enterClassContext(TestClient(server.app, base_url='http://pixoo.local:8088'))

    def setUp(self):
        self.enterContext(patch.object(main.DEVICE, 'last_push', 0.0))
        self.command = self.enterContext(patch.object(main.DEVICE, 'command', return_value={'error_code': 0}))
        self.api_headers = {'Authorization': f'Bearer {TOKEN}'}
        self.mcp_headers = {**self.api_headers, 'Accept': 'application/json, text/event-stream'}

    def rpc(self, method, params=None, *, request_id=1, headers=None):
        body = {'jsonrpc': '2.0', 'method': method}
        if request_id is not None:
            body['id'] = request_id
        if params is not None:
            body['params'] = params
        return self.client.post('/mcp', json=body, headers=self.mcp_headers if headers is None else headers)

    def call_tool(self, name, arguments):
        response = self.rpc('tools/call', {'name': name, 'arguments': arguments})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['result']

    def test_dashboard_and_existing_rest_routes(self):
        homepage = self.client.get('/')
        self.assertEqual(homepage.status_code, 200)
        self.assertIn('setPower(true)', homepage.text)
        self.assertIn('setPower(false)', homepage.text)
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/api/status').status_code, 401)
        self.assertEqual(self.client.get('/api/status', headers=self.api_headers).json(),
                         {'ok': True, 'device': {'error_code': 0}})

        for mode in ('message', 'card'):
            with self.subTest(mode=mode):
                response = self.client.post('/api/display', json={'mode': mode, 'text': 'Hallo'},
                                            headers=self.api_headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['mode'], mode)
                self.assertTrue(response.json()['preview'].startswith('data:image/png;base64,'))
                self.assertEqual(self.command.call_args.args[0]['Command'], 'Draw/SendHttpGif')

        response = self.client.post('/api/brightness', json={'brightness': 35}, headers=self.api_headers)
        self.assertEqual(response.json(), {'ok': True, 'brightness': 35})
        self.command.assert_called_with({'Command': 'Channel/SetBrightness', 'Brightness': 35})

    def test_rest_power(self):
        for on in (True, False):
            response = self.client.post('/api/power', json={'on': on}, headers=self.api_headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'ok': True, 'on': on})
            self.command.assert_called_with({'Command': 'Channel/OnOffScreen', 'OnOff': int(on)})

    def test_power_rejects_missing_credentials_and_invalid_input(self):
        self.assertEqual(self.client.post('/api/power', json={'on': True}).status_code, 401)
        for body in ({}, {'on': 0}, {'on': 'false'}, {'on': None}, []):
            with self.subTest(body=body):
                response = self.client.post('/api/power', json=body, headers=self.api_headers)
                self.assertEqual(response.status_code, 400)
        self.command.assert_not_called()

    def test_mcp_requires_token_and_validates_origin(self):
        for method in ('GET', 'POST', 'DELETE'):
            for headers in ({}, {'Authorization': 'Bearer wrong'}):
                with self.subTest(method=method, headers=headers):
                    response = self.client.request(method, '/mcp', headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers['www-authenticate'], 'Bearer')
        response = self.rpc('tools/list', headers={**self.mcp_headers, 'Origin': 'https://other.example'})
        self.assertEqual(response.status_code, 403)
        self.command.assert_not_called()

    def test_mcp_initializes_and_exposes_tools(self):
        response = self.rpc('initialize', {
            'protocolVersion': '2025-11-25',
            'capabilities': {},
            'clientInfo': {'name': 'pixoo-test', 'version': '1'},
        }, headers={**self.mcp_headers, 'Origin': 'http://pixoo.local:8088'})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()['result']
        self.assertEqual(result['serverInfo']['name'], 'Pixoo AI Display')
        self.assertIn('tools', result['capabilities'])
        self.mcp_headers['MCP-Protocol-Version'] = result['protocolVersion']
        notification = self.rpc('notifications/initialized', request_id=None)
        self.assertEqual(notification.status_code, 202)
        tools = self.rpc('tools/list').json()['result']['tools']
        self.assertEqual({tool['name'] for tool in tools}, {'show_message', 'set_brightness', 'set_power'})

    def test_mcp_calls_each_tool(self):
        result = self.call_tool('show_message', {'text': 'Hallo', 'theme': 'green'})
        self.assertFalse(result['isError'])
        self.assertEqual(result['structuredContent'], {'ok': True})
        self.assertEqual(self.command.call_args.args[0]['Command'], 'Draw/SendHttpGif')

        for brightness in (0, 100):
            result = self.call_tool('set_brightness', {'brightness': brightness})
            self.assertEqual(result['structuredContent'], {'ok': True, 'brightness': brightness})
            self.command.assert_called_with({'Command': 'Channel/SetBrightness', 'Brightness': brightness})

        for on in (True, False):
            result = self.call_tool('set_power', {'on': on})
            self.assertEqual(result['structuredContent'], {'ok': True, 'on': on})
            self.command.assert_called_with({'Command': 'Channel/OnOffScreen', 'OnOff': int(on)})

    def test_mcp_rejects_invalid_input(self):
        for name, arguments in (
            ('show_message', {'text': '   '}),
            ('show_message', {'text': 'a' * 181}),
            ('set_brightness', {'brightness': 101}),
            ('set_brightness', {'brightness': True}),
            ('set_brightness', {'brightness': '35'}),
            ('set_power', {'on': 0}),
            ('set_power', {'on': 'false'}),
        ):
            with self.subTest(name=name, arguments=arguments):
                self.assertTrue(self.call_tool(name, arguments)['isError'])
        self.command.assert_not_called()

    def test_device_failure_surfaces_in_rest_and_mcp(self):
        self.command.side_effect = RuntimeError('Pixoo meldet Fehler')
        response = self.client.post('/api/power', json={'on': True}, headers=self.api_headers)
        self.assertEqual(response.status_code, 502)
        result = self.call_tool('set_power', {'on': True})
        self.assertTrue(result['isError'])
        self.assertIn('Pixoo meldet Fehler', result['content'][0]['text'])

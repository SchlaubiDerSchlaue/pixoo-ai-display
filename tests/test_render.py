import unittest
from app.render import render_card,render_message,image_to_payload

class RenderTests(unittest.TestCase):
    def test_render(self):
        for im in (render_card('Wetter','21,5 °C','Wohnzimmer'),render_message('Backup erfolgreich!')):
            self.assertEqual(im.size,(64,64))
            self.assertEqual(im.mode,'RGB')
            self.assertEqual(len(image_to_payload(im)),16384)
    def test_invalid_theme(self):
        with self.assertRaises(ValueError): render_message('Hallo','bad')

if __name__=='__main__': unittest.main()

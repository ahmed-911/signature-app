import unittest
from io import BytesIO
from PIL import Image, ImageDraw
from processing import extract_ink, png_bytes


class InkTests(unittest.TestCase):
    def test_white_paper_is_transparent_and_strokes_unchanged(self):
        original = Image.new('RGB', (100, 60), 'white')
        ImageDraw.Draw(original).line((10, 20, 80, 45), fill='black', width=3)
        output = extract_ink(original, trim=False)
        self.assertEqual(output.getpixel((0, 0))[3], 0)
        self.assertEqual(output.getpixel((10, 20)), (0, 0, 0, 255))
        self.assertEqual(output.getchannel('A').getbbox(), (10, 19, 81, 47))
        reopened = Image.open(BytesIO(png_bytes(output)))
        self.assertEqual(reopened.mode, 'RGBA')

    def test_colored_ink_and_grey_edges(self):
        image = Image.new('RGB', (3, 1), 'white')
        image.putpixel((1, 0), (0, 0, 180))
        image.putpixel((2, 0), (128, 128, 128))
        output = extract_ink(image, black=False, trim=False)
        self.assertEqual(output.getpixel((1, 0)), (0, 0, 180, 255))
        self.assertEqual(output.getpixel((2, 0))[3], 127)

    def test_empty_selection(self):
        with self.assertRaises(ValueError):
            extract_ink(Image.new('RGB', (30, 30), 'white'))


if __name__ == '__main__':
    unittest.main()

import io
import unittest
from cryptography.fernet import Fernet, InvalidToken
from ops.archive import encrypt, decrypt, CHUNK


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.cipher = Fernet(Fernet.generate_key())
        self.original = b"sensitive-pilot-records" * (CHUNK // 10)
        stream = io.BytesIO()
        encrypt(io.BytesIO(self.original), stream, self.cipher)
        self.archive = stream.getvalue()

    def test_multiframe_roundtrip(self):
        output = io.BytesIO()
        decrypt(io.BytesIO(self.archive), output, self.cipher)
        self.assertEqual(output.getvalue(), self.original)
        self.assertNotIn(b"sensitive-pilot-records", self.archive)

    def test_wrong_key(self):
        with self.assertRaises(InvalidToken):
            decrypt(io.BytesIO(self.archive), io.BytesIO(), Fernet(Fernet.generate_key()))

    def test_truncation_rejected(self):
        with self.assertRaises((ValueError, InvalidToken)):
            decrypt(io.BytesIO(self.archive[:-100]), io.BytesIO(), self.cipher)

    def test_corruption_rejected(self):
        damaged = bytearray(self.archive)
        damaged[100] ^= 1
        with self.assertRaises((ValueError, InvalidToken)):
            decrypt(io.BytesIO(damaged), io.BytesIO(), self.cipher)

    def test_appended_data_rejected(self):
        with self.assertRaises(ValueError):
            decrypt(io.BytesIO(self.archive + b"extra"), io.BytesIO(), self.cipher)

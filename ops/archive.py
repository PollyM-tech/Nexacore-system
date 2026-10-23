"""Authenticated streaming backup encryption. Keys never enter command arguments."""
import hashlib
import os
import struct
import uuid
from cryptography.fernet import Fernet

MAGIC = b"LINTECH-BACKUP-1\n"
CHUNK = 1024 * 1024


def key_from_file(path):
    if os.stat(path).st_mode & 0o077:
        raise ValueError("Backup key file must be readable only by its owner (chmod 600).")
    with open(path, "rb") as stream:
        return Fernet(stream.read().strip())


def encrypt(source, target, cipher):
    backup_id = uuid.uuid4().bytes
    target.write(MAGIC + backup_id)
    digest = hashlib.sha256()
    count = 0
    while data := source.read(CHUNK):
        digest.update(data)
        payload = backup_id + struct.pack(">Q", count) + b"D" + data
        token = cipher.encrypt(payload)
        target.write(struct.pack(">I", len(token)) + token)
        count += 1
    token = cipher.encrypt(backup_id + struct.pack(">Q", count) + b"E" + digest.digest())
    target.write(struct.pack(">I", len(token)) + token)


def decrypt(source, target, cipher):
    if source.read(len(MAGIC)) != MAGIC:
        raise ValueError("Invalid backup format.")
    backup_id = source.read(16)
    digest = hashlib.sha256()
    count = 0
    while True:
        size = source.read(4)
        if len(size) != 4:
            raise ValueError("Incomplete backup.")
        length = struct.unpack(">I", size)[0]
        if not 0 < length < 2 * CHUNK:
            raise ValueError("Invalid backup frame.")
        payload = cipher.decrypt(source.read(length))
        if len(payload) < 25 or payload[:16] != backup_id or struct.unpack(">Q", payload[16:24])[0] != count:
            raise ValueError("Backup frame order or identity mismatch.")
        if payload[24:25] == b"E":
            if payload[25:] != digest.digest() or source.read(1):
                raise ValueError("Backup checksum or length mismatch.")
            return
        if payload[24:25] != b"D":
            raise ValueError("Invalid backup frame type.")
        digest.update(payload[25:])
        target.write(payload[25:])
        count += 1

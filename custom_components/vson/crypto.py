"""
3DES (DESede) crypto used by the VSON "Xiaomei" / myvsoncloud mobile app.

Reverse-engineered from the Android app class ``e0.b`` (DESede/CBC/PKCS5Padding).

Facts recovered from the decompiled app:
  - Algorithm: DESede (Triple DES), mode CBC, padding PKCS5/PKCS7.
  - IV: the ASCII string "01234567" (8 bytes).
  - A Java ``DESedeKeySpec`` only uses the first 24 bytes of the key material,
    so every key string below is truncated to 24 bytes.

Three keys are used for three purposes:
  - HEADER : request headers (mpb, mpm, the constant mac/uuid/bh) AND the
             session token header, AND encrypted response fields (userId).
  - CRED   : login credentials (account name + password).
  - MISC   : a third key used by a few other endpoints (kept for completeness).

This module depends only on ``cryptography``, which Home Assistant already
ships, so the integration manifest needs no extra requirement. TripleDES moved
to the ``decrepit`` subpackage in cryptography 43; both locations are tried.

Validated: encrypting with HEADER reproduces the exact constant header values
baked into the app (bh="VSON", mac="m123456", uuid="u123456").
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.ciphers import Cipher, modes

try:  # cryptography >= 43 moved TripleDES to the "decrepit" subpackage.
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:  # pragma: no cover - older cryptography
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES

_IV = b"01234567"
_BLOCK = 8

KEY_HEADER = b"*|rX<xO7<6B}7PA])?dN8fgX}wOr'HQh"[:24]
KEY_CRED = b"cjm'|I-pE2[8=TM4[1PXRu,_xiE}j0X>px2_MqOSU=%;/HK<lB"[:24]
KEY_MISC = b"5JF8DDyfS3rrO$H*vf7oTtFYJTSfQ7XINDSMj3QD2omfzy%%gL"[:24]


def _pkcs5_pad(data: bytes) -> bytes:
    pad = _BLOCK - (len(data) % _BLOCK)
    return data + bytes([pad]) * pad


def _pkcs5_unpad(data: bytes) -> bytes:
    if not data or len(data) % _BLOCK != 0:
        raise ValueError("invalid ciphertext length")
    pad = data[-1]
    if pad < 1 or pad > _BLOCK:
        raise ValueError("invalid padding")
    return data[:-pad]


def _encrypt(plain: str, key: bytes) -> str:
    """Encrypt a UTF-8 string and return standard Base64."""
    enc = Cipher(TripleDES(key), modes.CBC(_IV)).encryptor()
    ct = enc.update(_pkcs5_pad(plain.encode("utf-8"))) + enc.finalize()
    return base64.b64encode(ct).decode("ascii")


def _decrypt(b64: str, key: bytes) -> str:
    """Decrypt a Base64 string back to its UTF-8 plaintext."""
    dec = Cipher(TripleDES(key), modes.CBC(_IV)).decryptor()
    pt = dec.update(base64.b64decode(b64)) + dec.finalize()
    return _pkcs5_unpad(pt).decode("utf-8")


# Public helpers, named after their purpose in the app.
def enc_header(plain: str) -> str:
    """Encrypt a value destined for a request header (app ``e0.b.e``)."""
    return _encrypt(plain, KEY_HEADER)


def enc_cred(plain: str) -> str:
    """Encrypt a login credential: account name or password (app ``e0.b.g``)."""
    return _encrypt(plain, KEY_CRED)


def dec_header(b64: str) -> str:
    """Decrypt a header-key value, e.g. the encrypted userId (app ``e0.b.a``)."""
    return _decrypt(b64, KEY_HEADER)


def dec_cred(b64: str) -> str:
    """Decrypt a credential value (app ``e0.b.c``)."""
    return _decrypt(b64, KEY_CRED)

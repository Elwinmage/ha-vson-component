"""Tests for the 3DES crypto, pinned against the app's own constants."""

from __future__ import annotations

from custom_components.vson import crypto


def test_header_constants_match_app():
    # These exact ciphertexts are hardcoded in the decompiled app.
    assert crypto.enc_header("VSON") == "JmnuSXWflZY="
    assert crypto.enc_header("m123456") == "S+T1TP5Nrak="
    assert crypto.enc_header("u123456") == "ScqUePab+h0="


def test_header_roundtrip():
    assert crypto.dec_header(crypto.enc_header("hello world")) == "hello world"


def test_cred_roundtrip():
    secret = "+33600000000"
    assert crypto.dec_cred(crypto.enc_cred(secret)) == secret


def test_userid_decrypts_with_header_key():
    # A real encrypted userId captured from a live login response.
    enc = "+ONmTPCVSlCGaJsR9llDunGHcZLY/xQJod4KAoLlCAfSqQbEf8wKaw=="
    assert crypto.dec_header(enc) == "a373c1f9a9b0466f9c01f8124cd57f2f"

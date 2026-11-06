"""Compatibility and rejection checks for the JWT/PDF dependency replacements."""

import base64
import hashlib
import hmac
import json
import time
import uuid

import jwt
import pytest
from fastapi import HTTPException
from jwt.exceptions import InvalidTokenError

from app.api.v1.resume import _extract_text_from_pdf
from app.config import settings
from app.services.auth.jwt_utils import decode_token


def _segment(value: dict) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )


def _legacy_token(kind: str, expires: int, algorithm: str = "HS256") -> str:
    # Build the pre-migration compact HS256 format independently of PyJWT.
    header = _segment({"alg": algorithm, "typ": "JWT"})
    payload = _segment({"sub": str(uuid.UUID(int=1)), "type": kind, "exp": expires})
    message = f"{header}.{payload}"
    signature = hmac.new(settings.secret_key.encode(), message.encode(), hashlib.sha256).digest()
    return message + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


@pytest.mark.parametrize("kind", ["access", "refresh", "password_reset"])
def test_existing_hs256_token_format_remains_valid(kind: str) -> None:
    token = _legacy_token(kind, int(time.time()) + 300)
    payload = decode_token(token)
    assert payload["type"] == kind
    assert payload["sub"] == str(uuid.UUID(int=1))


@pytest.mark.parametrize("attack", ["tampered", "unsigned", "expired", "wrong_algorithm"])
def test_invalid_tokens_are_rejected_after_dependency_change(attack: str) -> None:
    token = _legacy_token("access", int(time.time()) + 300)
    if attack == "tampered":
        header, _, signature = token.split(".")
        token = (
            header
            + "."
            + _segment({"sub": str(uuid.UUID(int=2)), "type": "access"})
            + "."
            + signature
        )
    elif attack == "unsigned":
        token = _segment({"alg": "none"}) + "." + token.split(".")[1] + "."
    elif attack == "expired":
        token = _legacy_token("access", int(time.time()) - 60)
    else:
        token = jwt.encode(
            {"sub": str(uuid.UUID(int=1)), "type": "access"}, settings.secret_key, algorithm="HS384"
        )
    with pytest.raises(InvalidTokenError):
        decode_token(token)


def _sample_pdf() -> bytes:
    # A real single-page PDF with independent xref offsets and an uncompressed
    # text stream, rather than a mock PdfReader or a new-library round trip.
    text = b"BT /F1 12 Tf 72 720 Td (Synthetic resume) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return (
        data
        + b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )


def test_resume_text_is_extracted_from_real_pdf() -> None:
    assert _extract_text_from_pdf(_sample_pdf()) == "Synthetic resume"


def test_malformed_pdf_keeps_unprocessable_entity_response() -> None:
    with pytest.raises(HTTPException) as error:
        _extract_text_from_pdf(b"not a PDF")
    assert error.value.status_code == 422

"""Card checkout checks. Full PAN/CVC are never stored."""

from __future__ import annotations

from datetime import date
from typing import NamedTuple

from fastapi import HTTPException


class CardInfo(NamedTuple):
    brand: str
    last4: str


def digits_only(value: str) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in digits_only(number)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def brand_of(number: str) -> str:
    n = digits_only(number)
    if n.startswith(("34", "37")):
        return "amex"
    if n.startswith("4"):
        return "visa"
    prefix4 = int(n[:4]) if len(n) >= 4 else 0
    if n.startswith(("51", "52", "53", "54", "55")) or 2221 <= prefix4 <= 2720:
        return "mastercard"
    if n.startswith(("6011", "65", "644", "645", "646", "647", "648", "649")):
        return "discover"
    return "card"


def parse_exp(value: str) -> tuple[int, int]:
    raw = (value or "").strip().replace(" ", "")
    if "/" in raw:
        left, _, right = raw.partition("/")
    elif len(digits_only(raw)) == 4:
        d = digits_only(raw)
        left, right = d[:2], d[2:]
    else:
        raise HTTPException(400, "Enter expiry as MM/YY.")
    try:
        month = int(left)
        year = int(right)
    except ValueError as exc:
        raise HTTPException(400, "Enter expiry as MM/YY.") from exc
    return month, year


def expiry_ok(month: int, year: int) -> bool:
    if month < 1 or month > 12:
        return False
    if year < 100:
        year += 2000
    today = date.today()
    if year < today.year or year > today.year + 20:
        return False
    if year == today.year and month < today.month:
        return False
    return True


def validate_card(name: str, number: str, exp_month: int, exp_year: int, cvc: str) -> CardInfo:
    holder = (name or "").strip()
    if len(holder) < 2 or not any(c.isalpha() for c in holder):
        raise HTTPException(400, "Enter the name on the card.")
    pan = digits_only(number)
    if len(set(pan)) == 1:
        raise HTTPException(400, "Enter a valid card number.")
    if not luhn_ok(pan):
        raise HTTPException(400, "That card number is not valid.")
    brand = brand_of(pan)
    expected_len = 15 if brand == "amex" else None
    if expected_len and len(pan) != expected_len:
        raise HTTPException(400, "That card number is not valid.")
    if not expiry_ok(exp_month, exp_year):
        raise HTTPException(400, "That card is expired or the expiry date is invalid.")
    sec = digits_only(cvc)
    need = 4 if brand == "amex" else 3
    if len(sec) != need:
        raise HTTPException(400, f"Enter the {need}-digit security code.")
    return CardInfo(brand=brand, last4=pan[-4:])

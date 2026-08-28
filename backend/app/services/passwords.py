"""Password strength rules shared by registration and reset."""

from __future__ import annotations

MIN_LENGTH = 8
MAX_LENGTH = 200

# Short list of passwords that clear a length check but are the first thing
# any credential-stuffing list tries.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "12345678", "123456789",
    "1234567890", "qwertyui", "qwerty123", "iloveyou", "princess", "sunshine",
    "football", "baseball", "welcome1", "welcome123", "admin123", "administrator",
    "letmein1", "abc12345", "trustno1", "starwars", "michael1", "superman",
    "monkey123", "dragon123", "changeme", "secret123", "testtest", "asdfasdf",
}


def password_problem(value: str) -> str | None:
    """Return a human-readable reason the password is unacceptable, else None."""
    if len(value) < MIN_LENGTH:
        return f"Password must be at least {MIN_LENGTH} characters."
    if len(value) > MAX_LENGTH:
        return f"Password must be under {MAX_LENGTH} characters."
    lowered = value.lower()
    if lowered in COMMON_PASSWORDS:
        return "That password is too common. Choose something less guessable."
    if not any(c.isalpha() for c in value):
        return "Password must contain at least one letter."
    if not any(c.isdigit() for c in value):
        return "Password must contain at least one number."
    if len(set(value)) < 4:
        return "Password must use at least 4 different characters."
    return None


def validate_password(value: str) -> str:
    problem = password_problem(value)
    if problem:
        raise ValueError(problem)
    return value

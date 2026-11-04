"""Passport MRZ (ICAO 9303, TD3: two lines of 44 characters) parsing with check digits.

OCR often confuses look-alike characters (O/0, I/1, S/5 …). Numeric fields are mapped to
digits, alphabetic fields to letters, and the alphanumeric passport number is repaired by
trying look-alike substitutions until its check digit matches.
"""

import itertools
import re
from dataclasses import asdict, dataclass, field
from datetime import date

LINE = 44
TO_DIGIT = str.maketrans({"O": "0", "Q": "0", "D": "0", "U": "0", "I": "1", "L": "1",
                          "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"})
TO_ALPHA = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"})
SWAP = {"0": "O", "O": "0", "1": "I", "I": "1", "5": "S", "S": "5", "8": "B", "B": "8",
        "2": "Z", "Z": "2", "6": "G", "G": "6"}


def check_digit(value: str) -> int:
    total = 0
    for i, ch in enumerate(value):
        if ch.isdigit():
            v = int(ch)
        elif "A" <= ch <= "Z":
            v = ord(ch) - 55
        else:  # "<" and anything unexpected
            v = 0
        total += v * (7, 3, 1)[i % 3]
    return total % 10


def _ok(value: str, digit: str) -> bool:
    return digit.isdigit() and check_digit(value) == int(digit)


def _date(yymmdd: str, *, birth: bool, today: date | None = None) -> date | None:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return None
    today = today or date.today()
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    year = 2000 + yy
    if birth and year > today.year:
        year -= 100
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


@dataclass
class MrzResult:
    surname: str
    given_name: str
    passport_number: str
    nationality: str
    issuing_country: str
    date_of_birth: date | None
    passport_expiry_date: date | None
    gender: str | None  # male / female / other
    checks: dict[str, bool] = field(default_factory=dict)
    raw: tuple[str, str] = ("", "")

    @property
    def valid(self) -> bool:
        return all(self.checks.values())

    def as_dict(self) -> dict:
        d = asdict(self)
        d["valid"] = self.valid
        d.pop("raw")
        return d


def _repair_number(number: str, digit: str) -> tuple[str, bool]:
    if _ok(number, digit):
        return number, True
    spots = [i for i, ch in enumerate(number) if ch in SWAP][:6]
    for combo in itertools.product((False, True), repeat=len(spots)):
        chars = list(number)
        for i, swap in zip(spots, combo, strict=True):
            if swap:
                chars[i] = SWAP[chars[i]]
        candidate = "".join(chars)
        if _ok(candidate, digit):
            return candidate, True
    return number, False


def find_lines(text: str) -> tuple[str, str] | None:
    """Pick the TD3 line pair out of noisy OCR text."""
    lines = []
    for raw in text.upper().splitlines():
        s = re.sub(r"[^A-Z0-9<]", "", raw.replace("«", "<").replace(" ", ""))
        if len(s) >= 30 and "<" in s:
            lines.append(s)
    for i in range(len(lines) - 1):
        first, second = lines[i], lines[i + 1]
        p = first.find("P")
        if p != -1 and p <= 2:
            first = first[p:]
            fit = lambda s: (s + "<" * LINE)[:LINE]  # noqa: E731
            return fit(first), fit(second)
    return None


def parse_td3(line1: str, line2: str, today: date | None = None) -> MrzResult:
    line1, line2 = line1.upper(), line2.upper()
    if len(line1) != LINE or len(line2) != LINE or line1[0] != "P":
        raise ValueError("not a TD3 passport MRZ")

    issuing = line1[2:5].translate(TO_ALPHA).replace("<", "")
    names = line1[5:].translate(TO_ALPHA)
    surname, _, given = names.partition("<<")
    surname = surname.replace("<", " ").strip()
    given = re.sub(r"<+", " ", given).strip()

    number, number_ok = _repair_number(line2[0:9], line2[9].translate(TO_DIGIT))
    nationality = line2[10:13].translate(TO_ALPHA).replace("<", "")
    dob_raw = line2[13:19].translate(TO_DIGIT)
    dob_cd = line2[19].translate(TO_DIGIT)
    sex = line2[20].translate(TO_ALPHA)
    exp_raw = line2[21:27].translate(TO_DIGIT)
    exp_cd = line2[27].translate(TO_DIGIT)
    personal = line2[28:42]
    personal_cd = line2[42].translate(TO_DIGIT)
    composite_cd = line2[43].translate(TO_DIGIT)
    composite = number + line2[9].translate(TO_DIGIT) + dob_raw + dob_cd + exp_raw + exp_cd
    composite += personal + personal_cd

    checks = {
        "passport_number": number_ok,
        "date_of_birth": _ok(dob_raw, dob_cd),
        "expiry_date": _ok(exp_raw, exp_cd),
        "composite": _ok(composite, composite_cd),
    }
    if personal.strip("<"):
        checks["personal_number"] = _ok(personal, personal_cd)
    return MrzResult(
        surname=surname,
        given_name=given,
        passport_number=number.replace("<", ""),
        nationality=nationality,
        issuing_country=issuing,
        date_of_birth=_date(dob_raw, birth=True, today=today),
        passport_expiry_date=_date(exp_raw, birth=False, today=today),
        gender={"M": "male", "F": "female"}.get(sex, "other" if sex == "X" else None),
        checks=checks,
        raw=(line1, line2),
    )

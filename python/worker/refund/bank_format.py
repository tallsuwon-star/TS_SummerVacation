"""한국 주요 은행 계좌번호 자릿수 구분(-) 규칙.

주의: 은행별 계좌번호 자릿수/구분 형식은 계좌 종류(개인/기업, 가상계좌 등)에
따라 다를 수 있어 아래 표는 "가장 흔한 개인 계좌 형식" 기준의 참고값이다.
실제 환불 이체에 쓰기 전에는 반드시 실제 계좌 화면(또는 은행 앱)과 대조해
한 번 더 확인해야 한다. 자릿수가 표에 없는 조합이면 억지로 끼워맞추지 않고
원본 숫자를 그대로 돌려주며 verified=False로 표시해, 화면에서 "확인 필요"로
구분할 수 있게 한다.
"""

# 은행명(사용자가 흔히 쓰는 표기) -> {전체 자릿수: [그룹별 자릿수, ...]}
BANK_DASH_PATTERNS: dict[str, dict[int, list[int]]] = {
    "신한은행": {12: [3, 3, 6], 14: [3, 3, 8]},
    "국민은행": {14: [6, 2, 6], 16: [6, 2, 2, 6]},
    "우리은행": {13: [4, 3, 6]},
    "하나은행": {14: [3, 6, 5]},
    "농협은행": {13: [3, 4, 4, 2]},
    "기업은행": {14: [3, 6, 2, 3]},
    "제일은행": {12: [3, 2, 6]},
    "카카오뱅크": {13: [4, 2, 7]},
    "케이뱅크": {12: [3, 2, 7]},
    "토스뱅크": {12: [4, 4, 4]},
    "우체국": {13: [6, 2, 5]},
    "새마을금고": {14: [4, 4, 6]},
    "신협": {13: [4, 3, 6]},
}


def format_account_number(raw_number: str, bank_name: str) -> dict:
    """계좌번호에 은행별 관행에 맞춰 '-'를 넣는다.

    반환: {"formatted": str, "verified": bool}
    verified=False면 해당 은행/자릿수 조합의 구분 규칙을 표에서 찾지 못해
    원본 숫자를 그대로 반환했다는 뜻이다.
    """
    digits = "".join(ch for ch in raw_number if ch.isdigit())
    bank = bank_name.strip()

    groups = BANK_DASH_PATTERNS.get(bank, {}).get(len(digits))
    if not groups:
        return {"formatted": digits, "verified": False}

    parts = []
    idx = 0
    for size in groups:
        parts.append(digits[idx : idx + size])
        idx += size
    return {"formatted": "-".join(parts), "verified": True}

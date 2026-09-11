import re

# 실제 사람 이름이 아닌 것으로 의심되는(가짜/테스트) 계정을 걸러내기 위한 키워드.
# 회원 이름/보카킹 이름 검증용. 이 판정은 100% 정확하다고 보장하지 않는 '의심
# 후보' 목록을 만드는 용도이며, 최종적으로는 사용자가 이름을 직접 확인해야 한다.
FAKE_NAME_KEYWORDS = ["테스트", "test", "보카", "팝업", "샘플", "sample"]
_KOREAN_NAME_RE = re.compile(r"^[가-힣]{2,5}$")


def is_suspicious_name(name: str, extra: str = "") -> bool:
    """실제 사람(회원) 이름이 아닌 것으로 의심되는 이름인지 판별한다.

    - FAKE_NAME_KEYWORDS 중 하나라도 이름(+보조 텍스트, 예: 영어이름/별명)에
      포함되면 의심.
    - 순수 한글 2~5자 형태가 아니면(영문/숫자/기호가 섞였거나 너무 짧거나 길면)
      의심. 회원 이름은 거의 항상 한글이라 이 규칙이 유효하다.
    """
    if not name:
        return False
    combined = f"{name} {extra}".lower()
    if any(keyword.lower() in combined for keyword in FAKE_NAME_KEYWORDS):
        return True
    if not _KOREAN_NAME_RE.match(name):
        return True
    return False


def is_suspicious_tutor_name(name: str) -> bool:
    """강사 이름이 테스트 계정으로 의심되는지 판별한다.

    강사 이름은 대부분 영어라서 회원 이름과 같은 '순수 한글' 규칙을 적용할 수
    없다. 대신 이름에 "test"라는 단어가 포함되어 있는지만 본다
    (예: "JAKETEST", "황병권test").
    """
    if not name:
        return False
    return "test" in name.lower()

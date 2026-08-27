"""electron/main/ipc/clipboard.js 가 `python3 clipboard.py` 형태로 직접 실행하는 스크립트.
stdin으로 받은 텍스트를 시스템 클립보드에 복사한다 (pyperclip 사용).
"""
import sys

import pyperclip


def main() -> None:
    text = sys.stdin.read()
    pyperclip.copy(text)


if __name__ == "__main__":
    main()

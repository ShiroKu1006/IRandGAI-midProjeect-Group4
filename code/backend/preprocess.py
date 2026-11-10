import re

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")

STOPWORDS = frozenset(
    """
    a an and are as at be but by for if in into is it of on or such that the
    their then there these they this to was were will with
    """.split()
)


def tokenize(text: str) -> list[str]:
    """把文字切成詞的列表（保留重複，順序與原文一致）。"""
    tokens = TOKEN_PATTERN.findall(text.lower())
    return [
        token
        for token in tokens
        if token not in STOPWORDS and token.strip("_")
    ]

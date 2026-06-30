# -*- coding: utf-8 -*-
"""vizstyle.py — matplotlib 한글 폰트/스타일 공통 설정 (모든 시각화에서 import)."""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")                       # 화면 없이 PNG 저장(headless)
import matplotlib.pyplot as plt
from matplotlib import font_manager

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT = os.path.join(_HERE, "..", "assets", "NanumGothic.ttf")


def use_korean():
    """나눔고딕을 matplotlib 기본 폰트로 등록한다."""
    if os.path.exists(_FONT):
        font_manager.fontManager.addfont(_FONT)
        name = font_manager.FontProperties(fname=_FONT).get_name()
        plt.rcParams["font.family"] = name
    plt.rcParams["axes.unicode_minus"] = False  # 음수 부호 깨짐 방지
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["savefig.facecolor"] = "white"


# 출시상태 → (한글 배지, 색)
RELEASE_BADGE = {
    "released":          ("출시", "#2e7d32"),
    "discontinued":      ("단종", "#6d4c41"),
    "rumored_unreleased": ("미출시·추정", "#c62828"),
    "announced":         ("발표", "#1565c0"),
}

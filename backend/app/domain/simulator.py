"""
石頭剪刀布遊戲模擬器

功能：
- 執行單回合遊戲邏輯
- 模擬多回合對戰
- 計算勝負平統計
- 支援歷史記錄和視窗限制

核心函數：
- play_round(): 執行單回合對戰
- simulate(): 模擬多回合對戰並統計結果

參數說明：
- s1, s2: 策略物件，需實作 next() 方法
- history: 歷史對戰記錄
- k_window: 歷史視窗大小，限制策略考慮的歷史長度
- rounds: 模擬回合數
"""

import numpy as np
from .strategies import beats

def play_round(s1, s2, history, k_window=None):
    h = history[-k_window:] if k_window else history
    m1 = s1.next(history=h)
    m2 = s2.next(history=[(b,a) for a,b in h])
    return m1, m2, beats(m1, m2)

def simulate(s1, s2, rounds=1000, k_window=None):
    history = []
    results = []
    for _ in range(rounds):
        m1, m2, r = play_round(s1, s2, history, k_window=k_window)
        history.append((m1, m2))
        results.append(r)
    arr = np.array(results)
    wins  = float((arr == 1).mean())
    losses= float((arr == -1).mean())
    draws = float((arr == 0).mean())
    return {"win": wins, "loss": losses, "draw": draws}

"""
石頭剪刀布策略定義和計算模組

功能：
- 定義所有靜態策略 (A-P)：固定、隨機、偏好等策略
- 定義動態策略 (X/Y/Z)：反應性策略
- 提供策略對戰結果計算
- 支援動態策略的迭代收斂計算
- 提供策略分佈解析和穩態計算

策略類型：
- 靜態策略 (A-P)：固定機率分佈的策略
- 動態策略 (X/Y/Z)：根據對手歷史反應的策略
  - X: 贏前一拳 (counter-winning)
  - Y: 輸前一拳 (counter-losing)  
  - Z: 跟前一拳 (copy-previous)

核心函數：
- calculate_matchup(): 計算兩個策略的對戰結果
- resolve_dist(): 解析動態策略的分佈
- iterate_dists(): 迭代計算動態策略的穩態分佈
- get_all_strategies(): 獲取所有策略
- get_strategy_names(): 獲取策略名稱對應
"""

import numpy as np
from enum import IntEnum
from typing import Dict, Tuple, Any

class Move(IntEnum):
    ROCK = 0; PAPER = 1; SCISSORS = 2

def beats(a: int, b: int) -> int:
    if a == b: return 0
    return 1 if (a - b) % 3 == 1 else -1

# --- 靜態策略 A-P ---
BASE_STRATEGIES = {
    'A': {'name': 'A (Pure Scissors)', 'rock': 0, 'paper': 0, 'scissors': 1},
    'B': {'name': 'B (Pure Rock)', 'rock': 1, 'paper': 0, 'scissors': 0},
    'C': {'name': 'C (Pure Paper)', 'rock': 0, 'paper': 1, 'scissors': 0},
    'D': {'name': 'D (Random)', 'rock': 0.333, 'paper': 0.333, 'scissors': 0.334},
    'E': {'name': 'E (Rock + Paper)', 'rock': 0.5, 'paper': 0.5, 'scissors': 0},
    'F': {'name': 'F (Rock + Scissors)', 'rock': 0.5, 'paper': 0, 'scissors': 0.5},
    'G': {'name': 'G (Paper + Scissors)', 'rock': 0, 'paper': 0.5, 'scissors': 0.5},
    'H': {'name': 'H (Rock-biased)', 'rock': 0.5, 'paper': 0.25, 'scissors': 0.25},
    'I': {'name': 'I (Paper-biased)', 'rock': 0.25, 'paper': 0.5, 'scissors': 0.25},
    'J': {'name': 'J (Scissors-biased)', 'rock': 0.25, 'paper': 0.25, 'scissors': 0.5},
    'K': {'name': 'K (Rock-primary, Paper-secondary)', 'rock': 0.5, 'paper': 0.333, 'scissors': 0.167},
    'L': {'name': 'L (Rock-primary, Scissors-secondary)', 'rock': 0.5, 'paper': 0.167, 'scissors': 0.333},
    'M': {'name': 'M (Paper-primary, Rock-secondary)', 'rock': 0.333, 'paper': 0.5, 'scissors': 0.167},
    'N': {'name': 'N (Paper-primary, Scissors-secondary)', 'rock': 0.167, 'paper': 0.5, 'scissors': 0.333},
    'O': {'name': 'O (Scissors-primary, Rock-secondary)', 'rock': 0.333, 'paper': 0.167, 'scissors': 0.5},
    'P': {'name': 'P (Scissors-primary, Paper-secondary)', 'rock': 0.167, 'paper': 0.333, 'scissors': 0.5},
}


# --- 動態策略 X/Y/Z ---
DYNAMIC_STRATEGIES = {
    'X': {'name': 'X', 'rule': 'Play the move that counters the opponent’s previous move(e.g., if the opponent favored Scissors in the last round, I will favor Rock; and so on).'},
    'Y': {'name': 'Y', 'rule': 'Play the move that is counter to the opponent’s previous move(e.g., if the opponent favored Scissors in the last round, I will favor Paper; and so on).'},
    'Z': {'name': 'Z', 'rule': 'Play the same move as the opponent’s previous move(e.g., if the opponent favored Scissors in the last round, I will also favor Scissors; and so on).'},
}


def resolve_dist(key: str, opp_dist: Dict[str, float]) -> Dict[str, float]:
    """解析動態策略的分佈"""
    if key in BASE_STRATEGIES:
        return BASE_STRATEGIES[key]
    
    if key == 'X':  # 贏前一拳
        return {
            'rock': opp_dist['scissors'],
            'paper': opp_dist['rock'],
            'scissors': opp_dist['paper']
        }
    elif key == 'Y':  # 輸前一拳
        return {
            'rock': opp_dist['paper'],
            'paper': opp_dist['scissors'],
            'scissors': opp_dist['rock']
        }
    elif key == 'Z':  # 跟前一拳
        return {
            'rock': opp_dist['rock'],
            'paper': opp_dist['paper'],
            'scissors': opp_dist['scissors']
        }
    
    return {'rock': 0, 'paper': 0, 'scissors': 0}

def iterate_dists(k1: str, k2: str, iters: int = 50) -> Dict[str, Dict[str, float]]:
    """迭代計算動態策略的穩態分佈"""
    # 初始上一拳分佈（均勻）
    s1 = {'rock': 1/3, 'paper': 1/3, 'scissors': 1/3}
    s2 = {'rock': 1/3, 'paper': 1/3, 'scissors': 1/3}

    for _ in range(iters):
        next1 = resolve_dist(k1, s2)
        next2 = resolve_dist(k2, s1)
        # 簡單阻尼以避免震盪（可調 0.5~0.8）
        alpha = 0.7
        s1 = {
            'rock': alpha * next1['rock'] + (1 - alpha) * s1['rock'],
            'paper': alpha * next1['paper'] + (1 - alpha) * s1['paper'],
            'scissors': alpha * next1['scissors'] + (1 - alpha) * s1['scissors'],
        }
        s2 = {
            'rock': alpha * next2['rock'] + (1 - alpha) * s2['rock'],
            'paper': alpha * next2['paper'] + (1 - alpha) * s2['paper'],
            'scissors': alpha * next2['scissors'] + (1 - alpha) * s2['scissors'],
        }
    
    return {'s1': s1, 's2': s2}

def calculate_matchup(k1: str, k2: str) -> Dict[str, float]:
    """計算兩個策略的對戰結果"""
    is_base1 = k1 in BASE_STRATEGIES
    is_base2 = k2 in BASE_STRATEGIES

    if is_base1 and is_base2:
        # 兩邊皆為靜態策略
        s1 = BASE_STRATEGIES[k1]
        s2 = BASE_STRATEGIES[k2]
    elif is_base1 and not is_base2:
        # 我方靜態、對手動態：對手根據我方分佈反應
        s1 = BASE_STRATEGIES[k1]
        s2 = resolve_dist(k2, s1)
    elif not is_base1 and is_base2:
        # 我方動態、對手靜態：我方根據對手分佈反應
        s2 = BASE_STRATEGIES[k2]
        s1 = resolve_dist(k1, s2)
    else:
        # 雙方皆動態：以穩態迭代求收斂分佈
        it = iterate_dists(k1, k2, 50)
        s1 = it['s1']
        s2 = it['s2']

    # 計算勝負平機率
    wins = 0.0
    losses = 0.0
    draws = 0.0
    
    wins += s1['rock'] * s2['scissors']  # 石頭勝剪刀
    wins += s1['paper'] * s2['rock']     # 布勝石頭
    wins += s1['scissors'] * s2['paper'] # 剪刀勝布
    
    losses += s1['rock'] * s2['paper']    # 石頭敗布
    losses += s1['paper'] * s2['scissors'] # 布敗剪刀
    losses += s1['scissors'] * s2['rock']  # 剪刀敗石頭
    
    draws += s1['rock'] * s2['rock']     # 石頭平石頭
    draws += s1['paper'] * s2['paper']   # 布平布
    draws += s1['scissors'] * s2['scissors'] # 剪刀平剪刀

    return {
        'wins': wins * 100,
        'losses': losses * 100,
        'draws': draws * 100
    }

def get_all_strategies() -> Dict[str, Dict[str, Any]]:
    """獲取所有策略"""
    return {**BASE_STRATEGIES, **DYNAMIC_STRATEGIES}

def get_strategy_names() -> Dict[str, str]:
    """獲取所有策略名稱"""
    strategies = get_all_strategies()
    return {key: value['name'] for key, value in strategies.items()}

# --- 原有的策略類別（保留以維持向後相容性） ---
class FixedStrategy:
    def __init__(self, move: int): 
        self.move = move
    def next(self, **kwargs): 
        return self.move

class RandomStrategy:
    def next(self, **kwargs): 
        return int(np.random.choice([0,1,2]))

class ReactiveStrategy:
    def __init__(self, on_win=0, on_loss=1, on_draw=2):
        self.on_win, self.on_loss, self.on_draw = on_win, on_loss, on_draw
    def next(self, history):
        if not history: 
            return int(np.random.choice([0,1,2]))
        my, opp = history[-1]
        res = beats(my, opp)
        return [self.on_draw, self.on_win, self.on_loss][res] if res in (-1,0,1) else 0

class FrequencyStrategy:
    def next(self, history):
        if not history: 
            return int(np.random.choice([0,1,2]))
        opp_moves = [opp for _, opp in history]
        counts = np.bincount(opp_moves, minlength=3)
        top = int(np.argmax(counts))
        return (top + 1) % 3

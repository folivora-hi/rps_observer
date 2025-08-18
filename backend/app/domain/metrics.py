"""
評估指標計算模組

功能：
- 計算各種損失函數和評估指標
- 提供標準化函數
- 支援策略預測評估

主要指標：
- Cross-Entropy Loss
- Brier Score
- EV Loss (Expected Value Loss)
- Union Loss (綜合損失)
- 標準化函數
"""

import numpy as np
from typing import Dict, List, Tuple, Any

def to_prob(dist: Dict[str, float]) -> Dict[str, float]:
    """將勝負平分佈轉換為機率"""
    total = dist['wins'] + dist['losses'] + dist['draws']
    if total == 0:
        return {'win': 0.33, 'draw': 0.34, 'loss': 0.33}
    return {
        'win': dist['wins'] / total,
        'draw': dist['draws'] / total,
        'loss': dist['losses'] / total
    }

def compute_cross_entropy_loss(true_dist: Dict[str, float], pred_dist: Dict[str, float]) -> float:
    """計算 Cross-Entropy Loss"""
    t_prob = to_prob(true_dist)
    p_prob = to_prob(pred_dist)
    
    # 避免 log(0) 的情況
    epsilon = 1e-12
    ce_loss = -(
        t_prob['win'] * np.log(p_prob['win'] + epsilon) +
        t_prob['draw'] * np.log(p_prob['draw'] + epsilon) +
        t_prob['loss'] * np.log(p_prob['loss'] + epsilon)
    )
    return float(ce_loss)

def compute_brier_score(true_dist: Dict[str, float], pred_dist: Dict[str, float]) -> float:
    """計算 Brier Score"""
    t_prob = to_prob(true_dist)
    p_prob = to_prob(pred_dist)
    
    brier = (
        (p_prob['win'] - t_prob['win']) ** 2 +
        (p_prob['draw'] - t_prob['draw']) ** 2 +
        (p_prob['loss'] - t_prob['loss']) ** 2
    )
    return float(brier)

def compute_ev(true_dist: Dict[str, float]) -> float:
    """計算期望值 (Expected Value)"""
    return (true_dist['wins'] - true_dist['losses']) / 100

def compute_ev_loss(true_dist: Dict[str, float], pred_dist: Dict[str, float]) -> float:
    """計算 EV Loss (Expected Value Loss)"""
    true_ev = compute_ev(true_dist)
    pred_ev = compute_ev(pred_dist)
    return float((true_ev - pred_ev) ** 2)

def normalize_loss(loss: float, all_losses: List[float]) -> float:
    """Min-Max 標準化損失值"""
    if not all_losses:
        return 0.5
    
    min_loss = min(all_losses)
    max_loss = max(all_losses)
    
    if max_loss == min_loss:
        return 0.5
    
    return (loss - min_loss) / (max_loss - min_loss)

def compute_union_loss(true_dist: Dict[str, float], pred_dist: Dict[str, float]) -> float:
    """計算 Union Loss (綜合損失)"""
    ce_loss = compute_cross_entropy_loss(true_dist, pred_dist)
    brier_loss = compute_brier_score(true_dist, pred_dist)
    ev_loss = compute_ev_loss(true_dist, pred_dist)
    
    # 綜合三種損失
    union_loss = (ce_loss + brier_loss + ev_loss) / 3
    return float(union_loss)

def compute_all_losses_for_matrix(
    matrix: Dict[str, Dict[str, Dict[str, float]]],
    pred_dist: Dict[str, float]
) -> Dict[str, List[float]]:
    """計算矩陣中所有組合的損失值"""
    all_ce_losses = []
    all_brier_losses = []
    all_ev_losses = []
    all_union_losses = []
    
    for s1 in matrix.keys():
        for s2 in matrix.keys():
            true_dist = matrix[s1][s2]
            
            # 計算各種損失
            ce_loss = compute_cross_entropy_loss(true_dist, pred_dist)
            brier_loss = compute_brier_score(true_dist, pred_dist)
            ev_loss = compute_ev_loss(true_dist, pred_dist)
            union_loss = compute_union_loss(true_dist, pred_dist)
            
            all_ce_losses.append(ce_loss)
            all_brier_losses.append(brier_loss)
            all_ev_losses.append(ev_loss)
            all_union_losses.append(union_loss)
    
    return {
        'ce_losses': all_ce_losses,
        'brier_losses': all_brier_losses,
        'ev_losses': all_ev_losses,
        'union_losses': all_union_losses
    }

def compute_normalized_losses(
    matrix: Dict[str, Dict[str, Dict[str, float]]],
    pred_dist: Dict[str, float]
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """計算矩陣中所有組合的標準化損失值"""
    all_losses = compute_all_losses_for_matrix(matrix, pred_dist)
    
    normalized_matrix = {}
    loss_idx = 0
    
    for s1 in matrix.keys():
        normalized_matrix[s1] = {}
        for s2 in matrix.keys():
            # 獲取當前組合的損失值
            ce_loss = all_losses['ce_losses'][loss_idx]
            brier_loss = all_losses['brier_losses'][loss_idx]
            ev_loss = all_losses['ev_losses'][loss_idx]
            union_loss = all_losses['union_losses'][loss_idx]
            
            # 標準化
            normalized_ce = normalize_loss(ce_loss, all_losses['ce_losses'])
            normalized_ev = ev_loss / 1.0  # 固定上界標準化
            normalized_union = normalize_loss(union_loss, all_losses['union_losses'])
            
            normalized_matrix[s1][s2] = {
                'ce_loss': ce_loss,
                'brier_loss': brier_loss,
                'ev_loss': ev_loss,
                'union_loss': union_loss,
                'normalized_ce': normalized_ce,
                'normalized_ev': normalized_ev,
                'normalized_union': normalized_union
            }
            
            loss_idx += 1
    
    return normalized_matrix

def evaluate_prediction(
    true_strategy1: str,
    true_strategy2: str,
    pred_strategy1: str,
    pred_strategy2: str,
    matrix: Dict[str, Dict[str, Dict[str, float]]]
) -> Dict[str, Any]:
    """評估預測結果"""
    # 獲取真實和預測的對戰結果
    true_dist = matrix[true_strategy1][true_strategy2]
    pred_dist = matrix[pred_strategy1][pred_strategy2]
    
    # 計算各種損失
    ce_loss = compute_cross_entropy_loss(true_dist, pred_dist)
    brier_loss = compute_brier_score(true_dist, pred_dist)
    ev_loss = compute_ev_loss(true_dist, pred_dist)
    union_loss = compute_union_loss(true_dist, pred_dist)
    
    # 計算標準化損失
    all_losses = compute_all_losses_for_matrix(matrix, pred_dist)
    normalized_ce = normalize_loss(ce_loss, all_losses['ce_losses'])
    normalized_ev = ev_loss / 1.0
    normalized_union = normalize_loss(union_loss, all_losses['union_losses'])
    
    return {
        'true_distribution': true_dist,
        'pred_distribution': pred_dist,
        'losses': {
            'ce_loss': ce_loss,
            'brier_loss': brier_loss,
            'ev_loss': ev_loss,
            'union_loss': union_loss
        },
        'normalized_losses': {
            'normalized_ce': normalized_ce,
            'normalized_ev': normalized_ev,
            'normalized_union': normalized_union
        }
    }

# Experiment Results

This directory contains result charts from the three strategy matchup experiments reported in the paper.

## Scenarios

| Folder | Player 1 (Strategy) | Player 2 (Strategy) | Description |
|--------|---------------------|---------------------|-------------|
| `DY/` | D — Random (uniform 1/3 each) | Y — Lose vs last move (dynamic) | Static uniform vs. reactive dynamic strategy |
| `HC/` | H — Rock-biased (0.5, 0.25, 0.25) | C — Pure Paper (0, 1, 0) | Biased static vs. its pure counter-strategy |
| `NG/` | N — Paper>Scissors (0.167, 0.5, 0.333) | G — Paper+Scissors (0, 0.5, 0.5) | Two similar mixed strategies with close distributions |

**Models evaluated**: `gpt-4o-mini`, `o3`, `claude-3-7-sonnet` (NG uses `claude` shorthand)

---

## Chart Types

Each scenario folder contains the following chart types:

### Per-model charts

| Filename pattern | Description |
|-----------------|-------------|
| `{S}_{model}_loss_comparison.png` | CE Loss, Brier Score, and EV Loss per round for one model |
| `{S}_{model}_normalized_loss_comparison.png` | Same losses, normalized |
| `{S}_{model}_union_loss.png` | Union Loss trend over rounds for one model |
| `{S}_{model}_normalized_union_loss.png` | Normalized Union Loss trend for one model |

### Cross-model comparison charts

| Filename pattern | Description |
|-----------------|-------------|
| `{S}_comparison_union_loss.png` | Union Loss across all models (main comparison figure) |
| `{S}_comparison_normalized_union_loss.png` | Normalized Union Loss across all models |
| `{S}_comparison_ce_loss.png` | Cross-Entropy Loss across all models |
| `{S}_comparison_normalized_ce_loss.png` | Normalized CE Loss across all models |
| `{S}_comparison_brier_loss.png` | Brier Score across all models |
| `{S}_comparison_ev_loss.png` | EV Loss across all models |
| `{S}_comparison_normalized_ev_loss.png` | Normalized EV Loss across all models |

Where `{S}` is the scenario code (`DY`, `HC`, or `NG`).

---

## Metric Definitions

| Metric | Formula | Range | Lower is better |
|--------|---------|-------|-----------------|
| Cross-Entropy (CE) | −∑ p_true · log(p_pred) | [0, ∞) | Yes |
| Brier Score | ∑ (p_true − p_pred)² | [0, 2] | Yes |
| EV Loss | (EV_true − EV_pred)² | [0, 1] | Yes |
| Union Loss | mean(CE, Brier, EV) | [0, ∞) | Yes |

Normalized values are relative min-max scaled across the full 19×19 strategy matrix (Union, CE) or fixed upper-bound normalized (EV, upper bound = 1.0).

---

## Reproducing Results

See the [main README](../../README.md#running-experiments) for instructions on using `scripts/observer_auto_test.py` to re-run experiments.

For methodology details, refer to the paper: [arXiv:2512.19210](https://arxiv.org/abs/2512.19210)

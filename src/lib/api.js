/**
 * 前端 API 客戶端模組
 * 
 * 功能：
 * - 提供與後端 API 的統一介面
 * - 處理 HTTP 請求和回應
 * - 提供錯誤處理和資料轉換
 * - 支援所有後端端點的調用
 * 
 * API 端點：
 * - simulate(): 策略模擬
 * - observerPredict(): 觀察者預測
 * - playerAct(): 玩家行動
 * - evaluate(): 評估指標
 * - getAllStrategies(): 獲取所有策略
 * - calculateStrategyMatchup(): 計算策略對戰
 * - calculateStrategyMatrix(): 計算策略矩陣
 * - evaluatePrediction(): 評估預測結果
 * - evaluateMatrix(): 評估完整矩陣
 * 
 * 使用方式：
 * import { simulate, observerPredict } from './lib/api.js';
 * const result = await simulate({ s1: {...}, s2: {...}, rounds: 1000 });
 */

export async function simulate(body) {
  const res = await fetch('/api/v1/simulate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function observerPredict(body) {
  const res = await fetch('/api/v1/observer/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function observerRun(body) {
  const res = await fetch('/api/v1/observer/run', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- 新增：以 SSE 串流逐輪獲取觀察結果 ---
export function openObserverStream({ true_strategy1, true_strategy2, rounds = 50, warmup_rounds = 10, k_window, model = 'deepseek' }) {
  const params = new URLSearchParams({
    true_strategy1,
    true_strategy2,
    rounds: String(rounds),
    warmup_rounds: String(warmup_rounds),
    model: String(model || ''),
  });
  if (k_window != null && k_window !== '') params.set('k_window', String(k_window));
  const url = `/api/v1/observer/stream?${params.toString()}`;
  return new EventSource(url);
}

export async function playerAct(body) {
  const res = await fetch('/api/v1/player/act', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function evaluate(body) {
  const res = await fetch('/api/v1/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- 新增：策略相關 API ---
export async function getAllStrategies() {
  const res = await fetch('/api/v1/strategies/all', {
    method: 'GET', headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function calculateStrategyMatchup(strategy1, strategy2) {
  const res = await fetch('/api/v1/strategies/matchup', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ strategy1, strategy2 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function calculateStrategyMatrix(predStrategy1, predStrategy2) {
  const res = await fetch('/api/v1/strategies/matrix', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pred_strategy1: predStrategy1, pred_strategy2: predStrategy2 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- 新增：評估相關 API ---
export async function evaluatePrediction(trueStrategy1, trueStrategy2, predStrategy1, predStrategy2) {
  const res = await fetch('/api/v1/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      true_strategy1: trueStrategy1,
      true_strategy2: trueStrategy2,
      pred_strategy1: predStrategy1,
      pred_strategy2: predStrategy2
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function evaluateMatrix(predStrategy1, predStrategy2) {
  const res = await fetch('/api/v1/evaluate/matrix', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pred_strategy1: predStrategy1,
      pred_strategy2: predStrategy2
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

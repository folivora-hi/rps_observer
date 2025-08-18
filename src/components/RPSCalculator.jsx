// src/components/RPSCalculator.jsx
import React, { useState, useMemo } from 'react';
import doraemonIcon from '../icon/doraemon.png';

const RPSCalculator = () => {
  // --- 静态策略 A–P ---
  const baseStrategies = {
    A: { name: 'A (纯剪刀)', rock: 0,   paper: 0,   scissors: 1   },
    B: { name: 'B (纯石头)', rock: 1,   paper: 0,   scissors: 0   },
    C: { name: 'C (纯布)',   rock: 0,   paper: 1,   scissors: 0   },
    D: { name: 'D (随机)',   rock: 0.333, paper: 0.333, scissors: 0.334 },
    E: { name: 'E (石头+布)', rock: 0.5, paper: 0.5,   scissors: 0   },
    F: { name: 'F (石头+剪刀)', rock: 0.5, paper: 0,     scissors: 0.5 },
    G: { name: 'G (布+剪刀)',   rock: 0,   paper: 0.5,   scissors: 0.5 },
    H: { name: 'H (偏爱石头)', rock: 0.5, paper: 0.25,  scissors: 0.25 },
    I: { name: 'I (偏爱布)',   rock: 0.25,paper: 0.5,   scissors: 0.25 },
    J: { name: 'J (偏爱剪刀)', rock: 0.25,paper: 0.25,  scissors: 0.5 },
    K: { name: 'K (石头主布次)', rock: 0.5, paper: 0.333, scissors: 0.167 },
    L: { name: 'L (石头主剪次)', rock: 0.5, paper: 0.167, scissors: 0.333 },
    M: { name: 'M (布主石次)',   rock: 0.333,paper: 0.5,   scissors: 0.167 },
    N: { name: 'N (布主剪次)',   rock: 0.167,paper: 0.5,   scissors: 0.333 },
    O: { name: 'O (剪主石次)',   rock: 0.333,paper: 0.167, scissors: 0.5   },
    P: { name: 'P (剪主布次)',   rock: 0.167,paper: 0.333, scissors: 0.5   },
  };

  // --- 动态策略 X/Y/Z ---
  const strategies = {
    ...baseStrategies,
    X: { name: 'X (赢前一拳)' },
    Y: { name: 'Y (输前一拳)' },
    Z: { name: 'Z (跟前一拳)' },
  };
  const keys = Object.keys(strategies);

  // --- State hooks ---
  const [infoKey, setInfoKey]   = useState(keys[0]);
  const [actualA, setActualA]   = useState(keys[0]);
  const [actualB, setActualB]   = useState(keys[1]);
  const [predA, setPredA]       = useState(keys[0]);
  const [predB, setPredB]       = useState(keys[1]);
  const [colorMode, setColorMode] = useState('winRate'); // 'winRate' | 'loss'

  // --- Helper functions ---
  const resolveDist = (key, oppDist) => {
    if (baseStrategies[key]) return baseStrategies[key];
    if (key === 'X') return { rock: oppDist.scissors, paper: oppDist.rock,   scissors: oppDist.paper };
    if (key === 'Y') return { rock: oppDist.paper,    paper: oppDist.scissors, scissors: oppDist.rock };
    if (key === 'Z') return { rock: oppDist.rock,     paper: oppDist.paper,    scissors: oppDist.scissors };
    return { rock: 0, paper: 0, scissors: 0 };
  };

  // 在 calculateMatchup 函数之前添加迭代函数
  const iterateDists = (k1, k2, iters = 50) => {
    // 初始上一拳分佈（均勻）
    let s1 = { rock: 1/3, paper: 1/3, scissors: 1/3 };
    let s2 = { rock: 1/3, paper: 1/3, scissors: 1/3 };

    for (let i = 0; i < iters; i++) {
      const next1 = resolveDist(k1, s2);
      const next2 = resolveDist(k2, s1);
      // 簡單阻尼以避免震盪（可調 0.5~0.8）
      const alpha = 0.7;
      s1 = {
        rock: alpha * next1.rock + (1 - alpha) * s1.rock,
        paper: alpha * next1.paper + (1 - alpha) * s1.paper,
        scissors: alpha * next1.scissors + (1 - alpha) * s1.scissors,
      };
      s2 = {
        rock: alpha * next2.rock + (1 - alpha) * s2.rock,
        paper: alpha * next2.paper + (1 - alpha) * s2.paper,
        scissors: alpha * next2.scissors + (1 - alpha) * s2.scissors,
      };
    }
    return { s1, s2 };
  };

  // 替換原本的 calculateMatchup 函数
  const calculateMatchup = (k1, k2) => {
    const isBase1 = !!baseStrategies[k1];
    const isBase2 = !!baseStrategies[k2];

    let s1, s2;

    if (isBase1 && isBase2) {
      // 原本邏輯：兩邊皆為靜態策略
      s1 = baseStrategies[k1];
      s2 = baseStrategies[k2];
    } else if (isBase1 && !isBase2) {
      // 我方靜態、對手動態：對手根據我方分佈反應
      s1 = baseStrategies[k1];
      s2 = resolveDist(k2, s1);
    } else if (!isBase1 && isBase2) {
      // 我方動態、對手靜態：我方根據對手分佈反應
      s2 = baseStrategies[k2];
      s1 = resolveDist(k1, s2);
    } else {
      // 雙方皆動態：以穩態迭代求收斂分佈
      const it = iterateDists(k1, k2, 50);
      s1 = it.s1;
      s2 = it.s2;
    }

    let wins=0, losses=0, draws=0;
    wins   += s1.rock     * s2.scissors;
    wins   += s1.scissors * s2.paper;
    wins   += s1.paper    * s2.rock;
    losses += s1.scissors * s2.rock;
    losses += s1.paper    * s2.scissors;
    losses += s1.rock     * s2.paper;
    draws  += s1.rock     * s2.rock;
    draws  += s1.paper    * s2.paper;
    draws  += s1.scissors * s2.scissors;

    return { wins:wins*100, losses:losses*100, draws:draws*100 };
  };

  // 優化 allMatchups 計算，只在必要時重新計算
  const allMatchups = useMemo(() => {
    const table = {};
    keys.forEach(k1 => {
      table[k1] = {};
      keys.forEach(k2 => {
        table[k1][k2] = calculateMatchup(k1, k2);
      });
    });
    return table;
  }, [keys]); // 只在 keys 改變時重新計算

  const toProb = d => ({ win:d.wins/100, draw:d.draws/100, loss:d.losses/100 });

  const computeCELoss = (t, p) =>
    - (t.win  * Math.log(p.win  + 1e-12)
      + t.draw * Math.log(p.draw + 1e-12)
      + t.loss * Math.log(p.loss + 1e-12));

  const computeBrier = (t, p) =>
    (p.win - t.win)**2 + (p.draw - t.draw)**2 + (p.loss - t.loss)**2;

  const computeEV    = d => (d.wins - d.losses)/100;
  const computeEVLoss = (tDist, pDist) =>
    Math.pow(computeEV(tDist) - computeEV(pDist), 2);

  // --- 新增：Min-Max 標準化函數 ---
  const normalizeLoss = (loss, allLosses) => {
    const min = Math.min(...allLosses);
    const max = Math.max(...allLosses);
    return max === min ? 0.5 : (loss - min) / (max - min);
  };

  // --- 新增：先計算當前的分佈與 loss ---
  const trueDist  = allMatchups[actualA][actualB];
  const predDist  = allMatchups[predA][predB];
  const tProb     = toProb(trueDist);
  const pProb     = toProb(predDist);

  const ceLoss    = computeCELoss(tProb, pProb);
  const brierLoss = computeBrier(tProb, pProb);
  const evLoss    = computeEVLoss(trueDist, predDist);
  const unionLoss = (ceLoss + brierLoss + evLoss) / 3;

  const allLosses = useMemo(() => {
    const losses = [];
    keys.forEach(k1 => {
      keys.forEach(k2 => {
        const t = allMatchups[k1][k2];
        const tP = toProb(t);
        const pP = pProb;
        const loss = (computeCELoss(tP, pP) + computeBrier(tP, pP) + computeEVLoss(t, predDist)) / 3;
        losses.push(loss);
      });
    });
    return losses;
  }, [allMatchups, pProb, predDist]);

  // --- 修改：EV Loss 固定上界標準化，Union Loss 繼續使用 min-max 標準化 ---
  const normalizedEVLoss = evLoss / 1.0; // 固定上界標準化
  const normalizedUnionLoss = normalizeLoss(unionLoss, allLosses); // 相對 min-max 標準化

  // --- 新增：Cross-Entropy Loss 的標準化（使用全矩陣 min-max） ---
  const allCELosses = useMemo(() => {
    const losses = [];
    keys.forEach(k1 => {
      keys.forEach(k2 => {
        const t = allMatchups[k1][k2];
        const tP = toProb(t);
        const pP = pProb;
        const celoss = computeCELoss(tP, pP);
        losses.push(celoss);
      });
    });
    return losses;
  }, [allMatchups, pProb]);

  const normalizedCELoss = normalizeLoss(ceLoss, allCELosses); // 相對 min-max 標準化

  const fmt = v => `${v.toFixed(1)}%`;

  return (
    <div className="max-w-7xl mx-auto p-6 bg-white shadow-lg rounded-lg">
      <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
        🪨📄✂️ Tom 4 AI Evaluation on Gaming
      </h1>
      <hr className="my-4 border-gray-300" />
      <p className="mt-2 text-sm text-gray-600">
        可查詢各角色的策略
      </p>


      {/* 策略说明 + 图标 */}
      <div className="mb-6 flex items-center space-x-4">
        <label className="block text-sm font-medium">Strategy Dictionary:</label>
        <select
          className="mt-1 rounded border-gray-300"
          value={infoKey}
          onChange={e => setInfoKey(e.target.value)}
        >
          {keys.map(k => <option key={k} value={k}>{k}</option>)}
        </select>
        <div className="flex items-center space-x-2">
          <img src={doraemonIcon} alt="Doraemon" className="w-8 h-8" />
          <span className="text-base font-medium">{strategies[infoKey].name}</span>
        </div>
      </div>
      <hr className="my-4 border-gray-300" />
      {/* Actual / Pred 选择 */}
      <p className="mt-2 text-sm text-gray-600">
        選擇 <strong>Actual A / Actual B</strong> 代表真實對戰的兩個策略，
        上方顯示的勝/敗/平與 Loss function 會依此組合計算。
        選擇 <strong>Pred A / Pred B</strong> 代表模型預測的兩個策略，
        在矩陣中 Loss 的計算會固定使用這個預測分佈與每格真實分佈做比較。
      </p>
      <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        {['Actual A','Actual B','Pred A','Pred B'].map((label, idx) => (
          <div key={label}>
            <label className="block text-sm font-medium">{label}</label>
            <select
              className="mt-1 block w-full rounded border-gray-300"
              value={[actualA, actualB, predA, predB][idx]}
              onChange={e =>
                [setActualA, setActualB, setPredA, setPredB][idx](e.target.value)
              }
            >
              {keys.map(k => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
        ))}
      </div>

      {/* 结果展示 - 新增 Cross-Entropy Loss 標準化顯示 */}
      <div className="mb-8 p-6 bg-gray-50 rounded-lg text-center">
        <p className="text-lg">
          Actual Win: <span className="font-semibold">{fmt(trueDist.wins)}</span> /
          Lose: <span className="font-semibold">{fmt(trueDist.losses)}</span> /
          Even: <span className="font-semibold">{fmt(trueDist.draws)}</span>
        </p>
        <p className="mt-2 text-lg">
          Pred Win: <span className="font-semibold">{fmt(predDist.wins)}</span> /
          Lose: <span className="font-semibold">{fmt(predDist.losses)}</span> /
          Even: <span className="font-semibold">{fmt(predDist.draws)}</span>
        </p>
        <div className="mt-4 space-y-1">
          <p>Cross‐Entropy Loss: <span className="font-semibold">{ceLoss.toFixed(4)}</span>
            <span className="text-sm text-gray-500"> (Normalized (relative): {normalizedCELoss.toFixed(4)})</span>
          </p>
          <p>Brier Score:          <span className="font-semibold">{brierLoss.toFixed(4)}</span></p>
          <p>EV Loss:              <span className="font-semibold">{evLoss.toFixed(4)}</span>
            <span className="text-sm text-gray-500"> (Normalized (fixed bound): {normalizedEVLoss.toFixed(4)})</span>
          </p>
          <p className="text-2xl font-bold text-red-600">
            Union Loss:           {unionLoss.toFixed(4)}
            <span className="text-sm text-gray-500"> (Normalized (relative): {normalizedUnionLoss.toFixed(4)})</span>
          </p>
        </div>
      </div>

      {/* 全矩阵对战 - 修改 loss 顯示，遵循標準化規則 */}
      <hr className="my-4 border-gray-300" />
      <p className="mb-4 text-sm text-gray-600">
        矩陣的每格顯示該行策略（真實 A）對該列策略（真實 B）的
        <strong>真實勝率 / 敗率 / 平率</strong>，
        以及與上方所選 <strong>Pred A / Pred B</strong> 預測分佈相比的
        <strong>Union Loss（已正規化）</strong>。
        前三行數值是純真實對戰結果，最後一行 N 值代表預測與真實的差距：
        值越低代表預測越接近真實。
      </p>
      <div className="mb-4 flex items-center space-x-4">
        <label className="text-sm font-medium">Color Mode:</label>
        <button
          className={`px-3 py-1 rounded ${colorMode === 'winRate' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setColorMode('winRate')}
        >
          Win Rate
        </button>
        <button
          className={`px-3 py-1 rounded ${colorMode === 'loss' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setColorMode('loss')}
        >
          Loss
        </button>
      </div>
      

      <div className="overflow-x-auto shadow-md rounded-lg">
        <table className="min-w-full divide-y divide-gray-200 table-auto text-sm">
          <thead className="sticky top-0 bg-blue-600">
            <tr>
              <th className="px-4 py-3 text-left text-white font-medium uppercase sticky left-0 bg-blue-600 z-10">
                Strategy
              </th>
              {keys.map(k => (
                <th key={k} className="px-4 py-3 text-center text-white font-medium uppercase">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {keys.map(k1 => (
              <tr key={k1} className="hover:bg-gray-100 even:bg-gray-50">
                <td className="px-4 py-2 font-semibold bg-gray-50 sticky left-0 z-10 whitespace-nowrap">
                  {k1}
                </td>
                {keys.map(k2 => {
                  const t    = allMatchups[k1][k2];
                  const tP   = toProb(t);
                  const pP   = pProb;
                  const loss = (computeCELoss(tP,pP)
                                + computeBrier(tP,pP)
                                + computeEVLoss(t,predDist)) / 3;
                  
                  // 修改：遵循標準化規則 - EV Loss 用固定上界，Union Loss 用相對 min-max
                  const evLossForCell = computeEVLoss(t, predDist);
                  const normalizedEVLossForCell = evLossForCell / 1.0; // 固定上界標準化
                  const normalizedUnionLossForCell = normalizeLoss(loss, allLosses); // 相對 min-max 標準化
                  
                  // 根據模式選擇顏色
                  let hue, bg;
                  if (colorMode === 'winRate') {
                    hue = Math.round((t.wins/100) * 120); // 勝率高越綠
                    bg = `hsl(${hue},70%,90%)`;
                  } else {
                    hue = Math.round((1 - normalizedUnionLossForCell) * 120); // Loss 低越綠
                    bg = `hsl(${hue},70%,90%)`;
                  }
                  
                  return (
                    <td
                      key={k2}
                      className="px-4 py-2 text-center whitespace-nowrap"
                      style={{ background: bg }}
                    >
                      <div className="font-semibold text-xs">{fmt(t.wins)}</div>
                      <div className="text-gray-600 text-xs">{fmt(t.losses)}</div>
                      <div className="text-gray-500 text-xs">{fmt(t.draws)}</div>
                      {/* 修改：顯示 Union Loss 的標準化值（相對 min-max） */}
                      <div className="mt-1 text-[9px] text-blue-600 font-bold">
                        N {normalizedUnionLossForCell.toFixed(2)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RPSCalculator;

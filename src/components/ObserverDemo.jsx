import React, { useState, useEffect } from 'react';
import { 
  getAllStrategies, 
  observerPredict, 
  evaluatePrediction,
  evaluateMatrix 
} from '../lib/api.js';

const ObserverDemo = () => {
  // 狀態管理
  const [strategies, setStrategies] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 策略選擇（保留於狀態以維持既有流程，但不再顯示預測下拉）
  const [trueStrategy1, setTrueStrategy1] = useState('A');
  const [trueStrategy2, setTrueStrategy2] = useState('B');
  const [predStrategy1, setPredStrategy1] = useState('A');
  const [predStrategy2, setPredStrategy2] = useState('B');
  
  // 新增：實驗設定（真實使用者、模型、最多對戰輪次）
  const availableUsers = ['使用者A', '使用者B', '使用者C'];
  const availableModels = ['gpt-4o-mini', 'claude-3-5-sonnet', 'deepseek-chat'];
  const [selectedUser, setSelectedUser] = useState(availableUsers[0]);
  const [selectedModel, setSelectedModel] = useState(availableModels[0]);
  const [maxRounds, setMaxRounds] = useState(50);
  
  // 結果
  const [observerResult, setObserverResult] = useState(null);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [matrixResult, setMatrixResult] = useState(null);

  // 載入策略列表
  useEffect(() => {
    const loadStrategies = async () => {
      try {
        const result = await getAllStrategies();
        setStrategies(result.strategies);
      } catch (err) {
        setError('載入策略失敗: ' + err.message);
      }
    };
    loadStrategies();
  }, []);

  // Observer 預測
  const handleObserverPredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await observerPredict({
        strategy1: predStrategy1,
        strategy2: predStrategy2,
        // 新增資訊：真實使用者、模型與輪次（後端可忽略以保持相容）
        user: selectedUser,
        model: selectedModel,
        max_rounds: Number(maxRounds)
      });
      setObserverResult(result);
      
      // 檢查是否使用備用邏輯
      if (result.reasoning && result.reasoning.includes('備用')) {
        setError('⚠️ 注意: 目前使用備用預測邏輯，未連接真正的 LLM API');
      }
    } catch (err) {
      setError('Observer 預測失敗: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 評估預測
  const handleEvaluatePrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await evaluatePrediction(
        trueStrategy1, 
        trueStrategy2, 
        predStrategy1, 
        predStrategy2
      );
      setEvaluationResult(result);
    } catch (err) {
      setError('評估失敗: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 評估矩陣
  const handleEvaluateMatrix = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await evaluateMatrix(predStrategy1, predStrategy2);
      setMatrixResult(result);
    } catch (err) {
      setError('矩陣評估失敗: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const strategyOptions = Object.entries(strategies).map(([code, name]) => (
    <option key={code} value={code}>{code}: {name}</option>
  ));

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-lg rounded-lg">
      <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
        🧠 Observer 實驗系統
      </h1>
      
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* 實驗設定區域（改版） */}
      <div className="mb-8 p-6 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">實驗設定</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">真實使用者</label>
            <select
              className="w-full p-2 border rounded"
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
            >
              {availableUsers.map(u => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">使用模型</label>
            <select
              className="w-full p-2 border rounded"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {availableModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">最多對戰輪次</label>
            <input
              type="number"
              min="1"
              className="w-full p-2 border rounded"
              value={maxRounds}
              onChange={(e) => setMaxRounds(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* 策略選擇區域（只保留真實策略，預測策略下拉已移除） */}
      <div className="mb-8 p-6 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">真實策略選擇</h2>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">真實策略 1</label>
            <select
              className="w-full p-2 border rounded"
              value={trueStrategy1}
              onChange={(e) => setTrueStrategy1(e.target.value)}
            >
              {strategyOptions}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">真實策略 2</label>
            <select
              className="w-full p-2 border rounded"
              value={trueStrategy2}
              onChange={(e) => setTrueStrategy2(e.target.value)}
            >
              {strategyOptions}
            </select>
          </div>
        </div>
      </div>

      {/* 操作按鈕 */}
      <div className="mb-8 flex flex-wrap gap-4">
        <button
          onClick={handleObserverPredict}
          disabled={loading}
          className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? '預測中...' : '🧠 Observer 預測'}
        </button>
        
        <button
          onClick={handleEvaluatePrediction}
          disabled={loading}
          className="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          {loading ? '評估中...' : '📊 評估預測'}
        </button>
        
        <button
          onClick={handleEvaluateMatrix}
          disabled={loading}
          className="px-6 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
        >
          {loading ? '計算中...' : '🔢 評估矩陣'}
        </button>
      </div>

      {/* Observer 預測結果 */}
      {observerResult && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded">
          <h3 className="text-lg font-semibold mb-2">🧠 Observer 預測結果</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>勝率: {(observerResult.win * 100).toFixed(1)}%</div>
            <div>敗率: {(observerResult.loss * 100).toFixed(1)}%</div>
            <div>平率: {(observerResult.draw * 100).toFixed(1)}%</div>
            <div>信心度: {(observerResult.confidence * 100).toFixed(1)}%</div>
          </div>
          {observerResult.reasoning && (
            <div className="mt-2 text-sm text-gray-600">
              推理: {observerResult.reasoning}
            </div>
          )}
        </div>
      )}

      {/* 評估結果 */}
      {evaluationResult && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded">
          <h3 className="text-lg font-semibold mb-2">📊 評估結果</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">真實分佈</h4>
              <div className="text-sm">
                <div>勝: {evaluationResult.true_distribution.wins.toFixed(1)}%</div>
                <div>敗: {evaluationResult.true_distribution.losses.toFixed(1)}%</div>
                <div>平: {evaluationResult.true_distribution.draws.toFixed(1)}%</div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">預測分佈</h4>
              <div className="text-sm">
                <div>勝: {evaluationResult.pred_distribution.wins.toFixed(1)}%</div>
                <div>敗: {evaluationResult.pred_distribution.losses.toFixed(1)}%</div>
                <div>平: {evaluationResult.pred_distribution.draws.toFixed(1)}%</div>
              </div>
            </div>
          </div>
          
          <div className="mt-4">
            <h4 className="font-medium mb-2">損失函數</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>CE Loss: {evaluationResult.losses.ce_loss.toFixed(4)}</div>
              <div>Brier: {evaluationResult.losses.brier_loss.toFixed(4)}</div>
              <div>EV Loss: {evaluationResult.losses.ev_loss.toFixed(4)}</div>
              <div className="font-semibold text-red-600">
                Union Loss: {evaluationResult.losses.union_loss.toFixed(4)}
              </div>
            </div>
          </div>
          
          <div className="mt-4">
            <h4 className="font-medium mb-2">標準化損失</h4>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>標準化 CE: {evaluationResult.normalized_losses.normalized_ce.toFixed(4)}</div>
              <div>標準化 EV: {evaluationResult.normalized_losses.normalized_ev.toFixed(4)}</div>
              <div className="font-semibold text-red-600">
                標準化 Union: {evaluationResult.normalized_losses.normalized_union.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 矩陣結果預覽 */}
      {matrixResult && (
        <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded">
          <h3 className="text-lg font-semibold mb-2">🔢 矩陣評估結果</h3>
          <div className="text-sm">
            <div>策略數量: {Object.keys(matrixResult.strategy_names).length}</div>
            <div>預測分佈: 勝{(matrixResult.pred_distribution.wins * 100).toFixed(1)}% / 
                         敗{(matrixResult.pred_distribution.losses * 100).toFixed(1)}% / 
                         平{(matrixResult.pred_distribution.draws * 100).toFixed(1)}%</div>
            <div className="mt-2 text-gray-600">
              已計算完整矩陣和標準化損失，可用於進一步分析
            </div>
          </div>
        </div>
      )}

      {/* 使用說明 */}
      <div className="mt-8 p-4 bg-gray-100 rounded">
        <h3 className="font-semibold mb-2">📖 使用說明</h3>
        <div className="text-sm text-gray-700 space-y-1">
          <div>1. 選擇真實使用者、要使用的模型與最多對戰輪次</div>
          <div>2. 選擇真實對戰的兩個策略（Actual A/B）</div>
          <div>3. 點擊「Observer 預測」讓模型參與並預測對戰結果</div>
          <div>4. 點擊「評估預測」計算損失函數</div>
          <div>5. 點擊「評估矩陣」計算完整矩陣的標準化損失</div>
        </div>
      </div>
    </div>
  );
};

export default ObserverDemo;
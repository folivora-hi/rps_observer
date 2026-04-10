#!/usr/bin/env python3
"""
測試 observer API 的正規化 union_loss 功能
"""

import requests
import json

def test_normalized_loss_direct():
    """直接測試正規化 loss 計算"""
    url = "http://127.0.0.1:8002/api/v1/evaluate"
    
    payload = {
        "true_strategy1": "A",
        "true_strategy2": "B",
        "pred_strategy1": "C", 
        "pred_strategy2": "D"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ evaluate API 測試成功")
            
            # 檢查是否有正規化的 loss
            normalized_losses = data.get('normalized_losses', {})
            if 'normalized_union' in normalized_losses:
                print(f"✅ 找到正規化 union_loss: {normalized_losses['normalized_union']}")
                print(f"   原始 union_loss: {data.get('losses', {}).get('union_loss')}")
            else:
                print("❌ 未找到正規化 union_loss")
                
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

def test_observer_run():
    """測試 observer_run API"""
    url = "http://127.0.0.1:8002/api/v1/observer/run"
    
    payload = {
        "true_strategy1": "A",
        "true_strategy2": "B", 
        "rounds": 20,
        "warmup_rounds": 10,
        "model": "4o-mini"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ observer_run API 測試成功")
            
            # 檢查是否有 normalized_union_loss
            has_normalized = False
            has_guesses = False
            
            for round_record in data.get('per_round', []):
                if round_record.get('guess_s1') is not None or round_record.get('guess_s2') is not None:
                    has_guesses = True
                    print(f"  輪次 {round_record['round']}: guess_s1={round_record.get('guess_s1')}, guess_s2={round_record.get('guess_s2')}")
                
                if round_record.get('normalized_union_loss') is not None:
                    has_normalized = True
                    print(f"  輪次 {round_record['round']}: union_loss={round_record.get('union_loss')}, normalized_union_loss={round_record.get('normalized_union_loss')}")
            
            if has_guesses:
                print("✅ 找到策略猜測")
            else:
                print("❌ 沒有找到策略猜測（可能是 LLM API 問題）")
                
            if has_normalized:
                print("✅ 正規化 union_loss 已成功加入")
            else:
                print("❌ 未找到正規化 union_loss")
                
            # 檢查 trend 中是否有 last_normalized
            trend = data.get('trend', {})
            if 'last_normalized' in trend:
                print(f"✅ trend 中包含 last_normalized: {trend['last_normalized']}")
            else:
                print("❌ trend 中沒有 last_normalized")
                
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

def test_observer_run_simple():
    """測試 observer_run API 使用更簡單的模型"""
    url = "http://127.0.0.1:8002/api/v1/observer/run"
    
    payload = {
        "true_strategy1": "A",
        "true_strategy2": "B", 
        "rounds": 15,
        "warmup_rounds": 5,
        "model": "fallback"  # 使用 fallback 模型
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ observer_run API 測試成功")
            
            # 檢查是否有 normalized_union_loss
            has_normalized = False
            has_guesses = False
            
            for round_record in data.get('per_round', []):
                if round_record.get('guess_s1') is not None or round_record.get('guess_s2') is not None:
                    has_guesses = True
                    print(f"  輪次 {round_record['round']}: guess_s1={round_record.get('guess_s1')}, guess_s2={round_record.get('guess_s2')}")
                
                if round_record.get('normalized_union_loss') is not None:
                    has_normalized = True
                    print(f"  輪次 {round_record['round']}: union_loss={round_record.get('union_loss')}, normalized_union_loss={round_record.get('normalized_union_loss')}")
            
            if has_guesses:
                print("✅ 找到策略猜測")
            else:
                print("❌ 沒有找到策略猜測")
                
            if has_normalized:
                print("✅ 正規化 union_loss 已成功加入")
            else:
                print("❌ 未找到正規化 union_loss")
                
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

def test_observer_run_no_llm():
    """測試 observer_run API 不使用 LLM（warmup = rounds）"""
    url = "http://127.0.0.1:8002/api/v1/observer/run"
    
    payload = {
        "true_strategy1": "A",
        "true_strategy2": "B", 
        "rounds": 10,
        "warmup_rounds": 10,  # warmup = rounds，不會調用 LLM
        "model": "4o-mini"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ observer_run API (無 LLM) 測試成功")
            
            # 檢查結構是否正確
            per_round = data.get('per_round', [])
            print(f"  總輪數: {len(per_round)}")
            
            # 檢查是否所有輪次都有 normalized_union_loss 欄位（應該都是 null）
            all_have_field = all('normalized_union_loss' in round_record for round_record in per_round)
            if all_have_field:
                print("✅ 所有輪次都包含 normalized_union_loss 欄位")
            else:
                print("❌ 部分輪次缺少 normalized_union_loss 欄位")
            
            # 檢查 trend 中是否有 last_normalized 欄位
            trend = data.get('trend', {})
            has_last_normalized_field = 'last_normalized' in trend or len(trend) == 0
            if has_last_normalized_field:
                print("✅ trend 結構正確")
            else:
                print("❌ trend 缺少 last_normalized 欄位")
                
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    print("=== 測試正規化 loss 計算 ===")
    test_normalized_loss_direct()
    print("\n=== 測試 observer API (無 LLM) ===")
    test_observer_run_no_llm()
    print("\n=== 測試 observer API (fallback 模型) ===")
    test_observer_run_simple()
    print("\n=== 測試 observer API (4o-mini 模型) ===")
    test_observer_run()

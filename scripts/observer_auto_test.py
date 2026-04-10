import argparse
import itertools
import os
import datetime
import httpx
from openpyxl import Workbook
import signal
import sys


DEFAULT_SERVER = "http://localhost:5173"


def ensure_out_dir(path: str):
    os.makedirs(path, exist_ok=True)


DETAIL_HEADERS = [
    "timestamp",
    "combo_id",
    "repeat_idx",
    "round",
    "move1_label",
    "move2_label",
    "result",
    "guess_s1",
    "guess_s2",
    "union_loss",
    "normalized_union_loss",
    "ce_loss",
    "brier_loss",
    "ev_loss",
    "normalized_ce_loss",
    "normalized_ev_loss",
    "delta",
    "confidence",
    "reasoning",
    "model",
    "true_strategy1",
    "true_strategy2",
    "rounds",
    "warmup_rounds",
    "history_limit",
    "reasoning_interval",
]


def make_workbook():
    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "run_summary"
    ws_detail = wb.create_sheet("per_run_detail")

    ws_summary.append([
        "timestamp",
        "combo_id",
        "repeat_idx",
        "model",
        "true_strategy1",
        "true_strategy2",
        "rounds",
        "warmup_rounds",
        "history_limit",
        "reasoning_interval",
        "final_guess_s1",
        "final_guess_s2",
        "last_loss",
        "last_normalized_loss",  # 新增：最後一輪的正規化 loss
        "min_loss",
        "trend_avg5",
    ])

    ws_detail.append(DETAIL_HEADERS)

    return wb, ws_summary, ws_detail


def parse_args():
    p = argparse.ArgumentParser(
        description="Observer auto test: cartesian product over hyperparams; sequential API calls; Excel export."
    )
    p.add_argument("--server", required=True, help="API server base URL, e.g., http://localhost:8000")
    p.add_argument("--true-s1", action="append", dest="true_s1_list", required=True, help="Strategy code(s) for player 1; repeatable")
    p.add_argument("--true-s2", action="append", dest="true_s2_list", required=True, help="Strategy code(s) for player 2; repeatable")
    p.add_argument("--rounds", type=int, action="append", dest="rounds_list", required=True, help="Rounds values; repeatable")
    p.add_argument("--warmup", type=int, action="append", dest="warmup_list", required=True, help="Warmup rounds values; repeatable")
    p.add_argument(
        "--history-limit",
        type=int,
        action="append",
        dest="history_limit_list",
        required=True,
        help="History limit values; repeatable (use -1 for None)",
    )
    p.add_argument(
        "--reasoning-interval",
        type=int,
        action="append",
        dest="reasoning_interval_list",
        required=True,
        help="Reasoning interval values; repeatable",
    )
    p.add_argument("--model", action="append", dest="model_list", required=True, help="Model(s), e.g., deepseek, 4o-mini; repeatable")
    p.add_argument("--repeats", type=int, required=True, help="Repeat count per combination")
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument("--save-interval", type=int, default=10, help="Save interval (every N combinations, default: 10)")
    return p.parse_args()


class TestRunner:
    def __init__(self, args):
        self.args = args
        self.current_model = None
        self.current_wb = None
        self.current_ws_summary = None
        self.current_ws_detail = None
        self.current_out_path = None
        self.combo_id = 0
        self.total_combinations = 0
        self.completed_combinations = 0
        
        # 計算總組合數
        self.total_combinations = (
            len(args.true_s1_list) * 
            len(args.true_s2_list) * 
            len(args.rounds_list) * 
            len(args.warmup_list) * 
            len(args.history_limit_list) * 
            len(args.reasoning_interval_list) * 
            len(args.model_list) * 
            args.repeats
        )
        
        # 設置信號處理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        print(f"\n收到中斷信號 {signum}，正在保存當前進度...")
        if self.current_wb and self.current_out_path:
            self.save_current_workbook()
            print(f"已保存當前進度到: {self.current_out_path}")
        print(f"已完成 {self.completed_combinations}/{self.total_combinations} 組合 ({self.completed_combinations/self.total_combinations*100:.1f}%)")
        sys.exit(0)
    
    def save_current_workbook(self):
        """保存當前的工作簿"""
        if self.current_wb and self.current_out_path:
            self.current_wb.save(self.current_out_path)
            print(f"已保存 {self.current_model} 的進度: {self.current_out_path}")
    
    def start_new_model(self, model):
        """開始新的 model 測試"""
        if self.current_wb:
            self.save_current_workbook()
        
        self.current_model = model
        self.current_wb, self.current_ws_summary, self.current_ws_detail = make_workbook()
        self.combo_id = 0
        
        # 生成檔案名
        strategy_combo = f"{''.join(self.args.true_s1_list)}{''.join(self.args.true_s2_list)}"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_out_path = os.path.join(self.args.out_dir, f"{ts}_{model}-{strategy_combo}.xlsx")
        
        print(f"開始執行 model: {model}")
    
    def add_result(self, data, payload, repeat_idx):
        """添加測試結果到工作簿"""
        final_guess = data.get("final_guess", {}) or {}
        trend = data.get("trend", {}) or {}
        fg1 = final_guess.get("s1") or ""
        fg2 = final_guess.get("s2") or ""

        now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_ws_summary.append([
            now_ts,
            self.combo_id,
            repeat_idx,
            self.current_model,
            payload["true_strategy1"],
            payload["true_strategy2"],
            payload["rounds"],
            payload["warmup_rounds"],
            payload["history_limit"],
            payload["reasoning_interval"],
            fg1,
            fg2,
            trend.get("last"),
            trend.get("last_normalized"), # 新增：最後一輪的正規化 loss
            trend.get("min"),
            trend.get("avg_5"),
        ])

        per_round = data.get("per_round", []) or []

        def move_label(code):
            if code == 0:
                return "rock"
            if code == 1:
                return "paper"
            if code == 2:
                return "scissors"
            return ""

        for rr in per_round:
            m1 = rr.get("move1")
            m2 = rr.get("move2")
            row = [
                now_ts,
                self.combo_id,
                repeat_idx,
                rr.get("round"),
                move_label(m1),
                move_label(m2),
                rr.get("result"),
                rr.get("guess_s1"),
                rr.get("guess_s2"),
                rr.get("union_loss"),
                rr.get("normalized_union_loss"), # 新增：正規化的 union_loss
                rr.get("ce_loss"),
                rr.get("brier_loss"),
                rr.get("ev_loss"),
                rr.get("normalized_ce_loss"),
                # 不寫入 normalized_brier_loss
                rr.get("normalized_ev_loss"),
                rr.get("delta"),
                rr.get("confidence"),
                (rr.get("reasoning") or ""),
                self.current_model,
                payload["true_strategy1"],
                payload["true_strategy2"],
                payload["rounds"],
                payload["warmup_rounds"],
                payload["history_limit"],
                payload["reasoning_interval"],
            ]
            # 安全檢查：避免欄位錯位
            if len(row) != len(DETAIL_HEADERS):
                print("[WARN] detail row length mismatch:", len(row), "expected:", len(DETAIL_HEADERS))
                print("row=", row)
            self.current_ws_detail.append(row)
        
        self.completed_combinations += 1
        
        # 定期保存
        if self.combo_id % self.args.save_interval == 0:
            self.save_current_workbook()
            print(f"進度: {self.completed_combinations}/{self.total_combinations} ({self.completed_combinations/self.total_combinations*100:.1f}%)")


def main():
    args = parse_args()
    ensure_out_dir(args.out_dir)

    # 使用明確指定的參數，無預設值
    true_s1_list = args.true_s1_list
    true_s2_list = args.true_s2_list
    rounds_list = args.rounds_list
    warmup_list = args.warmup_list
    # 處理 history_limit: -1 表示 None
    history_limit_list = [None if x == -1 else x for x in args.history_limit_list]
    reasoning_interval_list = args.reasoning_interval_list
    model_list = args.model_list

    runner = TestRunner(args)

    with httpx.Client(base_url=args.server, timeout=None) as client:
        # 按 model 分組執行
        for model in model_list:
            runner.start_new_model(model)
            
            # 對當前 model 執行所有參數組合
            for (
                true_s1,
                true_s2,
                rounds,
                warmup,
                hist_lim,
                reason_int,
            ) in itertools.product(
                true_s1_list,
                true_s2_list,
                rounds_list,
                warmup_list,
                history_limit_list,
                reasoning_interval_list,
            ):
                runner.combo_id += 1
                for repeat_idx in range(1, args.repeats + 1):
                    payload = {
                        "true_strategy1": true_s1,
                        "true_strategy2": true_s2,
                        "rounds": int(rounds),
                        "warmup_rounds": int(warmup),
                        "history_limit": hist_lim,
                        "reasoning_interval": int(reason_int),
                        "model": model,
                    }

                    resp = client.post("/api/v1/observer/run", json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                    runner.add_result(data, payload, repeat_idx)
            
            # 保存當前 model 的結果
            runner.save_current_workbook()
            print(f"已完成 {model} 的所有測試")
            print(f"{model} 總組合數: {runner.combo_id}")
            print(f"{model} 總執行次數: {runner.combo_id * args.repeats}")
            print("-" * 50)

    print("所有測試完成！")


if __name__ == "__main__":
    main()



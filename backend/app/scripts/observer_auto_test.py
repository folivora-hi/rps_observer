import argparse
import itertools
import os
import datetime
import httpx
from openpyxl import Workbook


DEFAULT_SERVER = "http://localhost:5173"


def ensure_out_dir(path: str):
    os.makedirs(path, exist_ok=True)


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
        "min_loss",
        "trend_avg5",
    ])

    ws_detail.append([
        "timestamp",
        "combo_id",
        "repeat_idx",
        "round",
        "move1",
        "move2",
        "result",
        "guess_s1",
        "guess_s2",
        "union_loss",
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
    ])

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
    p.add_argument("--filename-prefix", required=True, help="Filename prefix")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_out_dir(args.out_dir)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(args.out_dir, f"{ts}_{args.filename_prefix}.xlsx")

    # 使用明確指定的參數，無預設值
    true_s1_list = args.true_s1_list
    true_s2_list = args.true_s2_list
    rounds_list = args.rounds_list
    warmup_list = args.warmup_list
    # 處理 history_limit: -1 表示 None
    history_limit_list = [None if x == -1 else x for x in args.history_limit_list]
    reasoning_interval_list = args.reasoning_interval_list
    model_list = args.model_list

    wb, ws_summary, ws_detail = make_workbook()
    combo_id = 0

    with httpx.Client(base_url=args.server, timeout=None) as client:
        for (
            true_s1,
            true_s2,
            rounds,
            warmup,
            hist_lim,
            reason_int,
            model,
        ) in itertools.product(
            true_s1_list,
            true_s2_list,
            rounds_list,
            warmup_list,
            history_limit_list,
            reasoning_interval_list,
            model_list,
        ):
            combo_id += 1
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

                resp = client.post("/observer/run", json=payload)
                resp.raise_for_status()
                data = resp.json()

                final_guess = data.get("final_guess", {}) or {}
                trend = data.get("trend", {}) or {}
                fg1 = final_guess.get("s1") or ""
                fg2 = final_guess.get("s2") or ""

                now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws_summary.append([
                    now_ts,
                    combo_id,
                    repeat_idx,
                    model,
                    true_s1,
                    true_s2,
                    rounds,
                    warmup,
                    payload["history_limit"],
                    payload["reasoning_interval"],
                    fg1,
                    fg2,
                    trend.get("last"),
                    trend.get("min"),
                    trend.get("avg_5"),
                ])

                per_round = data.get("per_round", []) or []
                for rr in per_round:
                    ws_detail.append([
                        now_ts,
                        combo_id,
                        repeat_idx,
                        rr.get("round"),
                        rr.get("move1"),
                        rr.get("move2"),
                        rr.get("result"),
                        rr.get("guess_s1"),
                        rr.get("guess_s2"),
                        rr.get("union_loss"),
                        rr.get("delta"),
                        rr.get("confidence"),
                        rr.get("reasoning"),
                        model,
                        true_s1,
                        true_s2,
                        rounds,
                        warmup,
                        payload["history_limit"],
                        payload["reasoning_interval"],
                    ])

    wb.save(out_path)
    print(f"Saved: {out_path}")
    print(f"Total combinations: {combo_id}")
    print(f"Total runs: {combo_id * args.repeats}")


if __name__ == "__main__":
    main()



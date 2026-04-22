import os
import csv
import time
import random
import numpy as np
import pandas as pd
from run_energy_model import run_case

DEMAND = "B11002460"
SCENARIOS = [1, 2, 3, 4, 5]

BASE_EV = 15
BASE_BASIC = 1.0
BASE_ENERGY = 1.0

EV_LIST = [5, 10, 15, 20, 25]
PRICE_FACTOR = [0.8, 0.9, 1.1, 1.2]

N_REP = 100
SEED0 = 314
OUT = "output_sensitivity"

os.makedirs(OUT, exist_ok=True)

RAW_PATH  = os.path.join(OUT, f"sensitivity_summary_raw_{N_REP}rep.csv")
FAIL_PATH = os.path.join(OUT, f"sensitivity_fail_log_{N_REP}rep.csv")
MEAN_PATH = os.path.join(OUT, f"sensitivity_summary_mean_{N_REP}rep.csv")
FINAL_PATH = os.path.join(OUT, "sensitivity_summary.csv")  # assessment が読む

# ----------------------------
# 乱数シード固定（repごとに変える）
# ----------------------------
def set_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)

# ----------------------------
# 進捗表示
# ----------------------------
runs_per_scenario = 1 + len(EV_LIST) + len(PRICE_FACTOR) + len(PRICE_FACTOR)
TOTAL_RUNS = len(SCENARIOS) * N_REP * runs_per_scenario
run_count = 0
t0 = time.time()

def progress(msg: str, every: int = 10):
    """every回に1回だけ表示（printが重いので）"""
    global run_count
    if run_count % every == 0 or run_count == TOTAL_RUNS:
        pct = 100.0 * run_count / TOTAL_RUNS
        elapsed = time.time() - t0
        print(f"[{run_count}/{TOTAL_RUNS} | {pct:5.1f}% | {elapsed:7.1f}s] {msg}")

# ----------------------------
# CSVスキーマ（列の揺れ対策）
# run_caseの出力キーが多少増減しても、ここにある列は安定して書ける
# ----------------------------
RAW_FIELDS = [
    # model summary core (あなたのCSV例に合わせて)
    "name", "Num_EV", "TripEnergy", "Demand", "RES", "SolarCapacity", "BESS_BatteryCapacity",
    "BuyPowerEnergy", "ContractPower", "Cost", "EnergyCost", "ContractCost",
    "Is_opt_solarcapacity", "Is_opt_BESS", "TripType", "ChargeType", "ControlRatio",

    # run_case add-ons
    "DemandName", "Scenario", "NumEV", "NumICE", "BasicFactor", "EnergyFactor",
    "Ref_PVScenario", "DefaultSolar_kW_used",

    # runner meta
    "Sensitivity", "Rep", "Seed",
    # optional test values (入ってても入ってなくてもOK)
    "EV_test", "BasicFactor_test", "EnergyFactor_test",
]

FAIL_FIELDS = ["DemandName", "Scenario", "Sensitivity", "Rep", "Seed", "EV_test", "BasicFactor_test", "EnergyFactor_test", "Reason"]

# ----------------------------
# 逐次書き込みの準備（既存ファイルがあれば上書き）
# ----------------------------
for p in [RAW_PATH, FAIL_PATH]:
    if os.path.exists(p):
        os.remove(p)

raw_f = open(RAW_PATH, "w", newline="", encoding="utf-8")
fail_f = open(FAIL_PATH, "w", newline="", encoding="utf-8")

raw_writer = csv.DictWriter(raw_f, fieldnames=RAW_FIELDS, extrasaction="ignore")
fail_writer = csv.DictWriter(fail_f, fieldnames=FAIL_FIELDS, extrasaction="ignore")

raw_writer.writeheader()
fail_writer.writeheader()

def write_fail(sc, sens, rep, seed, extra=None, reason="run_case returned None"):
    row = {
        "DemandName": DEMAND,
        "Scenario": sc,
        "Sensitivity": sens,
        "Rep": rep,
        "Seed": seed,
        "Reason": reason,
    }
    if extra:
        row.update(extra)
    fail_writer.writerow(row)

def write_raw(res, sens, sc, rep, seed, extra=None):
    row = dict(res)  # summary dict
    row["DemandName"] = row.get("DemandName", DEMAND)
    row["Scenario"] = row.get("Scenario", sc)
    row["Sensitivity"] = sens
    row["Rep"] = rep
    row["Seed"] = seed
    if extra:
        row.update(extra)

    # 欠けている列は空欄でOK（DictWriterが自動で埋める）
    raw_writer.writerow(row)

# ----------------------------
# メインループ（逐次保存）
# ----------------------------
try:
    for sc in SCENARIOS:

        # ---- Base ----
        for rep in range(N_REP):
            run_count += 1
            seed = SEED0 + 100000 * sc + rep
            progress(f"Scenario={sc} Sens=Base rep={rep+1}/{N_REP} seed={seed}")

            set_seeds(seed)
            base = run_case(DEMAND, BASE_EV, sc, BASE_BASIC, BASE_ENERGY, OutputFolder=OUT)
            if base is None:
                write_fail(sc, "Base", rep, seed)
            else:
                write_raw(base, "Base", sc, rep, seed)

            if run_count % 50 == 0:
                raw_f.flush()
                fail_f.flush()

        # ---- EV sensitivity ----
        for ev in EV_LIST:
            for rep in range(N_REP):
                run_count += 1
                seed = SEED0 + 100000 * sc + 1000 * ev + rep
                progress(f"Scenario={sc} Sens=NumEV(ev={ev}) rep={rep+1}/{N_REP} seed={seed}")

                set_seeds(seed)
                r = run_case(DEMAND, ev, sc, BASE_BASIC, BASE_ENERGY, OutputFolder=OUT)
                extra = {"EV_test": ev}
                if r is None:
                    write_fail(sc, "NumEV", rep, seed, extra=extra)
                else:
                    write_raw(r, "NumEV", sc, rep, seed, extra=extra)

                if run_count % 50 == 0:
                    raw_f.flush()
                    fail_f.flush()

        # ---- Basic price ----
        for bf in PRICE_FACTOR:
            for rep in range(N_REP):
                run_count += 1
                seed = SEED0 + 100000 * sc + int(bf * 1000) + rep
                progress(f"Scenario={sc} Sens=BasicPrice(bf={bf}) rep={rep+1}/{N_REP} seed={seed}")

                set_seeds(seed)
                r = run_case(DEMAND, BASE_EV, sc, bf, BASE_ENERGY, OutputFolder=OUT)
                extra = {"BasicFactor_test": bf}
                if r is None:
                    write_fail(sc, "BasicPrice", rep, seed, extra=extra)
                else:
                    write_raw(r, "BasicPrice", sc, rep, seed, extra=extra)

                if run_count % 50 == 0:
                    raw_f.flush()
                    fail_f.flush()

        # ---- Energy price ----
        for ef in PRICE_FACTOR:
            for rep in range(N_REP):
                run_count += 1
                seed = SEED0 + 100000 * sc + int(ef * 1000) + rep + 50000
                progress(f"Scenario={sc} Sens=EnergyPrice(ef={ef}) rep={rep+1}/{N_REP} seed={seed}")

                set_seeds(seed)
                r = run_case(DEMAND, BASE_EV, sc, BASE_BASIC, ef, OutputFolder=OUT)
                extra = {"EnergyFactor_test": ef}
                if r is None:
                    write_fail(sc, "EnergyPrice", rep, seed, extra=extra)
                else:
                    write_raw(r, "EnergyPrice", sc, rep, seed, extra=extra)

                if run_count % 50 == 0:
                    raw_f.flush()
                    fail_f.flush()

finally:
    raw_f.flush()
    fail_f.flush()
    raw_f.close()
    fail_f.close()

print("Raw logging DONE:", RAW_PATH)

# ----------------------------
# 最後に平均化して sensitivity_summary.csv を作る（assessment入力用）
# ----------------------------
df_raw = pd.read_csv(RAW_PATH)

# group keys（存在する列だけ）
group_key_candidates = ["DemandName", "Scenario", "Sensitivity", "NumEV", "NumICE", "BasicFactor", "EnergyFactor"]
group_keys = [k for k in group_key_candidates if k in df_raw.columns]

# 数値列抽出
numeric_cols = df_raw.select_dtypes(include=[np.number]).columns.tolist()

# Rep/Seedは集計対象から外す
numeric_cols = [c for c in numeric_cols if c not in ["Rep", "Seed"]]

# group key列も数値に含まれてしまうので除外（重複防止）
numeric_cols = [c for c in numeric_cols if c not in group_keys]

df_mean = df_raw.groupby(group_keys, dropna=False)[numeric_cols].mean().reset_index()
df_std  = df_raw.groupby(group_keys, dropna=False)[numeric_cols].std(ddof=1).reset_index()
df_std = df_std.rename(columns={c: f"{c}_std" for c in numeric_cols})

df_avg = pd.merge(df_mean, df_std, on=group_keys, how="left")

df_avg.to_csv(MEAN_PATH, index=False)
df_avg.to_csv(FINAL_PATH, index=False)

print("Avg DONE:", FINAL_PATH)
print("raw :", df_raw.shape, "avg :", df_avg.shape)
print("fails:", sum(1 for _ in open(FAIL_PATH, encoding="utf-8")) - 1)  # header除く
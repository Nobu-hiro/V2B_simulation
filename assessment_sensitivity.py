import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ================================
# Settings
# ================================
INPUT_CSV = "output_sensitivity/sensitivity_summary.csv"
OUTPUT_DIR = "assessment_sensitivity_output"

# Case1-5 only
NUM_VEHICLE = 15
SYSTEM_LIFETIME = 20  # year (PV lifetime = 20 想定)

TRIPDIST_TAC = 7930.9   # TAC用（現状維持）
TRIPDIST_DPB = 10000.0  # DPBP用（旧スクリプトに合わせる）

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== prices (10k JPY units; 後半スクリプトと同じ) =====
Price_ini_Solarpanel = 25.5   # 10kJPY/kW
Price_om_Solarpanel  = 0.5    # 10kJPY/kW/year
lifetime_Solarpanel  = 20     # year

Price_init_V2H = 33           # 10kJPY/unit
Price_om_V2H   = 0.6          # 10kJPY/unit/year
lifetime_V2H   = 10           # year

Price_init_NC = 15            # 10kJPY/unit
Price_om_NC   = 0.1           # 10kJPY/unit/year
lifetime_NC   = 10            # year

Price_init_BESS = 18.7        # 10kJPY/kWh
Price_om_BESS   = 0.47        # 10kJPY/kWh/year
lifetime_BESS   = 10          # year

# ================================
# Load data
# ================================
DF = pd.read_csv(INPUT_CSV)

# ================================
# Case definition (Scenario = Case)
# ================================
scenario_to_case = {1: "Case1", 2: "Case2", 3: "Case3", 4: "Case4", 5: "Case5"}
DF["Case"] = DF["Scenario"].map(scenario_to_case)

CASE_ORDER = ["Case1", "Case2", "Case3", "Case4", "Case5"]
DF["Case"] = pd.Categorical(DF["Case"], categories=CASE_ORDER, ordered=True)

# ================================
# Cost functions
# ================================
def trvl_ICE(num_ice, AnnualTripDistance=7930.9):
    """Fuel cost for ICE (10kJPY/year)"""
    Cost_Gasoline = 175      # JPY/L
    Fuel_Efficiency = 22     # km/L
    return Cost_Gasoline * AnnualTripDistance / Fuel_Efficiency / 1e4 * num_ice
# これに置き換え
def get_NumICE(row):
    return row["NumICE"]

def capex_components(row):
    """Initial CAPEX components (10kJPY)"""
    NumEV = row["NumEV"]
    ControlRatio = row["ControlRatio"]
    PVini   = Price_ini_Solarpanel * row["SolarCapacity"]
    V2Hini  = Price_init_V2H * NumEV * ControlRatio
    NCini   = Price_init_NC * NumEV * (1 - ControlRatio)
    BESSini = Price_init_BESS * row["BESS_BatteryCapacity"]
    return PVini, V2Hini, NCini, BESSini

def calc_Cini(row):
    """Initial CAPEX total (10kJPY)"""
    return sum(capex_components(row))

def calc_om_annual(row):
    """Annual O&M (10kJPY/year)"""
    NumEV = row["NumEV"]
    ControlRatio = row["ControlRatio"]
    PVom   = Price_om_Solarpanel * row["SolarCapacity"]
    V2Hom  = Price_om_V2H * NumEV * ControlRatio
    NCom   = Price_om_NC * NumEV * (1 - ControlRatio)
    BESSom = Price_om_BESS * row["BESS_BatteryCapacity"]
    return PVom + V2Hom + NCom + BESSom

def calc_capex_annualized(row):
    """Annualized CAPEX by component lifetime (10kJPY/year)"""
    PVini, V2Hini, NCini, BESSini = capex_components(row)
    return (PVini / lifetime_Solarpanel
            + V2Hini / lifetime_V2H
            + NCini / lifetime_NC
            + BESSini / lifetime_BESS)

def evaluate_TAC(row):
    """
    TAC (10kJPY/year) = Electricity + Fuel + Annualized CAPEX + O&M
    ※後半スクリプトの AnnualCost に相当
    """
    electricity_cost = row["EnergyCost"] + row["ContractCost"]
    fuel_cost = trvl_ICE(get_NumICE(row))
    return electricity_cost + fuel_cost + calc_capex_annualized(row) + calc_om_annual(row)

def evaluate_operational_cost(row):
    """
    DPBP用の年間運用コスト：
    Electricity + Fuel(10000km) + O&M
    """
    electricity_cost = row["EnergyCost"] + row["ContractCost"]
    fuel_cost = trvl_ICE(get_NumICE(row), TRIPDIST_DPB)  # ★ここだけ10000
    return electricity_cost + fuel_cost + calc_om_annual(row)
# ================================
# Prepare columns
# ================================

# NumICE はCSVにあるならそれを優先（無ければ scenario から補完）
if "NumICE" not in DF.columns:
    DF["NumICE"] = DF.apply(get_NumICE, axis=1)
else:
    # NaNだけ補完したい場合
    DF["NumICE"] = DF["NumICE"].fillna(DF.apply(get_NumICE, axis=1))

# ここで Num_vehicle を作る（NumICE を潰さないことが重要）
DF["Num_vehicle"] = DF["NumICE"] + DF["NumEV"]

DF["FuelCost"] = DF["NumICE"].apply(lambda n: trvl_ICE(n, TRIPDIST_TAC))
DF["Cini"] = DF.apply(calc_Cini, axis=1)
DF["CAPEX_annualized"] = DF.apply(calc_capex_annualized, axis=1)
DF["OM_annual"] = DF.apply(calc_om_annual, axis=1)
DF["OpCost"] = DF.apply(evaluate_operational_cost, axis=1)
DF["TAC"] = DF.apply(evaluate_TAC, axis=1)

# ================================
# Base (PBP reference = Case1 Base)
# ================================
BASE_CASE = "Case1"
BASE_ROW = DF[(DF["Case"] == BASE_CASE) & (DF["Sensitivity"] == "Base")].iloc[0]

# ================================
# Annual savings for DPBP (運用費差分)
# ================================
def calc_Rannual(row):
    if row["Case"] == BASE_CASE:
        return 0.0
    # 年間の純便益（運用コスト削減）= Base運用費 - 対象運用費
    return float(BASE_ROW["OpCost"] - row["OpCost"])

DF["Rannual"] = DF.apply(calc_Rannual, axis=1)

def fmt_pct_from_factor(factor, prefix, base=1.0, tol=1e-9, decimals=0):
    """
    factor: 0.8, 1.0, 1.2 など
    prefix: "BasicPrice", "EnergyPrice" など
    """
    if pd.isna(factor):
        return f"{prefix}: NA"
    if abs(factor - base) <= tol:
        return f"{prefix}: Base"
    pct = (factor / base - 1.0) * 100
    # 符号付きで丸め
    if decimals == 0:
        return f"{prefix}: {pct:+.0f}%"
    else:
        return f"{prefix}: {pct:+.{decimals}f}%"

# ================================
# Investment PV with replacements (DPBP用)
# ================================
def pv_investment_with_replacements(row, r):
    """
    システム期間(SYSTEM_LIFETIME)内の投資支出をPV化（10kJPY, present value）
    寿命10年の機器は10年目に更新が発生するとみなす（20年なら2回分）
    """
    PVini, V2Hini, NCini, BESSini = capex_components(row)

    pv = 0.0

    # PV: lifetime 20 -> t=0 1回のみ（SYSTEM_LIFETIME=20の想定）
    pv += PVini  # year 0

    # V2H/NC/BESS: lifetime 10 -> year0 + year10（SYSTEM_LIFETIME=20の場合）
    # 一般化：t = 0, L, 2L,... < SYSTEM_LIFETIME
    def add_replacements(cost, life):
        nonlocal pv
        t = 0
        while t < SYSTEM_LIFETIME:
            pv += cost / ((1 + r) ** t)
            t += life

    add_replacements(V2Hini, lifetime_V2H)
    add_replacements(NCini, lifetime_NC)
    add_replacements(BESSini, lifetime_BESS)

    return pv

def pv_investment_diff(row, r):
    """Baseとの差分（PV of investment）"""
    return pv_investment_with_replacements(row, r) - pv_investment_with_replacements(BASE_ROW, r)

# ================================
# Discounted Payback Period
# ================================
def DPBP_continuous(C, R, r=0.0, max_year=20):
    """
    年次で割引累積しつつ、最後の年で線形補間して“小数年”を返すDPBP
    r=0なら C/R とほぼ一致（厳密）
    """
    if C <= 0 or R <= 0:
        return np.nan

    cum_prev = 0.0
    for t in range(1, max_year + 1):
        cash = R / ((1 + r) ** t)
        cum = cum_prev + cash
        if cum >= C:
            # t年目の途中で回収 → その年の何割で回収したか
            frac = (C - cum_prev) / cash  # 0〜1
            return (t - 1) + frac
        cum_prev = cum
    return np.nan

def DPBP(Cini_PV, Rannual, r, max_year=20):
    """
    Cini_PV: 投資差分の現在価値（10kJPY）
    Rannual: 年間便益（10kJPY/year）
    """
    if Cini_PV <= 0 or Rannual <= 0:
        return 0.0

    cum = 0.0
    for t in range(1, max_year + 1):
        cum += Rannual / ((1 + r) ** t)
        if cum >= Cini_PV:
            return t
    return np.nan

# ================================
# Discount rate sensitivity (Base only)
# ================================
discount_rates = [0.0, 0.03, 0.05]
BASE_DF = DF[DF["Sensitivity"] == "Base"].copy()

records = []
for r in discount_rates:
    tmp = BASE_DF.copy()
    tmp["Sensitivity"] = "DiscountRate"
    tmp["DiscountRate"] = r

    # DPBP用：寿命更新を考慮した投資PV差分を計算
    tmp["Cini_PVdiff"] = tmp.apply(lambda x: pv_investment_diff(x, r), axis=1)

    tmp["DPBP"] = tmp.apply(
        lambda x: DPBP_continuous(x["Cini_PVdiff"], x["Rannual"], r),
        axis=1
    )
    records.append(tmp)

DF_DPB = pd.concat(records, ignore_index=True)

# ================================
# Unit conversion: 10kJPY -> JPY
# ================================
TO_JPY = 10_000  # 1万円 = 10,000円

# DF側（TACなど）
for col in ["FuelCost", "Cini", "CAPEX_annualized", "OM_annual", "OpCost", "Rannual", "TAC"]:
    if col in DF.columns:
        DF[col + "_JPY"] = DF[col] * TO_JPY

# DF_DPB側（投資PV差分やDPBP用の入力）
for col in ["Cini_PVdiff", "Rannual"]:
    if col in DF_DPB.columns:
        DF_DPB[col + "_JPY"] = DF_DPB[col] * TO_JPY

import matplotlib.ticker as ticker

# ================================
# Plot units: kJPY (thousand JPY)
# ================================
TO_kJPY = 1_000

# すでに *_JPY を持っている想定（無ければ後述）
for col in ["FuelCost", "Cini", "CAPEX_annualized", "OM_annual", "OpCost", "Rannual", "TAC"]:
    if col + "_JPY" in DF.columns:
        DF[col + "_kJPY"] = DF[col + "_JPY"] / TO_kJPY

if "Cini_PVdiff_JPY" in DF_DPB.columns:
    DF_DPB["Cini_PVdiff_kJPY"] = DF_DPB["Cini_PVdiff_JPY"] / TO_kJPY
DF["Num_vehicle"] = DF["NumICE"] + DF["NumEV"]

# ================================
# Save tables
# ================================
DF.to_csv(os.path.join(OUTPUT_DIR, "TAC_sensitivity_summary.csv"), index=False)
DF_DPB.to_csv(os.path.join(OUTPUT_DIR, "DPBP_sensitivity_summary.csv"), index=False)

# ================================
# Visualization helpers
# ================================
def plot_TAC_sensitivity(df, sens, value_col, cmap, title, fname, label_func=None):
    sub = df[df["Sensitivity"] == sens].copy()
    if sub.empty:
        print(f"[WARN] No data for Sensitivity={sens}")
        return

    # Case順を固定
    case_order = ["Case1", "Case2", "Case3", "Case4", "Case5"]
    x = np.arange(len(case_order))

    # レベル（Num_vehicleなど）を数値としてソート
    levels = sub[value_col].dropna().unique().tolist()
    levels = sorted(levels, key=lambda v: float(v))
    colors = cmap(np.linspace(0.3, 1.0, len(levels)))

    fig, ax = plt.subplots(figsize=(12, 4), constrained_layout=True)

    for lv, c in zip(levels, colors):
        # 同じ (Case, lv) が複数ある可能性があるので平均で1点にまとめる
        tmp = sub[sub[value_col] == lv].groupby("Case", as_index=True)["TAC_kJPY"].mean()
        y = tmp.reindex(case_order)  # 無いCaseはNaNになる

        label = f"{value_col} = {lv}" if label_func is None else label_func(lv)
        ax.plot(x, y.values, marker="o", color=c, label=label, linewidth=2)

    ax.set_xticks(x)
    ax.set_xticklabels(case_order)
    #ax.set_xlabel("Case")
    ax.set_ylabel("TAC [kJPY/year]")
    ax.grid(alpha=0.3)

    ax.ticklabel_format(style="plain", axis="y", useOffset=False)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=True)
    fig.subplots_adjust(right=0.80)

    fig.savefig(os.path.join(OUTPUT_DIR, fname), dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_TAC_price_sensitivity_side_by_side(df):
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 4),
        sharey=True, constrained_layout=True
    )
    settings = [
        ("BasicPrice", "BasicFactor", plt.cm.Reds, "Basic price sensitivity"),
        ("EnergyPrice", "EnergyFactor", plt.cm.Greens, "Energy price sensitivity"),
    ]

    case_order = ["Case1", "Case2", "Case3", "Case4", "Case5"]
    x = np.arange(len(case_order))

    for ax, (sens, value_col, cmap, title) in zip(axes, settings):
        sub = df[df["Sensitivity"] == sens].copy()
        base = df[df["Sensitivity"] == "Base"].copy()
        base[value_col]=1.0
        sub = pd.concat([sub,base])
        if sub.empty:
            ax.set_title(f"{title}\n(No data)")
            continue

        levels = sub[value_col].dropna().unique().tolist()
        levels = sorted(levels, key=lambda v: float(v))
        vmin, vmax = min(levels), max(levels)
        colors = cmap(np.linspace(0.3, 1.0, len(levels)))

        for lv,color in zip(levels,colors):
            tmp = (
                sub[sub[value_col] == lv]
                .groupby("Case", as_index=True)["TAC_kJPY"]
                .mean()
            )
            y = tmp.reindex(case_order)

            is_base = np.isclose(lv, 1.0)
            
             
            lw = 3 if is_base else 2
            ls = "-" if is_base else "--"
            print(vmax,vmin,lv,is_base,lw,ls,color,y.values)


            ax.plot(
                x, y.values,
                marker="o",
                color=color,
                linewidth=lw,
                linestyle=ls,
                label=fmt_pct_from_factor(lv, sens)
            )

        ax.set_xticks(x)
        ax.set_xticklabels(case_order)
        ax.set_title(title)
        ax.set_ylabel("TAC [kJPY/year]")
        ax.grid(alpha=0.3)

        # ★ 凡例は各グラフ右上
        ax.legend(loc="upper right", frameon=True, fontsize=9)

    fig.savefig(
        os.path.join(OUTPUT_DIR, "TAC_sensitivity_Price_side_by_side.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close(fig)

# ================================
# TAC sensitivity plots
# ================================
plot_TAC_sensitivity(
    DF, "NumEV", "Num_vehicle", plt.cm.Blues,
    "TAC sensitivity to EV number",
    "TAC_sensitivity_Num_vehicle.png",
    label_func=lambda v: f"Num_vehicle = {int(v)}"
)

# BasicPrice：BasicFactor(0.8など)を“BasicPrice -20%”に
plot_TAC_sensitivity(
    DF, "BasicPrice", "BasicFactor", plt.cm.Reds,
    "TAC sensitivity to Basic price",
    "TAC_sensitivity_BasicPrice.png",
    label_func=lambda v: fmt_pct_from_factor(v, "BasicPrice")
)

# EnergyPrice：EnergyFactorを“EnergyPrice +10%”などに
plot_TAC_sensitivity(
    DF, "EnergyPrice", "EnergyFactor", plt.cm.Greens,
    "TAC sensitivity to Energy price",
    "TAC_sensitivity_EnergyPrice.png",
    label_func=lambda v: fmt_pct_from_factor(v, "EnergyPrice")
)
plot_TAC_price_sensitivity_side_by_side(DF)

# ================================
# DPBP vs Case (Discount rate)  ※ Case1 제외
# ================================
plt.figure(figsize=(12, 4))
ax = plt.gca()

# DPBPでは Case1 を除外
case_order = ["Case2","Case3","Case4","Case5"]
x = np.arange(len(case_order))

rates = discount_rates
offsets = np.linspace(-0.18, 0.18, len(rates))

markers = ["o", "s", "D", "^"]
linestyles = ["-", "--", "-.", ":"]

for i, r in enumerate(rates):
    r_df = DF_DPB[DF_DPB["DiscountRate"] == r]
    r_df = r_df[r_df["Case"].isin(case_order)]
    r_df = r_df.set_index("Case").reindex(case_order).reset_index()

    ax.plot(
        x + offsets[i],
        r_df["DPBP"].values,
        marker=markers[i % len(markers)],
        linestyle=linestyles[i % len(linestyles)],
        linewidth=2,
        markersize=6,
        label=f"r = {int(r*100)}%"
    )

ax.axhline(
    SYSTEM_LIFETIME,
    ls="--",
    color="gray",
    alpha=0.6,
    label="System lifetime"
)

ax.set_xticks(x)
ax.set_xticklabels(case_order)
ax.set_ylabel("Discounted Payback Period [year]")
ax.set_ylim(0, SYSTEM_LIFETIME)
ax.grid(alpha=0.3)

ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=True)
plt.tight_layout(rect=[0, 0, 0.82, 1])

plt.savefig(
    os.path.join(OUTPUT_DIR, "DPBP_sensitivity_DiscountRate.png"),
    dpi=300
)
plt.close()



print("Assessment sensitivity completed (updated with ICE/TAC/DPBP replacement PV).")
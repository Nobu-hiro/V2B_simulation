import os
import datetime
import numpy as np
import pandas as pd
import gc
from create_EVmodel3 import EVGroupTrip, EVGroupCharge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 参照PV容量のキャッシュ（同じ条件で何回も参照計算しない）
_PV_CAP_CACHE = {}  # key -> solar_kw




def run_case(
    demand_name,
    Num_Vehicle,
    scenario_id,
    basic_factor=1.0,
    energy_factor=1.0,
    starttime=datetime.datetime(2012, 1, 1),
    endtime=datetime.datetime(2015, 4, 1),
    InputFolder=None,
    OutputFolder="output_single",
    _ref_depth=0,  # 内部用（参照再帰の深さ制限）
):
    if InputFolder is None:
        InputFolder = os.path.join(BASE_DIR, "BuildingDemand_Input")

    os.makedirs(OutputFolder, exist_ok=True)

    # ------------------
    # Load demand
    # ------------------
    DF = pd.read_csv(os.path.join(InputFolder, f"{demand_name}.csv"), index_col=0)
    DF = DF.dropna()
    DF.loc[DF["Demand_Power"] < 0, "Demand_Power"] = 0

    # ------------------
    # Scenario definition
    #  Is_SolarCapacity: PV容量を最適化するかどうか（PV有無ではない）
    #  Ref_PVCapacity: 参照シナリオ番号（ID）
    # ------------------
    if scenario_id == 1:
        # ICE only
        Is_SolarCapacity = False
        ControlRatio = 0
        Is_BESScal = False
        Ref_PVScenario = 0

    elif scenario_id == 2:
        # ICE + PV (opt)
        Is_SolarCapacity = True
        ControlRatio = 0
        Is_BESScal = False
        Ref_PVScenario = 1  # ※最適化するので「参照ID」は実質不要（ログ用）

    elif scenario_id == 3:
        # EV only, no control (PV capacity fixed from ref scenario)
        Is_SolarCapacity = False
        ControlRatio = 0
        Is_BESScal = False
        Ref_PVScenario = 2

    elif scenario_id == 4:
        # EV + control (PV capacity fixed from ref scenario)
        Is_SolarCapacity = False
        ControlRatio = 1
        Is_BESScal = False
        Ref_PVScenario = 2

    elif scenario_id == 5:
        # EV + PV + control (opt)
        Is_SolarCapacity = True
        ControlRatio = 1
        Is_BESScal = False
        Ref_PVScenario = 5  # ※最適化するので参照IDは実質不要（ログ用）

    else:
        raise ValueError("Undefined scenario_id")

    # ------------------
    # NumEV / NumICE をケース定義に合わせて設定
    #  - Case1,2: ICEあり EVなし
    #  - Case3,4,5: EVあり ICEなし
    # ------------------
    if scenario_id in [1, 2]:
        NumEV = 0
        NumICE = Num_Vehicle
    else:
        NumEV = Num_Vehicle
        NumICE = 0

    # ------------------
    # EV trip
    # ------------------
    TripType = "Office"
    EVgrouptrip = EVGroupTrip(
        "All",
        NumEV,        # ★ EV台数はここに入れる
        starttime,
        endtime,
        False,
        TripType,
        10000,
    )

    # ------------------
    # Resolve PV capacity if NOT optimizing
    # 参照シナリオ番号(Ref_PVScenario) -> 参照シナリオの SolarCapacity[kW] を取得
    # ------------------
    def _resolve_ref_solar_kw(ref_scenario_id: int) -> float:
        if ref_scenario_id in [0, None]:
            return 0.0

        # 参照計算の無限再帰を防ぐ
        if _ref_depth >= 3:
            raise RuntimeError("Reference PV resolution recursion too deep. Check Ref_PVScenario settings.")

        key = (demand_name, Num_Vehicle, ref_scenario_id, basic_factor, energy_factor, starttime, endtime)
        if key in _PV_CAP_CACHE:
            return _PV_CAP_CACHE[key]

        # 参照シナリオを回して SolarCapacity(kW) を取得
        ref_summary = run_case(
            demand_name=demand_name,
            Num_Vehicle=Num_Vehicle,
            scenario_id=ref_scenario_id,
            basic_factor=basic_factor,
            energy_factor=energy_factor,
            starttime=starttime,
            endtime=endtime,
            InputFolder=InputFolder,
            OutputFolder=OutputFolder,
            _ref_depth=_ref_depth + 1,
        )
        if ref_summary is None:
            raise RuntimeError(f"Reference scenario {ref_scenario_id} failed for PV capacity resolution.")

        solar_kw = float(ref_summary.get("SolarCapacity", 0.0))
        _PV_CAP_CACHE[key] = solar_kw
        return solar_kw

    if Is_SolarCapacity:
        # 最適化する → Default_solarcapacity は「初期値」扱いなので 0 として渡す（安全）
        default_solar_kw = 0.0
    else:
        # 最適化しない → 参照シナリオの PV容量(kW) を固定値として使う
        default_solar_kw = _resolve_ref_solar_kw(Ref_PVScenario)

    # ------------------
    # Run model
    # ------------------
    Evgroupcharge = EVGroupCharge(
        demand_name,
        EVgrouptrip,
        "V2B",
        0.5, 0.3, 6, 62,
        DF.index.to_numpy(),
        DF["Demand_Power"].to_numpy(),
        DF["RE_Power"].to_numpy(),
        Is_SolarCapacity,     # Is_opt_capacity
        default_solar_kw,     # ★ 参照IDではなく「kW」を渡す
        ControlRatio,
        Is_BESScal,
        energy_price_factor=energy_factor,
        contract_price_factor=basic_factor,
    )

    if Evgroupcharge.results is None:
        return None

    # ------------------
    # Summary
    # ------------------
    summary = Evgroupcharge.Dict_summary.copy()
    summary["DemandName"] = demand_name
    summary["Scenario"] = scenario_id
    summary["NumEV"] = NumEV
    summary["NumICE"] = NumICE
    summary["BasicFactor"] = basic_factor
    summary["EnergyFactor"] = energy_factor

    # 参照情報も残す（解析に便利）
    summary["Is_opt_solarcapacity"] = Is_SolarCapacity
    summary["Ref_PVScenario"] = Ref_PVScenario
    summary["DefaultSolar_kW_used"] = float(default_solar_kw)  # 実際に固定に使ったkW（optなら0）

        
    del Evgroupcharge
    del EVgrouptrip
    del DF
    gc.collect()


    return summary
import pandas as pd
from .query import chiller_query
import math
from . import config
import pandas as pd
import numpy as np
import re
def _float_or_none(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None 
    try:
        return float(v)
    except Exception:
        return None
    
def build_param_response(df: pd.DataFrame, include_total: bool = True):
    if df is None or df.empty:
        return {"ok": False, "error": "no data"}
    df = df.sort_values(["ts", "Source_tag"])
    
    param = {}
    total = 0.0

    for _, row in df.iterrows():
        tag = row["Source_tag"]
        val = _float_or_none(row["value"])
        
        th = config.THRESHOLD_BY_TAG.get(tag, config.DEFAULT_THRESHOLD)
        
        online = (val is not None) and (val > th)
        data = 0.0 if val is None else val

        param[tag] = {"online": online, "data": data}

        if include_total and val is not None:
            total += val

    ts = df["ts"].max()
    ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

    out = {"ok": True, "ts": ts_str, "param": param}
    if include_total:
        out["total"] = total
    return out


def _pivot_history_to_records(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    
    pivoted = df.pivot(index = "ts", columns = "Source_tag", values = "value").reset_index()
    recs = pivoted.to_dict(orient = "records")

    cleaned = []
    for r in recs:
        out = {}
        for k,v in r.items():
            if isinstance(v, pd.Timestamp):
                out[k] = v.isoformat()
            elif isinstance(v, float) and math.isnan(v):
                out[k] = None
            else:
                out[k] = v
        cleaned.append(out)
    return cleaned


#-------Chiller power-------#
def df_chiller_power():
    df = chiller_query.chiller_power()
    print(type(df))

    return  build_param_response(df, include_total=True)

def df_chiller_power_history(start="-20d", stop="now()", every = "30m"):
    df = chiller_query.chiller_power_history(start, stop, every)
    
    return _pivot_history_to_records(df)



#-------pump_power-------#
def df_pump_power():
    df = chiller_query.pump_power()

    return build_param_response(df)

def df_pump_power_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_power_history(start, stop, every)
    return _pivot_history_to_records(df)


#-------flow-------#
def df_pump_flow():
    df = chiller_query.pump_flow()
    print(type(df))

    return build_param_response(df)

def df_pump_flow_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_flow_history(start, stop, every)
    return _pivot_history_to_records(df)

#------temp_chiller-------#
def df_chiller_temp():
    df = chiller_query.chiller_temp()
    print(type(df))
    return build_param_response(df)

def df_chiller_temp_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_temp_history(start, stop, every)
    return _pivot_history_to_records(df)


#chiller_temp_history
def df_chiller_tank_temp_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_tank_temp_history(start, stop, every)
    return _pivot_history_to_records(df)



#Thermoform
def df_thermoform_power_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.thermoform_power_history(start, stop, every)
    return _pivot_history_to_records(df)



#------chiller_cooling capa-------#
def kw_cooling(flow_m3h: float, dt_c: float) -> float:
    RHO = 997.0          # kg/m3
    CP = 4.186           # kJ/kg-K
    # (m3/h * kg/m3) => kg/h  แล้ว /3600 => kg/s
    # kg/s * (kJ/kgK) => kJ/sK = kW/K
    return (flow_m3h * RHO * CP * dt_c) / 3600.0


#COP (flow*cp*dif_temp)
def df_cop():
    pw = df_chiller_power()
    fl = df_pump_flow()
    tp = df_chiller_temp()

    if not pw or not fl or not tp:
        return None
    
    MAP = {
        "P1_CH01": {
            "power": "Winenergy.P1CH01.kW",
            "flow": "Winenergy.P1CH01.Flow_Counter",
            "t_ret": "Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1",
            "t_sup": "Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1"
        },

        "P1_CH02": {
            "power": "Winenergy.P1CH02.kW",
            "flow": "Winenergy.P1CH01.Flow_Counter",
            "t_ret": "Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1",
            "t_sup": "Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1"
        },

    }
    out = {}
    for name, m in MAP.items():
        try:
            p_kw = float(pw["data"][m["power"]])
            f_m3h = float(fl["data"][m["flow"]])
            t_ret = float(tp["data"][m["t_ret"]])
            t_sup = float(tp["data"][m["t_sup"]])
        except KeyError:
            continue

        dt = t_ret - t_sup
        q_kw = kw_cooling(f_m3h, dt)
        cop = (q_kw / p_kw) if p_kw > 0 else None

        out[name] = {
            "COP": cop,
            "Q_kW": q_kw,
            "P_kW": p_kw,
            "flow_m3h": f_m3h,
            "dT": dt
        }

    ts = max(pw["ts"], fl["ts"], tp["ts"])
    return {"ts": ts, "data": out}


PUMP_TAGS = [
    "Winenergy.P2CHP09.kW",
    "Winenergy.P2CHP10.kW",
    "Winenergy.P2CHP11.kW"
]




#Cost
def pump_power_cost_history(start="-24h", stop="now()", every="10m", rate=4.0):
    chiller = chiller_query.pump_power_history(start, stop, every)
    df_chiller = _pivot_history_to_records(chiller)

    df = pd.DataFrame(df_chiller) #list[dict]

    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts").set_index("ts")
    if df.empty:
        return {"ok": False, "error": "ts parse failed or empty"}

    # calc dt (hour)
    dt_h = df.index.to_series().diff().dt.total_seconds().div(3600)
    dt_h = dt_h.fillna(0).clip(lower=0)  # block dt ติดลบ

    start_ts = df.index.min()
    end_ts   = df.index.max()

    start_iso = start_ts.isoformat()
    end_iso   = end_ts.isoformat()

    # choose tag this groups
    group_tags = [
        "Winenergy.P2CHP09.kW",
        "Winenergy.P2CHP10.kW",
        "Winenergy.P2CHP11.kW"
    ]

    missing = [t for t in group_tags if t not in df.columns]
    if missing:
        return {"ok": False, "error": f"missing tags: {missing}"}

    # sum kw
    df["kw_total"] = df[group_tags].fillna(0).sum(axis=1)
    sum_kw = df["kw_total"]
    # kWh ต่อช่วงเวลา + THB ต่อช่วงเวลา
    df["kwh"] = df["kw_total"] * dt_h
    df["thb"] = df["kwh"] * rate

    total_kwh = float(df["kwh"].sum())
    total_thb = float(df["thb"].sum())

    #print(total_kwh, total_thb)

    pump = chiller_query.pump_power_history()
    df_pump = build_param_response(pump)


    return {
            "ok": True,
            "rate": rate,
            "summary": {"total_kwh": total_kwh, "total_thb": total_thb},
            "start_iso": start_iso,
            "end_iso": end_iso,
            "data": sum_kw
        }
    #print(df_chiller)



def predict_cost_history(start="-24h", stop="now()", every="10m",rate=4.0 , rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, rpm_drop))
    raw = pump_power_cost_history(start, stop, every, rate)
    power_ratio = rpm_drop**3
    power_drop = power_ratio*raw["data"]
    saving = (1-power_ratio)
    saving_rate = saving*100
    cost_before = raw["summary"]["total_thb"]
    cost_after = cost_before*saving
    cost_saving = cost_before - cost_after
    return {
        "ok": True,
        "saving_rate": round(saving_rate, 2),
        "cost_before": round(cost_before, 2),
        "cost_after": round(cost_after, 2),
        "cost_seving": round(cost_saving, 2),
        "pred_power_drop": round(power_drop, 2)
    }


def df_pump_total_predict_history(start="-24h", stop="now()", every="10m", rate=4.0, rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, float(rpm_drop)))
    power_ratio = rpm_drop ** 3

    raw_hist = df_pump_power_history(start=start, stop=stop, every=every)  # list[dict]: ts + tags
    history = []
    for r in raw_hist:
        total = 0.0
        for tag in PUMP_TAGS:
            v = r.get(tag)
            if isinstance(v, (int, float)):
                total += float(v)

        history.append({
            "ts": r.get("ts"),
            "kw_total": total,
            "pred_total_kw": total * power_ratio,
        })

    raw = pump_power_cost_history(start, stop, every, rate)
    cost_before = float(raw["summary"]["total_thb"])
    cost_after = cost_before * power_ratio
    cost_saving = cost_before - cost_after
    saving_rate = (1.0 - power_ratio) * 100.0

    return {
        "ok": True,
        "history": history,
        "summary": {
            "saving_rate": round(saving_rate, 2),
            "cost_before": round(cost_before, 2),
            "cost_after": round(cost_after, 2),
            "cost_saving": round(cost_saving, 2),
        },
    }

#reccomed

def df_recommend(start="-30d", stop="now()", every="1h"):

    tf = pd.DataFrame(df_thermoform_power_history(start=start, stop=stop, every=every))
    tank = pd.DataFrame(df_chiller_tank_temp_history(start=start, stop=stop, every=every))

    tf["ts"] = pd.to_datetime(tf["ts"], utc=True, errors="coerce")
    tank["ts"] = pd.to_datetime(tank["ts"], utc=True, errors="coerce")


    # รวมให้เป็น df เดียว จะได้กรองแล้วเอา temp ไปเฉลี่ยได้ทันที
    df = tf.merge(tank, on="ts", how="inner")

    col4 = "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal"
    col5 = "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal"
    col7 = "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal"
    tempcol = "Chiller.PLANT_Node2.CLG2_TEMP_CHWR"

    # condition
    on_3TF = (df[col4] > 40) & (df[col5] > 40) & (df[col7] > 40)
    on_2TF = (
        ((df[col4] > 40) & (df[col5] > 40)) |
        ((df[col4] > 40) & (df[col7] > 40)) |
        ((df[col5] > 40) & (df[col7] > 40))
    )
    
    #  fill out to new df
    df_2TF = df.loc[on_2TF].copy()
    df_3TF = df.loc[on_3TF].copy()
    #print(df_3TF)
    #  make average
    mean_2TF = df_2TF[tempcol].mean() if not df_2TF.empty else np.nan
    mean_3TF = df_3TF[tempcol].mean() if not df_3TF.empty else np.nan

    return {
        "ok": True,
        "rows": {"on_2TF": len(df_2TF), "on_3TF": len(df_3TF)},
        "mean_TF": {
            "on_2TF": None if np.isnan(mean_2TF) else round(mean_2TF, 2),
            "on_3TF": None if np.isnan(mean_3TF) else round(mean_3TF, 2),
        }
    }


#suggestion
def _parse_every_to_minutes(every: str) -> int:
    """
    รองรับ "30m", "10m", "1h", "2h"
    """
    m = re.match(r"^\s*(\d+)\s*([mh])\s*$", str(every).lower())
    if not m:
        return 60  
    n = int(m.group(1))
    unit = m.group(2)
    return n if unit == "m" else n * 60

def _consecutive_true(series_bool: pd.Series, n_points: int) -> pd.Series:
    # True ต่อเนื่องครบ n_points
    s = series_bool.fillna(False).astype(int)
    return s.rolling(n_points, min_periods=n_points).sum().ge(n_points)

def suggestion_status_chiller():
    start="-5h"
    stop="now()"
    every="15m"
    percent_load = 85 #%
    load_input = 240 #kW
    consecutive_minutes = 180

    ch_df = pd.DataFrame(df_chiller_power_history(start=start, stop=stop, every=every))
    if ch_df is None or ch_df.empty:
        return {"ok": False, "error": "no data"}
    ch_df["ts"] = pd.to_datetime(ch_df["ts"], utc=True, errors="coerce")
    ch_df = ch_df.dropna(subset=["ts"]).sort_values("ts")

    #chiller
    P2CH1_power = "Winenergy.P2CH01.kW"
    P2CH2_power = "Winenergy.P2CH02.kW"

    #temp_return

    P2CH1_temp_return = "Chiller.PLANT_Node2.CLG2_TEMP_CHWR"
    P2CH1_temp_supply = "Chiller.PLANT_Node2.CLG2_TEMP_CHWS"

    ch_df["p2ch1_pct"] = (ch_df[P2CH1_power] / load_input) * 100.0
    ch_df["p2ch2_pct"] = (ch_df[P2CH2_power] / load_input) * 100.0
    
    ch_df["p2ch1_over"] = (ch_df["p2ch1_pct"] > percent_load)
    ch_df["p2ch2_over"] = (ch_df["p2ch2_pct"] > percent_load)
    
    all_true_p2ch1 = ch_df["p2ch1_over"].all()
    all_true_p2ch2 = ch_df["p2ch2_over"].all()

    print(all_true_p2ch1)

    last = ch_df.iloc[-1]
    last["p2ch2_over_consec"]

    decision = None
    print((ch_df[P2CH1_power] > 50 & ch_df[P2CH2_power] > 50))
    if (ch_df[P2CH1_power] > 50 & ch_df[P2CH2_power] > 50):#
        return
    
    if all_true_p2ch1 or all_true_p2ch2:
        decision = "ON_2_CHILLER"  # ถ้ามี chiller ตัวใดเกินเกณฑ์ต่อเนื่อง แนะนำเปิด 2 ตัว
    else:
        decision = "ON_1_CHILLER"  # ถ้าไม่มีใครเกินเกณฑ์ แนะนำเปิด 1 ตัว

    return {
        "ok": True,
        "decision": decision,
        "last_data": last.to_dict(),  # ข้อมูลล่าสุดที่ใช้ตัดสินใจ
        }
    #return()

print(suggestion_status_chiller())

"""
def suggestion:
    def number_chiller_on:
    def how_many_saving:
    def 

"""
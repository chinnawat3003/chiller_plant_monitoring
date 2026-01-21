import pandas as pd
from .query import chiller_query
import math
from . import config
import pandas as pd
import numpy as np
import re

test_mockup = False

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
def df_chiller_power(plant_id):
    df = chiller_query.chiller_power(plant_id)
    result = build_param_response(df, include_total=True)

    if test_mockup:
        result ={
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "param": {
                "Winenergy.P2CH01.kW": {
                "online": False,
                "data": 0
                },
                "Winenergy.P2CH02.kW": {
                "online": True,
                "data": 150
                }
            },
            "total": 250,
            }
    return  result

def df_chiller_power_history(plant_id, start="-20d", stop="now()", every = "30m"):
    df = chiller_query.chiller_power_history(plant_id, start, stop, every)
    
    return _pivot_history_to_records(df)



#-------pump_power-------#
def df_pump_power(plant_id):
    df = chiller_query.pump_power(plant_id)
    result = build_param_response(df)

    if test_mockup:
        result ={
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "param": {
                "Winenergy.P2CHP09.kW": {
                "online": True,
                "data": 78.90409088134766
                },
                "Winenergy.P2CHP10.kW": {
                "online": False,
                "data": 0
                },
                "Winenergy.P2CHP11.kW": {
                "online": True,
                "data": 90.5
                }
            },
            "total": 78.90409088134766,
        }
    return result

def df_pump_power_history(plant_id,start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_power_history(plant_id, start, stop, every)
    return _pivot_history_to_records(df)


#-------flow-------#
def df_pump_flow(plant_id):
    df = chiller_query.pump_flow(plant_id)
    result = build_param_response(df)

    if test_mockup:
        result ={
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "param": {
                "Winenergy.P2CH01.Flow_Counter": {
                "online": True,
                "data": 150.5
                }
            }
        }
    return result

def df_pump_flow_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_flow_history(plant_id, start, stop, every)
    return _pivot_history_to_records(df)

#------temp_chiller-------#
def df_chiller_temp(plant_id):
    df = chiller_query.chiller_temp(plant_id)
    result = build_param_response(df, include_total=True)
    if test_mockup:
        result ={
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "param": {
                "Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1": {
                "online": True,
                "data": 11
                },
                "Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1": {
                "online": True,
                "data": 9
                },
                "Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1": {
                "online": True,
                "data": 11
                },
                "Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1": {
                "online": True,
                "data": 9
                },
            },
            }
    return  result

def df_chiller_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_temp_history(plant_id, start, stop, every)
    return _pivot_history_to_records(df)


#chiller_temp
def df_chiller_tank_temp(plant_id):
    df = chiller_query.chiller_tank_temp(plant_id)
    result = build_param_response(df, include_total=True)
    if test_mockup:
        result ={
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "param": {
                "Chiller.PLANT_Node2.CLG2_TEMP_CHWR": {
                "online": True,
                "data": 11
                },
                "Chiller.PLANT_Node2.CLG2_TEMP_CHWS": {
                "online": True,
                "data": 9
                },
                
            },
            }
    return  result

def df_chiller_tank_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_tank_temp_history(plant_id, start, stop, every)
    return _pivot_history_to_records(df)



#Thermoform
def df_thermoform_power(plant_id):
    df = chiller_query.thermoform_power(plant_id)
    return build_param_response(df)

#history
def df_thermoform_power_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.thermoform_power_history(plant_id, start, stop, every)
    return _pivot_history_to_records(df)



#------chiller_cooling capa-------#
def kw_cooling(flow_m3h: float, dt_c: float) -> float:
    RHO = 997.0          # kg/m3
    CP = 4.186           # kJ/kg-K
    # (m3/h * kg/m3) => kg/h  แล้ว /3600 => kg/s
    # kg/s * (kJ/kgK) => kJ/sK = kW/K
    return (flow_m3h * RHO * CP * dt_c) / 3600.0

def df_cooling_capa_history(plant_id, start="-24h", stop="now()", every="10m"):
    df_temp = chiller_query.chiller_tank_temp_history(plant_id, start, stop, every)
    df_flow = chiller_query.pump_flow_history(plant_id, start, stop, every)
    #constant param
    Cp = 1.163

    for d in (df_temp, df_flow):
        d["ts"] = pd.to_datetime(d["ts"], utc=True, errors="coerce")
        d.dropna(subset=["ts"], inplace=True)
        d.sort_values("ts", inplace=True)
        
    raw_df = pd.concat([df_temp, df_flow], ignore_index=True).sort_values("ts")
    wide = raw_df.pivot(index="ts", columns="Source_tag", values="value")
    
    # different temp (use plant COP map CH01)
    plant = config.get_plant(plant_id)
    t_ret = plant["cop_map"]["CH01"]["t_ret"]
    t_sup = plant["cop_map"]["CH01"]["t_sup"]
    wide["dif_temp"] = wide[t_ret] - wide[t_sup]

    #cooling capa 
    #flow = wide["Winenergy.P2CH01.Flow_Counter"]
    flow = 150 # ใช้ constant
    wide["cooling_capa"] = flow * Cp * wide["dif_temp"]

    #print(f"dif temp = {wide["dif_temp"]}")
    out = wide[["cooling_capa"]].reset_index()
    return out

#COP (flow*cp*dif_temp)
def df_cop(plant_id):
    pw = df_chiller_power(plant_id)
    fl = df_pump_flow(plant_id)
    tp = df_chiller_tank_temp(plant_id)
    
    if not pw or not fl or not tp:
        return None
    
    plant = config.get_plant(plant_id)
    MAP = plant["cop_map"]    
    out = {}
    
    for name, m in MAP.items():
        
        def getv(payload, tag):
            return payload["param"][tag]["data"]

        # ใน loop:
        p_kw = float(getv(pw, m["power"]))
        f_m3h = float(getv(fl, m["flow"]))
        t_ret = float(getv(tp, m["t_ret"]))
        t_sup = float(getv(tp, m["t_sup"]))

        
        #print(f"p_kw = {p_kw}")
        f_m3h = 150 #mockup
        dt = t_ret - t_sup
        #dt = 3
        q_kw = kw_cooling(f_m3h, dt)  
        
        cop = (q_kw / p_kw) if p_kw > 30 else None

        out[name] = {
            "COP": cop
            
        }

    ts = max(pw["ts"], fl["ts"], tp["ts"])
    return {"ts": ts, "data": out}


#Cost
def pump_power_cost_history(plant_id, start="-24h", stop="now()", every="10m", rate=4.0):
    chiller = chiller_query.pump_power_history(plant_id, start, stop, every)
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

    return {
            "ok": True,
            "rate": rate,
            "summary": {"total_kwh": total_kwh, "total_thb": total_thb},
            "start_iso": start_iso,
            "end_iso": end_iso,
            "data": sum_kw
        }
    #print(df_chiller)



def predict_cost_history(plant_id, start="-24h", stop="now()", every="10m",rate=4.0 , rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, rpm_drop))
    raw = pump_power_cost_history(plant_id, start, stop, every, rate)
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


def df_pump_total_predict_history(plant_id, start="-24h", stop="now()", every="10m", rate=4.0, rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, float(rpm_drop)))
    power_ratio = rpm_drop ** 3
    plant = config.get_plant(plant_id)
    pump_tags = plant["tags"]["pump_power"]


    raw_hist = df_pump_power_history(plant_id, start=start, stop=stop, every=every)  # list[dict]: ts + tags
    history = []
    for r in raw_hist:
        total = 0.0
        for tag in pump_tags:
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

def suggestion(plant_id):
    plant = config.get_plant(plant_id)
    print(plant)
    cop_map = plant["cop_map"]  # {"CH01": {...}, "CH02": {...}}
    power_tags = [m["power"] for m in cop_map.values()]

    # -------- helpers --------
    def _clean_ts(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or "ts" not in df.columns:
            return pd.DataFrame()
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")
        return df

    def pull_data(start="-12h", stop="now()", every="15m"):
        ch_power_df   = _clean_ts(pd.DataFrame(df_chiller_power_history(plant_id, start=start, stop=stop, every=every)))
        ch_cooling_df = _clean_ts(pd.DataFrame(df_cooling_capa_history(plant_id, start=start, stop=stop, every=every)))

        if ch_power_df.empty:
            return pd.DataFrame()

        raw_df = ch_power_df
        if not ch_cooling_df.empty:
            raw_df = pd.merge(raw_df, ch_cooling_df, on="ts", how="outer")

        raw_df = raw_df.sort_values("ts")
        return raw_df

    def check_status_chiller_on(th_kw=50.0):
        snap = df_chiller_power(plant_id)  # current snapshot
        if not snap or not snap.get("ok"):
            return {"ok": False, "num_chiller_on": 0}

        num_on = 0
        for tag in power_tags:
            v = snap.get("param", {}).get(tag, {}).get("data", 0)
            if isinstance(v, (int, float)) and float(v) > th_kw:
                num_on += 1

        return {"ok": True, "num_chiller_on": num_on}

    def on_2_condition(start="-12h", stop="now()", every="20m", cooling_low=686):
        df = _clean_ts(pd.DataFrame(df_cooling_capa_history(plant_id, start=start, stop=stop, every=every)))
        if df.empty or "cooling_capa" not in df.columns:
            return {"ok": True, "status": "Now 2 Chiller ON", "suggest": "-", "reason": "no cooling data"}

        # เงื่อนไข: cooling ต่ำกว่า threshold ตลอดช่วง -> แนะนำลดเหลือ 1 chiller
        all_low = (df["cooling_capa"].dropna() < cooling_low).all()

        if all_low:
            return {
                "ok": True,
                "status": "Now 2 Chiller ON",
                "suggest": "ON 1 Chiller",
                "reason": f"Cooling capa less than {cooling_low} (all points)"
            }
        else:
            return {
                "ok": True,
                "status": "Now 2 Chiller ON",
                "suggest": "-",
                "reason": f"Cooling capa more than {cooling_low} (some points)"
            }

    def on_1_condition(start="-1h", stop="now()", every="15m", cooling_low=686):
        # constant (คุณปรับทีหลังได้)
        power_peak = 250.0
        percent_load = 85.0  # %

        df = pull_data(start=start, stop=stop, every=every)
        if df.empty:
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "no history"}

        snap = df_chiller_power(plant_id)  # current snapshot
        if not snap or not snap.get("ok"):
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "no snapshot"}

        # หา chiller ที่กำลัง ON จาก snapshot
        on_tag = None
        on_val = 0.0
        for tag in power_tags:
            v = float(snap.get("param", {}).get(tag, {}).get("data", 0))
            if v > 50:
                on_tag = tag
                on_val = v
                break

        if on_tag is None:
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "cannot detect running chiller"}

        # เงื่อนไข 1: cooling capacity สูงเกิน -> เปิดเพิ่ม
        if "cooling_capa" in df.columns:
            last_c = df["cooling_capa"].dropna()
            if not last_c.empty and (last_c > cooling_low).all():
                return {
                    "ok": True,
                    "status": f"Now 1 Chiller ON ({on_tag})",
                    "suggest": "ON 2 Chiller",
                    "reason": f"Cooling capa more than {cooling_low}"
                }

        # เงื่อนไข 2: %load chiller ที่กำลังวิ่ง เกิน threshold -> เปิดเพิ่ม
        if on_tag in df.columns:
            series = pd.to_numeric(df[on_tag], errors="coerce").dropna()
            if not series.empty:
                over = ((series / power_peak) * 100.0 > percent_load).all()
                if over:
                    return {
                        "ok": True,
                        "status": f"Now 1 Chiller ON ({on_tag})",
                        "suggest": "ON 2 Chiller",
                        "reason": f"%load more than {percent_load}%"
                    }

        return {
            "ok": True,
            "status": f"Now 1 Chiller ON ({on_tag})",
            "suggest": "-",
            "reason": f"load={round((on_val/power_peak)*100, 2)}% and cooling not over"
        }

    # -------- main decision --------
    start = "-12h"
    stop = "now()"
    every = "20m"
    cooling_low = 686

    st = check_status_chiller_on()

    if st.get("num_chiller_on", 0) >= 2:
        return on_2_condition(start=start, stop=stop, every=every, cooling_low=cooling_low)

    if st.get("num_chiller_on", 0) == 1:
        return on_1_condition(start="-1h", stop=stop, every="15m", cooling_low=cooling_low)

    return {"ok": True, "status": "Plant close", "suggest": "-", "reason": "-"}




#limit
def limit_chiller_power_input(plant_id):
    data = df_chiller_power(plant_id)
    plant = config.get_plant(plant_id)
    ch_tags = plant["tags"]["chiller_power"]
    # consider chiller online if any chiller power tag is online
    any_online = any(data.get("param", {}).get(t, {}).get("online") for t in ch_tags)
    #if data = 0 
    if any_online:
        
        data["limits"] = {"low": 75.0, "high": 250.0}
    elif not any_online:
        
        data["limits"] = {"low": 0.0, "high": 0.0}

    return data


if __name__ == "__main__":
    print(suggestion())
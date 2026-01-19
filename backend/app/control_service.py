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


#chiller_temp
def df_chiller_tank_temp():
    df = chiller_query.chiller_tank_temp()

    return build_param_response(df)

def df_chiller_tank_temp_history(start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_tank_temp_history(start, stop, every)
    return _pivot_history_to_records(df)


def df_pump_power():
    df = chiller_query.pump_power()

    return build_param_response(df)

#Thermoform
def df_thermoform_power():
    df = chiller_query.thermoform_power()
    return build_param_response(df)

#history
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

def df_cooling_capa_history(start="-24h", stop="now()", every="10m"):
    df_temp = chiller_query.chiller_tank_temp_history(start, stop, every)
    df_flow = chiller_query.pump_flow_history(start, stop, every)
    #constant param
    Cp = 1.163

    for d in (df_temp, df_flow):
        d["ts"] = pd.to_datetime(d["ts"], utc=True, errors="coerce")
        d.dropna(subset=["ts"], inplace=True)
        d.sort_values("ts", inplace=True)
        
    raw_df = pd.concat([df_temp, df_flow], ignore_index=True).sort_values("ts")
    wide = raw_df.pivot(index="ts", columns="Source_tag", values="value")
    
    # different temp
    p2ch1_ret = wide["Chiller.PLANT_Node2.CLG2_TEMP_CHWR"]
    p2ch1_sup = wide["Chiller.PLANT_Node2.CLG2_TEMP_CHWS"]
    
    wide["dif_temp"] = p2ch1_ret - p2ch1_sup

    #cooling capa 
    #flow = wide["Winenergy.P2CH01.Flow_Counter"]
    flow = 150 # ใช้ constant
    wide["cooling_capa"] = flow * Cp * wide["dif_temp"]

    #print(f"dif temp = {wide["dif_temp"]}")
    out = wide[["cooling_capa"]].reset_index()
    return out

#COP (flow*cp*dif_temp)
def df_cop():
    pw = df_chiller_power()
    fl = df_pump_flow()
    tp = df_chiller_temp()
    
    if not pw or not fl or not tp:
        return None
    
    MAP = {
        "P2_CH01": {
            "power": "Winenergy.P2CH01.kW",
            "flow": "Winenergy.P2CH01.Flow_Counter",
            "t_ret": "Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1",
            "t_sup": "Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1"
        },

        "P2_CH02": {
            "power": "Winenergy.P2CH02.kW",
            "flow": "Winenergy.P2CH01.Flow_Counter",
            "t_ret": "Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1",
            "t_sup": "Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1"
        },

    }
    out = {}
    
    for name, m in MAP.items():
        try:
            def getv(payload, tag):
                return payload["param"][tag]["data"]

            # ใน loop:
            p_kw = float(getv(pw, m["power"]))
            f_m3h = float(getv(fl, m["flow"]))
            t_ret = float(getv(tp, m["t_ret"]))
            t_sup = float(getv(tp, m["t_sup"]))

        except KeyError:
            continue
        
        print(f"p_kw = {p_kw}")
        f_m3h = 150
        dt = t_ret - t_sup
        q_kw = kw_cooling(f_m3h, dt)  
        cop = (q_kw / p_kw) if p_kw > 30 else None

        out[name] = {
            "COP": cop
            
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

#reccomend

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

"""
def suggestion:
    def function for pull raw data such as Power, cooling capa, temp return, temp supply
    def chck about number of chiller status
    def condition
        if on 2 chiller
        if on 1 chiller

"""
def suggestion():
    def pull_data(start="-12h", stop="now()", every="15m"):
        
        percent_load = 85 #%
        load_input_max = 240 #kW

        ch_power_df = pd.DataFrame(df_chiller_power_history(start=start, stop=stop, every=every))
        ch_temp_df = pd.DataFrame(df_chiller_temp_history(start=start, stop=stop, every=every))
        ch_flow_df = pd.DataFrame(df_pump_flow_history(start=start, stop=stop, every=every))

        raw_df = pd.concat([ch_power_df, ch_temp_df, ch_flow_df], ignore_index=True).sort_values("ts")
        print(raw_df.columns)
        #wide = raw_df.pivot(index="ts", columns="Source_tag", values="value")
        


        print(raw_df)
        
        return raw_df
    
    def check_status_chiller_on():
        num_chiller_open = 0
        ch_power_df = df_chiller_power()
        #print(ch_power_df)
        
        data_P1CH1 = ch_power_df["param"]["Winenergy.P2CH01.kW"]["data"]
        data_P1CH2 = ch_power_df["param"]["Winenergy.P2CH02.kW"]["data"]
        #print(data_P1CH2)
        if data_P1CH1 > 50 and data_P1CH2 > 50:
            num_chiller_open = 2
        elif data_P1CH1 > 50 or data_P1CH2 > 50:
            num_chiller_open = 1
        return {
            "ok": True,
            "num_chiller_on": num_chiller_open
            }
    
    def on_2_condition(start="-12h", stop="now()", every="20m", cooling_low=686):
        result_df = pull_data(start=start, stop=stop, every=every)

        cooling_df = df_cooling_capa_history(start=start, stop=stop, every=every)
        cooling_df = cooling_df.dropna(subset=["cooling_capa"])
        
        cooling_df["p2_cooling_capa_out"] = cooling_df["cooling_capa"] < cooling_low
        #print(cooling_df["p2_cooling_capa_out"])
        all_true_cooling_capa = cooling_df["p2_cooling_capa_out"].all()
        print(all_true_cooling_capa)

        if all_true_cooling_capa == True:
            
            return {
                "ok": True,
                "status": "Now 2 Chiller ON",
                "suggest": "ON 1 Chiller",
                "reason": f"Cooling capa less than {cooling_low}"
            }
        if all_true_cooling_capa == False:

            return {
                "ok": True,
                "status": "Now 2 Chiller ON",
                "suggest": "-",
                "reason": f"Cooling capa more than {cooling_low}"
            }
        
        print(f"all_true_cooling_capa_p2 = {all_true_cooling_capa}")
        
    
    def on_1_condition(start="-12h", stop="now()", every="15m", cooling_low=686):
        #constant
        power_peak = 250
        percent_load = 85 #%
        power_P2CH1 = "Winenergy.P2CH01.kW"
        power_P2CH2 = "Winenergy.P2CH02.kW"
        result_df = pull_data(start=start, stop=stop, every=every)
        ch_now = df_chiller_power()
        #power check
        which_one_on = "None"
        
        """
            
        result_df["P2CH1_on"] = result_df[power_P2CH1] > 50 #check on-off
        P2CH1_on = result_df["P2CH1_on"].all()
        result_df["P2CH2_on"] = result_df[power_P2CH2] > 50
        P2CH2_on = result_df["P2CH2_on"].all()
        """

        p1 = ch_now["param"]["Winenergy.P2CH01.kW"]["data"]
        p2 = ch_now["param"]["Winenergy.P2CH02.kW"]["data"]
        P2CH1_on = p1 > 50
        P2CH2_on = p2 > 50

        #%Load calculation
        result_df["percent_load_p2_ch1"] = ((result_df[power_P2CH1] / power_peak) * 100) > percent_load
        result_df["percent_load_p2_ch2"] = ((result_df[power_P2CH2] / power_peak) * 100) > percent_load
        
        P2CH1_over = result_df["percent_load_p2_ch1"].all()        
        P2CH2_over = result_df["percent_load_p2_ch2"].all()


        
        
        cooling_df = df_cooling_capa_history(start=start, stop=stop, every=every)
        cooling_df = cooling_df.dropna(subset=["cooling_capa"])

        cooling_df["p2_cooling_capa_out"] = cooling_df["cooling_capa"] > cooling_low
        all_true_cooling_capa = cooling_df["p2_cooling_capa_out"].all()
        
        #cooling_capa check
        if all_true_cooling_capa == True: #cooling over
            last = cooling_df.iloc[-1]
            return {
                "ok": True,
                "status": "Now 1 Chiller ON",
                "suggest": "ON 2 Chiller",
                "reason": f"Cooling capa more than {cooling_low} at {round(last["cooling_capa"], 2)}"
            }
        
        else:
            
            if P2CH1_on == True: #chiller1 on and %Load over
                which_one_on = power_P2CH1
                if P2CH1_over == True: 
                    return {
                        "ok": True,
                        "status": "Now P2CH1 ON",
                        "suggest": "ON 2 Chiller",
                        "reason": f"%load more than {percent_load} %"
                    }
                else: #%load in range
                    last = cooling_df.iloc[-1]
                    return {
                        "ok": True,
                        "status": "Now P2CH1 ON",
                        "suggest": "-",
                        "reason": f"Cooling capa less than {cooling_low} at {round(last["cooling_capa"], 2)} and %load less than {percent_load} %"
                    }
                
            if P2CH2_on == True: #chiller2 on and %Load over
                which_one_on = power_P2CH2
                if P2CH2_over == True:
                    return {
                        "ok": True,
                        "status": "Now P2CH2 ON",
                        "suggest": "ON 2 Chiller",
                        "reason": f"%load more than {percent_load} %"
                    }
                else: 
                    last = cooling_df.iloc[-1]
                    return {
                        "ok": True,
                        "status": "Now P2CH2 ON",
                        "suggest": "-",
                        "reason": f"Cooling capa less than {cooling_low} at {round(last["cooling_capa"], 2)} and %load less than {percent_load} %"
                    }

        


        if P2CH1_on == True: #chiller1 on
            which_one_on = power_P2CH1
            if P2CH1_over == True: #%Load over
                return {
                    "ok": True,
                    "status": "Now P2CH1 ON",
                    "suggest": "ON 2 Chiller",
                    "reason": f"%load more than {percent_load} %"
                }
            else:
                return {
                    "ok": True,
                    "status": "Now P2CH1 ON",
                    "suggest": "-",
                    "reason": f"%load less than {percent_load} %"
                }
            
        elif P2CH2_on == True: #chiller2 on
            which_one_on = power_P2CH2
            if P2CH2_over == True: #%Load over
                return {
                    "ok": True,
                    "status": "Now P2CH2 ON",
                    "suggest": "ON 2 Chiller",
                    "reason": f"%load more than {percent_load} %"
                }
            else:
                return {
                    "ok": True,
                    "status": "Now P2CH2 ON",
                    "suggest": "-",
                    "reason": f"%load less than {percent_load} %"
                }
        return {
            "ok": True,
            "status": "Now 1 Chiller ON",
            "suggest": "-",
            "reason": "No condition matched"
        }



        
    
    #start get in condition
    start = "-12h"
    stop = "now()"
    every = "20m"
    cooling_low = 686
    check_num_chiller_on = check_status_chiller_on()


    if check_num_chiller_on["num_chiller_on"] == 2:
    
        return on_2_condition(start=start, stop=stop, every=every, cooling_low=cooling_low)
    
    elif check_num_chiller_on["num_chiller_on"] == 1:
        return on_1_condition(start=start, stop=stop, every=every, cooling_low=cooling_low)

        
    
    elif check_num_chiller_on["num_chiller_on"] == 0:
        return {
                    "ok": True,
                    "status": "Plant close",
                    "suggest": "-",
                    "reason": "-"
                }
    
    return {
        "ok": False,
        "status": "Unknown state",
        "suggest": "-",
        "reason": "Invalid chiller status"
    }

#limit
def limit_chiller_power_input():
    data = df_chiller_power()
    #if data = 0 
    if data["param"]["Winenergy.P2CH01.kW"]["online"] or data["param"]["Winenergy.P2CH02.kW"]["online"]:
        
        data["limits"] = {"low": 75.0, "high": 250.0}
    elif not (data["param"]["Winenergy.P2CH01.kW"]["online"] or data["param"]["Winenergy.P2CH02.kW"]["online"]):
        
        data["limits"] = {"low": 0.0, "high": 0.0}

    return data


if __name__ == "__main__":
    print(suggestion())
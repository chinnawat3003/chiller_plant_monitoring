import math
import pandas as pd
import numpy as np
import os
import random
import re
from datetime import timedelta
import pandas as pd
from reactivex import start
from .query import chiller_query
from . import config
from . import mock_provider
test_mockup = False

# -------------------- utils --------------------
def _float_or_none(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _iso_ts(v):
    if v is None:
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    try:
        # datetime
        return v.isoformat()
    except Exception:
        return str(v)   


def _clean_records_for_json(records: list[dict]) -> list[dict]:
    cleaned = []
    for r in records:
        out = {}
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                out[k] = v.isoformat()
            elif isinstance(v, float) and math.isnan(v):
                out[k] = None
            else:
                out[k] = v
        cleaned.append(out)
    return cleaned


# -------------------- old style (by real tag) --------------------
def build_param_response(df: pd.DataFrame, include_total: bool = True):
    """
    Keepไว้สำหรับ internal analytics (COP/suggestion/cost) ที่ยังใช้ key เป็น tag จริง
    """
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

        param[tag] = {"online": bool(online), "data": data}

        if include_total and val is not None:
            total += float(val)

    ts = df["ts"].max()
    out = {"ok": True, "ts": _iso_ts(ts), "param": param}
    if include_total:
        out["total"] = total
    return out


# -------------------- UI style (by slot id) --------------------
def build_slot_response(df: pd.DataFrame, slots: list[dict], include_total: bool = True):
    """
    slots: [{"id","label","unit","tag"}, ...]
    return: {"ok":True, "ts":..., "items":[...], "total":...}
    """
    by_tag = {}
    if df is not None and not df.empty:
        df = df.sort_values(["ts", "Source_tag"])
        for _, row in df.iterrows():
            by_tag[row["Source_tag"]] = _float_or_none(row["value"])
        ts = df["ts"].max()
        ts_str = _iso_ts(ts)
    else:
        ts_str = None

    total = 0.0
    items = []

    for s in slots:
        tag = s["tag"]
        val = by_tag.get(tag)

        th = config.THRESHOLD_BY_TAG.get(tag, config.DEFAULT_THRESHOLD)
        online = (val is not None) and (val > th)

        items.append({
            "id": s["id"],
            "label": s.get("label"),
            "unit": s.get("unit"),
            "value": 0.0 if val is None else float(val),
            "online": bool(online),
            # "raw_tag": tag,  # เปิดไว้ debug ได้
        })

        if include_total and val is not None:
            total += float(val)

    out = {"ok": True, "ts": ts_str, "items": items}
    if include_total:
        out["total"] = total
    return out


def pivot_history_to_slot_records(df: pd.DataFrame, slots: list[dict]) -> list[dict]:
    """
    history ออกมาเป็น list[dict] ที่ key เป็น slot id (CH1/CH2/P9...)
    """
    if df is None or df.empty:
        return []

    tag_to_id = {s["tag"]: s["id"] for s in slots}

    pivoted = df.pivot(index="ts", columns="Source_tag", values="value").reset_index()
    pivoted = pivoted.rename(columns=tag_to_id)

    keep_cols = ["ts"] + [s["id"] for s in slots]
    keep_cols = [c for c in keep_cols if c in pivoted.columns]
    pivoted = pivoted[keep_cols]

    recs = pivoted.to_dict(orient="records")
    return _clean_records_for_json(recs)


def _pivot_history_to_records(df: pd.DataFrame) -> list[dict]:
    """
    legacy history (key เป็น tag จริง) ใช้กับ cost/analytics
    """
    if df is None or df.empty:
        return []

    pivoted = df.pivot(index="ts", columns="Source_tag", values="value").reset_index()
    recs = pivoted.to_dict(orient="records")
    return _clean_records_for_json(recs)


def _plant_slots(plant_id: str, slot_group: str) -> list[dict]:
    plant = config.get_plant(plant_id)
    return plant["ui_slots"][slot_group]


# -------------------- UI endpoints group --------------------
# -------Chiller power (UI)-------#
def df_chiller_power(plant_id):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["chiller_power"]
    
    tag_list = plant["tags"]["chiller_power"]
    if mock_provider.enabled():
        values = mock_provider.default_values("chiller_power", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.chiller_power(plant_id)

    result = build_slot_response(df, slots)
    return result


def df_chiller_power_history(plant_id, start="-20d", stop="now()", every="30m"):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["chiller_power"]
    tag_list = plant["tags"]["chiller_power"]

    if mock_provider.enabled():
        base = mock_provider.default_values("chiller_power", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.chiller_power_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result


# -------pump_power (UI)-------#
def df_pump_power(plant_id):
    df = chiller_query.pump_power(plant_id)
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["pump_power"]
    
    tag_list = plant["tags"]["pump_power"]
    if mock_provider.enabled():
        values = mock_provider.default_values("pump_power", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.pump_power(plant_id)

    result = build_slot_response(df, slots)
    return result


def df_pump_power_history(plant_id, start="-24h", stop="now()", every="10m"):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["pump_power"]
    tag_list = plant["tags"]["pump_power"]

    if mock_provider.enabled():
        base = mock_provider.default_values("pump_power", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.pump_power_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result


# -------flow (UI)-------#
def df_pump_flow(plant_id):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["flow"]
    
    tag_list = plant["tags"]["flow"]
    if mock_provider.enabled():
        values = mock_provider.default_values("flow", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.pump_flow(plant_id)

    result = build_slot_response(df, slots)
    return result


def df_pump_flow_history(plant_id, start="-24h", stop="now()", every="10m"):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["flow"]
    tag_list = plant["tags"]["flow"]

    if mock_provider.enabled():
        base = mock_provider.default_values("flow", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.pump_flow_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result


# ------temp_chiller (UI)-------#
def df_chiller_temp(plant_id):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["chiller_temp"]
    
    tag_list = plant["tags"]["chiller_temp"]
    if mock_provider.enabled():
        values = mock_provider.default_values("chiller_temp", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.chiller_temp(plant_id)

    result = build_slot_response(df, slots)
    return result

def df_chiller_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["chiller_temp"]
    tag_list = plant["tags"]["chiller_temp"]

    if mock_provider.enabled():
        base = mock_provider.default_values("chiller_temp", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.chiller_temp_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result


# ------tank temp (UI)-------#
def df_chiller_tank_temp(plant_id):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["tank_temp"]
    
    tag_list = plant["tags"]["tank_temp"]
    if mock_provider.enabled():
        values = mock_provider.default_values("tank_temp", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.chiller_tank_temp(plant_id)

    result = build_slot_response(df, slots)
    return result


def df_chiller_tank_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["tank_temp"]
    tag_list = plant["tags"]["tank_temp"]

    if mock_provider.enabled():
        base = mock_provider.default_values("tank_temp", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.chiller_tank_temp_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result


# -------Thermoform (UI)-------#
def df_thermoform_power(plant_id):
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["thermoform_power"]
    
    tag_list = plant["tags"]["thermoform_power"]
    if mock_provider.enabled():
        values = mock_provider.default_values("thermoform_power", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.thermoform_power(plant_id)

    result = build_slot_response(df, slots)
    return result


def df_thermoform_power_history(plant_id, start="-24h", stop="now()", every="10m"): 
    plant = config.get_plant(plant_id)
    slots = plant["ui_slots"]["thermoform_power"]
    tag_list = plant["tags"]["thermoform_power"]

    if mock_provider.enabled():
        base = mock_provider.default_values("thermoform_power", tag_list)
        df = mock_provider.history_df(tag_list, base_by_tag=base, start=start, every=every, jitter=1.0)
    else:
        df = chiller_query.thermoform_power_history(plant_id, start=start, stop=stop, every=every)

    result = pivot_history_to_slot_records(df, slots)
    return result

# -------------------- internal (by tag) helpers for analytics --------------------
def _snap_chiller_power_by_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["chiller_power"]
    if mock_provider.enabled():
        values = mock_provider.default_values("chiller_power", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.chiller_power(plant_id)
    return build_param_response(df, include_total=True)


def _snap_pump_flow_by_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["flow"]
    if mock_provider.enabled():
        values = mock_provider.default_values("flow", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.pump_flow(plant_id)
    return build_param_response(df, include_total=False)


def _snap_tank_temp_by_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["tank_temp"]
    if mock_provider.enabled():
        values = mock_provider.default_values("tank_temp", tag_list)
        df = mock_provider.oneshot_df(tag_list, values)
    else:
        df = chiller_query.chiller_tank_temp(plant_id)
    return build_param_response(df, include_total=False)



# -------------------- cooling capa / COP / suggestion / limit --------------------
def kw_cooling(flow_m3h: float, dt_c: float) -> float:
    RHO = 997.0
    CP = 4.186
    return (flow_m3h * RHO * CP * dt_c) / 3600.0

def _every_to_pandas_freq(every: str) -> str:
    """
    "10m" -> "10min", "15m" -> "15min", "1h" -> "1H"
    """
    import re
    m = re.match(r"^\s*(\d+)\s*([smhd])\s*$", str(every))
    if not m:
        return "10min"
    n = int(m.group(1))
    u = m.group(2).lower()
    return {"s": f"{n}S", "m": f"{n}min", "h": f"{n}H", "d": f"{n}D"}[u]


def df_cooling_capa_history(plant_id, start="-24h", stop="now()", every="10m"):
    plant = config.get_plant(plant_id)

    temp_tags = [t for t in plant["tags"]["tank_temp"] if t]
    flow_tags = [t for t in plant["tags"]["flow"] if t]

    # ---------- get history (mock/real) ----------
    if mock_provider.enabled():
        temp_base = mock_provider.default_values("tank_temp", temp_tags)
        flow_base = mock_provider.default_values("flow", flow_tags)

        df_temp = mock_provider.history_df(temp_tags, base_by_tag=temp_base, start=start, every=every, jitter=0.2)
        df_flow = mock_provider.history_df(flow_tags, base_by_tag=flow_base, start=start, every=every, jitter=0.5)
    else:
        df_temp = chiller_query.chiller_tank_temp_history(plant_id, start, stop, every)
        df_flow = chiller_query.pump_flow_history(plant_id, start, stop, every)

    if df_temp is None or df_temp.empty:
        return {"ok": True, "series": []}

    # ---------- normalize ts ----------
    for d in (df_temp, df_flow):
        if d is None or d.empty:
            continue
        d["ts"] = pd.to_datetime(d["ts"], utc=True, errors="coerce")
        d.dropna(subset=["ts"], inplace=True)

    raw_df = pd.concat([df_temp, df_flow], ignore_index=True)

    # ---------- pivot -> wide ----------
    wide = raw_df.pivot(index="ts", columns="Source_tag", values="value")
    wide = wide.sort_index()

    # ---------- align timeline (แก้ null/NaN จากเวลาไม่ตรงกัน) ----------
    freq = _every_to_pandas_freq(every)
    wide = wide.resample(freq).mean().ffill()

    # ---------- pick tags from cop_map ----------
    # ใช้ชุดแรกของ cop_map เป็นตัว reference (ตาม design เดิมคุณ)
    first_map = next(iter(plant["cop_map"].values()))
    t_ret_tag = first_map["t_ret"]
    t_sup_tag = first_map["t_sup"]
    flow_tag  = first_map.get("flow")  # อาจมี/ไม่มี

    # temp ต้องมีครบ
    if t_ret_tag not in wide.columns or t_sup_tag not in wide.columns:
        return {"ok": True, "series": []}

    dif_temp = wide[t_ret_tag] - wide[t_sup_tag]

    # ---------- flow series ----------
    if flow_tag and flow_tag in wide.columns:
        flow_m3h = wide[flow_tag]
    else:
        cols = [c for c in wide.columns if c in flow_tags]
        if cols:
            flow_m3h = wide[cols].sum(axis=1, min_count=1)
        else:
            flow_m3h = pd.Series(150.0, index=wide.index)  # fallback

    Cp = 1.163  # constant

    cooling_capa = (flow_m3h * Cp * dif_temp).replace([np.inf, -np.inf], np.nan)
    cooling_capa = cooling_capa.fillna(0.0)

    out = pd.DataFrame({"ts": cooling_capa.index, "cooling_capa": cooling_capa.values})
    recs = out.to_dict(orient="records")
    recs = _clean_records_for_json(recs)

    return {"ok": True, "series": recs}


def df_cop(plant_id):
    pw = _snap_chiller_power_by_tag(plant_id)
    fl = _snap_pump_flow_by_tag(plant_id)
    tp = _snap_tank_temp_by_tag(plant_id)

    if not pw.get("ok") or not fl.get("ok") or not tp.get("ok"):
        return {"ok": False, "error": "missing snapshot"}

    plant = config.get_plant(plant_id)
    MAP = plant["cop_map"]

    def getv(payload, tag):
        return payload["param"][tag]["data"]

    out = {}
    for name, m in MAP.items():
        p_kw  = float(getv(pw, m["power"]))
        f_m3h = float(getv(fl, m["flow"])) if m.get("flow") in fl.get("param", {}) else 150.0
        t_ret = float(getv(tp, m["t_ret"]))
        t_sup = float(getv(tp, m["t_sup"]))

        dt = t_ret - t_sup
        q_kw = kw_cooling(f_m3h, dt)
        cop = (q_kw / p_kw) if p_kw > 30 else None
        out[name] = {"COP": cop}

    ts = max(pw["ts"], fl["ts"], tp["ts"])
    return {"ok": True, "ts": ts, "data": out}


# -------------------- COST (FIX JSON) --------------------
def pump_power_cost_history(plant_id, start="-24h", stop="now()", every="10m", rate=4.0):
    """
    FIX: ห้ามคืน pandas.Series / DataFrame ไปตรงๆ -> แปลงเป็น history list[dict]
    """
    plant = config.get_plant(plant_id)
    group_tags = [t for t in plant["tags"]["pump_power"] if t]

    if mock_provider.enabled():
        base = mock_provider.default_values("pump_power", group_tags)
        hist_df = mock_provider.history_df(group_tags, base_by_tag=base, start=start, every=every, jitter=0.5)
    else:
        hist_df = chiller_query.pump_power_history(plant_id, start, stop, every)

    hist = _pivot_history_to_records(hist_df)
    df = pd.DataFrame(hist)

    if df.empty or "ts" not in df.columns:
        return {"ok": False, "error": "empty history"}

    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts").set_index("ts")
    if df.empty:
        return {"ok": False, "error": "ts parse failed or empty"}

    dt_h = df.index.to_series().diff().dt.total_seconds().div(3600).fillna(0).clip(lower=0)

    plant = config.get_plant(plant_id)
    group_tags = plant["tags"]["pump_power"]

    missing = [t for t in group_tags if t not in df.columns]
    if missing:
        return {"ok": False, "error": f"missing tags: {missing}"}

    df["kw_total"] = df[group_tags].fillna(0).sum(axis=1)
    df["kwh"] = df["kw_total"] * dt_h
    df["thb"] = df["kwh"] * float(rate)

    total_kwh = float(df["kwh"].sum())
    total_thb = float(df["thb"].sum())

    out_df = df.reset_index()[["ts", "kw_total", "kwh", "thb"]]
    history = out_df.to_dict(orient="records")
    history = _clean_records_for_json(history)

    return {
        "ok": True,
        "rate": float(rate),
        "summary": {"total_kwh": total_kwh, "total_thb": total_thb},
        "start_iso": _iso_ts(df.index.min()),
        "end_iso": _iso_ts(df.index.max()),
        "history": history,
    }


def predict_cost_history(plant_id, start="-24h", stop="now()", every="10m", rate=4.0, rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, float(rpm_drop)))
    raw = pump_power_cost_history(plant_id, start, stop, every, rate)
    if not raw.get("ok"):
        return raw

    power_ratio = rpm_drop ** 3
    saving_rate = (1.0 - power_ratio) * 100.0

    cost_before = float(raw["summary"]["total_thb"])
    cost_after = cost_before * power_ratio
    cost_saving = cost_before - cost_after

    return {
        "ok": True,
        "saving_rate": round(saving_rate, 2),
        "cost_before": round(cost_before, 2),
        "cost_after": round(cost_after, 2),
        "cost_saving": round(cost_saving, 2),
    }


# -------------------- suggestion / limit (ใช้ by-tag snapshot) --------------------
def suggestion(plant_id: str):

    import pandas as pd

    # ===================== EDIT HERE (ง่ายสุด) =====================
    SETPOINT_RETURN_C = 14.0     # <-- setpoint อยู่ตรงนี้เลย
    COOLING_TH_KW = 550.0
    LOAD_TH_PCT = 85.0
    RATED_KW = 250.0             # ใช้คำนวณ %load
    CHILLER_ON_TH_KW = 50.0      # ถือว่า chiller ON เมื่อ kW > ค่านี้
    EVERY = "10m"
    LOOKBACK = "-2h"
    N_UP = 3                     # กันสวิง 1->2
    N_DOWN = 6                   # กันสวิง 2->1
    # ===============================================================

    # -------- helpers --------
    def _clean_ts(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or "ts" not in df.columns:
            return pd.DataFrame()
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")
        return df

    def _last_n_all_true(series: pd.Series, n: int) -> bool:
        s = pd.to_numeric(series, errors="coerce").dropna()
        if s.empty:
            return False
        tail = s.tail(n)
        if len(tail) < n:
            return False
        return bool(tail.all())

    # -------- read plant config / tags --------
    plant = config.get_plant(plant_id)
    first_map = next(iter(plant["cop_map"].values()))
    t_ret_tag = first_map["t_ret"]
    power_tags = [m["power"] for m in plant["cop_map"].values()]

    # -------- snapshot: how many chillers are ON --------
    snap_pw = _snap_chiller_power_by_tag(plant_id)
    if not snap_pw or not snap_pw.get("ok"):
        return {"ok": True, "status": "unknown", "suggest": "-", "reason": "no snapshot power"}

    running = []
    for tag in power_tags:
        v = snap_pw.get("param", {}).get(tag, {}).get("data", 0)
        try:
            if float(v) > CHILLER_ON_TH_KW:
                running.append((tag, float(v)))
        except Exception:
            pass

    num_on = len(running)
    if num_on == 0:
        return {"ok": True, "status": "Plant close", "suggest": "-", "reason": "-"}

    ch_tags = [t for t in plant["tags"]["chiller_power"] if t]
    if mock_provider.enabled():
        base = mock_provider.default_values("chiller_power", ch_tags)
        hist_pw = mock_provider.history_df(ch_tags, base_by_tag=base, start=LOOKBACK, every=EVERY, jitter=1.0)
    else:
        hist_pw = chiller_query.chiller_power_history(plant_id, LOOKBACK, "now()", EVERY)
    df_pw = _clean_ts(pd.DataFrame(_pivot_history_to_records(hist_pw)))

    # tank temp history (wide)
    temp_tags = [t for t in plant["tags"]["tank_temp"] if t]
    if mock_provider.enabled():
        base = mock_provider.default_values("tank_temp", temp_tags)
        hist_tp = mock_provider.history_df(temp_tags, base_by_tag=base, start=LOOKBACK, every=EVERY, jitter=0.2)
    else:
        hist_tp = chiller_query.chiller_tank_temp_history(plant_id, LOOKBACK, "now()", EVERY)
    df_tp = _clean_ts(pd.DataFrame(_pivot_history_to_records(hist_tp)))

    # cooling capa history (series)
    cool = df_cooling_capa_history(plant_id, start=LOOKBACK, stop="now()", every=EVERY)
    df_cool = _clean_ts(pd.DataFrame(cool.get("series", [])))

    # -------- stable conditions (anti-flapping) --------
    def stable_load_over(on_tag: str) -> bool:
        if on_tag not in df_pw.columns:
            # fallback snapshot only
            now_kw = dict(running).get(on_tag, 0.0)
            return (now_kw / RATED_KW * 100.0) > LOAD_TH_PCT
        load_pct = pd.to_numeric(df_pw[on_tag], errors="coerce") / RATED_KW * 100.0
        return _last_n_all_true(load_pct > LOAD_TH_PCT, N_UP)

    def stable_cooling_high() -> bool:
        if df_cool.empty or "cooling_capa" not in df_cool.columns:
            return False
        s = pd.to_numeric(df_cool["cooling_capa"], errors="coerce")
        return _last_n_all_true(s > COOLING_TH_KW, N_UP)

    def stable_cooling_low_for_down() -> bool:
        if df_cool.empty or "cooling_capa" not in df_cool.columns:
            return False
        s = pd.to_numeric(df_cool["cooling_capa"], errors="coerce")
        return _last_n_all_true(s < COOLING_TH_KW, N_DOWN)

    def stable_temp_over() -> bool:
        if df_tp.empty or t_ret_tag not in df_tp.columns:
            return False
        s = pd.to_numeric(df_tp[t_ret_tag], errors="coerce")
        return _last_n_all_true(s > SETPOINT_RETURN_C, N_UP)

    # latest metrics for debug
    latest_cool = None
    if not df_cool.empty and "cooling_capa" in df_cool.columns:
        s = pd.to_numeric(df_cool["cooling_capa"], errors="coerce").dropna()
        if not s.empty:
            latest_cool = float(s.iloc[-1])

    latest_tret = None
    if not df_tp.empty and t_ret_tag in df_tp.columns:
        s = pd.to_numeric(df_tp[t_ret_tag], errors="coerce").dropna()
        if not s.empty:
            latest_tret = float(s.iloc[-1])

    # ===================== FLOWCHART =====================
    # Case: ON 2 Chiller
    if num_on >= 2:
        if stable_cooling_low_for_down():
            return {
                "ok": True,
                "status": "Now 2 Chiller ON",
                "suggest": "ON 1 Chiller",
                "reason": f"Cooling capa < {COOLING_TH_KW} (stable {N_DOWN} pts)",
                "metrics": {"num_on": num_on, "cooling_capa": latest_cool, "cool_th": COOLING_TH_KW},
            }
        return {
            "ok": True,
            "status": "Now 2 Chiller ON",
            "suggest": "Still on 2 Chiller",
            "reason": f"Cooling capa not < {COOLING_TH_KW} (stable)",
            "metrics": {"num_on": num_on, "cooling_capa": latest_cool, "cool_th": COOLING_TH_KW},
        }

    # Case: ON 1 Chiller
    on_tag, on_kw = running[0]
    load_now = (on_kw / RATED_KW * 100.0) if RATED_KW else None

    cond_load = stable_load_over(on_tag)
    cond_cool = stable_cooling_high()
    cond_temp = stable_temp_over()

    # 1) %load > 85%
    if cond_load:
        # reason แตกต่างตาม flowchart bottom boxes
        if cond_cool and cond_temp:
            reason = f"%load>{LOAD_TH_PCT}, cooling>{COOLING_TH_KW}, temp>{SETPOINT_RETURN_C}"
        elif cond_cool:
            reason = f"%load>{LOAD_TH_PCT}, cooling>{COOLING_TH_KW}"
        elif cond_temp:
            reason = f"%load>{LOAD_TH_PCT}, temp>{SETPOINT_RETURN_C}"
        else:
            reason = f"%load>{LOAD_TH_PCT}"
        return {
            "ok": True,
            "status": f"Now 1 Chiller ON ({on_tag})",
            "suggest": "ON 2 Chiller",
            "reason": reason,
            "metrics": {
                "num_on": num_on, "on_tag": on_tag, "power_kw": on_kw, "load_pct_now": load_now,
                "cooling_capa": latest_cool, "temp_return": latest_tret, "setpoint": SETPOINT_RETURN_C
            },
        }

    # 2) cooling capa > 550
    if cond_cool:
        reason = f"cooling>{COOLING_TH_KW}" + (f", temp>{SETPOINT_RETURN_C}" if cond_temp else "")
        return {
            "ok": True,
            "status": f"Now 1 Chiller ON ({on_tag})",
            "suggest": "ON 2 Chiller",
            "reason": reason,
            "metrics": {
                "num_on": num_on, "on_tag": on_tag, "power_kw": on_kw, "load_pct_now": load_now,
                "cooling_capa": latest_cool, "temp_return": latest_tret, "setpoint": SETPOINT_RETURN_C
            },
        }

    # 3) temp_return > setpoint
    if cond_temp:
        return {
            "ok": True,
            "status": f"Now 1 Chiller ON ({on_tag})",
            "suggest": "ON 2 Chiller",
            "reason": f"temp>{SETPOINT_RETURN_C}",
            "metrics": {"num_on": num_on, "on_tag": on_tag, "temp_return": latest_tret, "setpoint": SETPOINT_RETURN_C},
        }

    # 4) still on 1
    return {
        "ok": True,
        "status": f"Now 1 Chiller ON ({on_tag})",
        "suggest": "Still on 1 Chiller",
        "reason": "No trigger",
        "metrics": {
            "num_on": num_on, "on_tag": on_tag, "power_kw": on_kw, "load_pct_now": load_now,
            "cooling_capa": latest_cool, "temp_return": latest_tret, "setpoint": SETPOINT_RETURN_C
        },
    }




def limit_chiller_power_input(plant_id):
    """
    FIX: ใช้ snapshot by-tag เพื่อเช็ค online (ไม่ผูกกับ response UI)
    """
    data_ui = df_chiller_power(plant_id)
    snap = _snap_chiller_power_by_tag(plant_id)

    plant = config.get_plant(plant_id)
    ch_tags = plant["tags"]["chiller_power"]

    any_online = any(snap.get("param", {}).get(t, {}).get("online") for t in ch_tags)

    if any_online:
        data_ui["limits"] = {"low": 75.0, "high": 250.0}
    else:
        data_ui["limits"] = {"low": 0.0, "high": 0.0}

    return data_ui

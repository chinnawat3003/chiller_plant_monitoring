import math
import pandas as pd
import numpy as np

from .query import chiller_query
from . import config

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
    df = chiller_query.chiller_power(plant_id)
    slots = _plant_slots(plant_id, "chiller_power")
    result = build_slot_response(df, slots, include_total=True)

    if test_mockup:
        result = {
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "items": [
                {"id": "CH1", "label": "P2CH01", "unit": "kW", "value": 0, "online": False},
                {"id": "CH2", "label": "P2CH02", "unit": "kW", "value": 150, "online": True},
            ],
            "total": 150,
        }
    return result


def df_chiller_power_history(plant_id, start="-20d", stop="now()", every="30m"):
    df = chiller_query.chiller_power_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "chiller_power")
    return pivot_history_to_slot_records(df, slots)


# -------pump_power (UI)-------#
def df_pump_power(plant_id):
    df = chiller_query.pump_power(plant_id)
    slots = _plant_slots(plant_id, "pump_power")
    result = build_slot_response(df, slots, include_total=True)

    if test_mockup:
        result = {
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "items": [
                {"id": "P9", "label": "P2CHP09", "unit": "kW", "value": 78.9, "online": True},
                {"id": "P10", "label": "P2CHP10", "unit": "kW", "value": 0, "online": False},
                {"id": "P11", "label": "P2CHP11", "unit": "kW", "value": 90.5, "online": True},
            ],
            "total": 169.4,
        }
    return result


def df_pump_power_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_power_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "pump_power")
    return pivot_history_to_slot_records(df, slots)


# -------flow (UI)-------#
def df_pump_flow(plant_id):
    df = chiller_query.pump_flow(plant_id)
    slots = _plant_slots(plant_id, "flow")
    result = build_slot_response(df, slots, include_total=False)

    if test_mockup:
        result = {
            "ok": True,
            "ts": "2026-01-19T04:14:33.888531+00:00",
            "items": [{"id": "FLOW_RET", "label": "Return", "unit": "m³/h", "value": 150.5, "online": True}],
        }
    return result


def df_pump_flow_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.pump_flow_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "flow")
    return pivot_history_to_slot_records(df, slots)


# ------temp_chiller (UI)-------#
def df_chiller_temp(plant_id):
    df = chiller_query.chiller_temp(plant_id)
    slots = _plant_slots(plant_id, "chiller_temp")
    result = build_slot_response(df, slots, include_total=False)
    return result


def df_chiller_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_temp_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "chiller_temp")
    return pivot_history_to_slot_records(df, slots)


# ------tank temp (UI)-------#
def df_chiller_tank_temp(plant_id):
    df = chiller_query.chiller_tank_temp(plant_id)
    slots = _plant_slots(plant_id, "tank_temp")  # return/supply
    result = build_slot_response(df, slots, include_total=False)
    return result


def df_chiller_tank_temp_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.chiller_tank_temp_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "tank_temp")
    return pivot_history_to_slot_records(df, slots)


# -------Thermoform (UI)-------#
def df_thermoform_power(plant_id):
    df = chiller_query.thermoform_power(plant_id)
    slots = _plant_slots(plant_id, "thermoform_power")
    return build_slot_response(df, slots, include_total=False)


def df_thermoform_power_history(plant_id, start="-24h", stop="now()", every="10m"):
    df = chiller_query.thermoform_power_history(plant_id, start, stop, every)
    slots = _plant_slots(plant_id, "thermoform_power")
    return pivot_history_to_slot_records(df, slots)


# -------------------- internal (by tag) helpers for analytics --------------------
def _snap_chiller_power_by_tag(plant_id):
    df = chiller_query.chiller_power(plant_id)
    return build_param_response(df, include_total=True)


def _snap_pump_flow_by_tag(plant_id):
    df = chiller_query.pump_flow(plant_id)
    return build_param_response(df, include_total=False)


def _snap_tank_temp_by_tag(plant_id):
    df = chiller_query.chiller_tank_temp(plant_id)
    return build_param_response(df, include_total=False)


# -------------------- cooling capa / COP / suggestion / limit --------------------
def kw_cooling(flow_m3h: float, dt_c: float) -> float:
    RHO = 997.0
    CP = 4.186
    return (flow_m3h * RHO * CP * dt_c) / 3600.0


def df_cooling_capa_history(plant_id, start="-24h", stop="now()", every="10m"):
   
    df_temp = chiller_query.chiller_tank_temp_history(plant_id, start, stop, every)
    df_flow = chiller_query.pump_flow_history(plant_id, start, stop, every)

    Cp = 1.163  # constant (คุณปรับได้)

    for d in (df_temp, df_flow):
        d["ts"] = pd.to_datetime(d["ts"], utc=True, errors="coerce")
        d.dropna(subset=["ts"], inplace=True)
        d.sort_values("ts", inplace=True)

    raw_df = pd.concat([df_temp, df_flow], ignore_index=True).sort_values("ts")
    wide = raw_df.pivot(index="ts", columns="Source_tag", values="value")

    plant = config.get_plant(plant_id)
    t_ret = plant["cop_map"]["CH01"]["t_ret"]
    t_sup = plant["cop_map"]["CH01"]["t_sup"]
    wide["dif_temp"] = wide[t_ret] - wide[t_sup]

    flow = 150  # constant/mockup
    wide["cooling_capa"] = flow * Cp * wide["dif_temp"]

    out = wide[["cooling_capa"]].reset_index()
    recs = out.to_dict(orient="records")
    return _clean_records_for_json(recs)


def df_cop(plant_id):
    pw = _snap_chiller_power_by_tag(plant_id)
    fl = _snap_pump_flow_by_tag(plant_id)
    tp = _snap_tank_temp_by_tag(plant_id)

    if not pw or not fl or not tp or not pw.get("ok") or not fl.get("ok") or not tp.get("ok"):
        return {"ok": False, "error": "missing snapshot"}

    plant = config.get_plant(plant_id)
    MAP = plant["cop_map"]

    def getv(payload, tag):
        return payload["param"][tag]["data"]

    out = {}
    for name, m in MAP.items():
        p_kw = float(getv(pw, m["power"]))
        f_m3h = float(getv(fl, m["flow"])) if m.get("flow") in fl.get("param", {}) else 150.0
        t_ret = float(getv(tp, m["t_ret"]))
        t_sup = float(getv(tp, m["t_sup"]))

        f_m3h = 150.0  # mockup (คุณจะเปลี่ยนทีหลัง)
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


def df_pump_total_predict_history(plant_id, start="-24h", stop="now()", every="10m", rate=4.0, rpm_drop=0.8):
    rpm_drop = max(0.0, min(1.0, float(rpm_drop)))
    power_ratio = rpm_drop ** 3

    plant = config.get_plant(plant_id)
    pump_tags = plant["tags"]["pump_power"]

    # history by real tag (for sum)
    raw_hist = _pivot_history_to_records(chiller_query.pump_power_history(plant_id, start, stop, every))

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

    raw_cost = pump_power_cost_history(plant_id, start, stop, every, rate)
    if not raw_cost.get("ok"):
        return raw_cost

    cost_before = float(raw_cost["summary"]["total_thb"])
    cost_after = cost_before * power_ratio
    cost_saving = cost_before - cost_after
    saving_rate = (1.0 - power_ratio) * 100.0

    return {
        "ok": True,
        "history": _clean_records_for_json(history),
        "summary": {
            "saving_rate": round(saving_rate, 2),
            "cost_before": round(cost_before, 2),
            "cost_after": round(cost_after, 2),
            "cost_saving": round(cost_saving, 2),
        },
    }


# -------------------- suggestion / limit (ใช้ by-tag snapshot) --------------------
def suggestion(plant_id):
    plant = config.get_plant(plant_id)
    cop_map = plant["cop_map"]
    power_tags = [m["power"] for m in cop_map.values()]

    def _clean_ts(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or "ts" not in df.columns:
            return pd.DataFrame()
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")
        return df

    def pull_data(start="-12h", stop="now()", every="15m"):
        ch_power_df = _clean_ts(pd.DataFrame(_pivot_history_to_records(
            chiller_query.chiller_power_history(plant_id, start, stop, every)
        )))
        ch_cooling_df = _clean_ts(pd.DataFrame(df_cooling_capa_history(plant_id, start, stop, every)))

        if ch_power_df.empty:
            return pd.DataFrame()

        raw_df = ch_power_df
        if not ch_cooling_df.empty:
            raw_df = pd.merge(raw_df, ch_cooling_df, on="ts", how="outer")

        return raw_df.sort_values("ts")

    def check_status_chiller_on(th_kw=50.0):
        snap = _snap_chiller_power_by_tag(plant_id)
        if not snap or not snap.get("ok"):
            return {"ok": False, "num_chiller_on": 0}

        num_on = 0
        for tag in power_tags:
            v = snap.get("param", {}).get(tag, {}).get("data", 0)
            if isinstance(v, (int, float)) and float(v) > th_kw:
                num_on += 1
        return {"ok": True, "num_chiller_on": num_on}

    def on_2_condition(start="-12h", stop="now()", every="20m", cooling_low=686):
        df = _clean_ts(pd.DataFrame(df_cooling_capa_history(plant_id, start, stop, every)))
        if df.empty or "cooling_capa" not in df.columns:
            return {"ok": True, "status": "Now 2 Chiller ON", "suggest": "-", "reason": "no cooling data"}

        all_low = (pd.to_numeric(df["cooling_capa"], errors="coerce").dropna() < cooling_low).all()
        if all_low:
            return {"ok": True, "status": "Now 2 Chiller ON", "suggest": "ON 1 Chiller",
                    "reason": f"Cooling capa < {cooling_low} (all points)"}
        return {"ok": True, "status": "Now 2 Chiller ON", "suggest": "-", "reason": f"Cooling capa >= {cooling_low} (some points)"}

    def on_1_condition(start="-1h", stop="now()", every="15m", cooling_low=686):
        power_peak = 250.0
        percent_load = 85.0

        df = pull_data(start=start, stop=stop, every=every)
        if df.empty:
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "no history"}

        snap = _snap_chiller_power_by_tag(plant_id)
        if not snap or not snap.get("ok"):
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "no snapshot"}

        on_tag, on_val = None, 0.0
        for tag in power_tags:
            v = float(snap.get("param", {}).get(tag, {}).get("data", 0))
            if v > 50:
                on_tag, on_val = tag, v
                break

        if on_tag is None:
            return {"ok": True, "status": "Now 1 Chiller ON", "suggest": "-", "reason": "cannot detect running chiller"}

        if "cooling_capa" in df.columns:
            last_c = pd.to_numeric(df["cooling_capa"], errors="coerce").dropna()
            if not last_c.empty and (last_c > cooling_low).all():
                return {"ok": True, "status": f"Now 1 Chiller ON ({on_tag})",
                        "suggest": "ON 2 Chiller", "reason": f"Cooling capa > {cooling_low}"}

        if on_tag in df.columns:
            series = pd.to_numeric(df[on_tag], errors="coerce").dropna()
            if not series.empty:
                over = ((series / power_peak) * 100.0 > percent_load).all()
                if over:
                    return {"ok": True, "status": f"Now 1 Chiller ON ({on_tag})",
                            "suggest": "ON 2 Chiller", "reason": f"%load > {percent_load}%"}

        return {"ok": True, "status": f"Now 1 Chiller ON ({on_tag})",
                "suggest": "-", "reason": f"load={round((on_val/power_peak)*100, 2)}% and cooling not over"}

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

# mock_provider.py
import os
import re
import numpy as np
import pandas as pd

MOCK_MODE = os.getenv("MOCK_MODE", "1") == "1"

def enabled() -> bool:
    return MOCK_MODE

def _clean_tag_list(tag_list):
    """กันเคส [] หรือ [""] หรือ None"""
    if not tag_list:
        return []
    return [t for t in tag_list if isinstance(t, str) and t.strip()]

def _extract_index(tag: str) -> int:
    # ช่วยเรียง CH01/CH02/P01/TF01 ถ้าหาไม่เจอให้ท้ายสุด
    m = re.search(r"(?:ch|p|pump|tf)\s*0*(\d+)", tag, re.IGNORECASE)
    return int(m.group(1)) if m else 9999

def _parse_every_to_freq(every: str) -> str:
    m = re.match(r"^\s*(\d+)\s*([smhd])\s*$", str(every))
    if not m:
        return "15min"
    n = int(m.group(1))
    unit = m.group(2)
    return {"s": f"{n}S", "m": f"{n}min", "h": f"{n}H", "d": f"{n}D"}[unit]

def range_start_to_hours(start: str, default_hours: float = 24.0) -> float:
    # "-24h" -> 24, "-7d" -> 168, "-90m" -> 1.5
    s = str(start).strip()
    m = re.match(r"^\s*-\s*(\d+)\s*([smhd])\s*$", s, re.IGNORECASE)
    if not m:
        return float(default_hours)
    n = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "s": return n / 3600.0
    if unit == "m": return n / 60.0
    if unit == "h": return n
    if unit == "d": return n * 24.0
    return float(default_hours)

def default_values(group_name: str, tag_list: list[str]) -> dict[str, float]:
    """
    กำหนดค่า mock เบื้องต้น “ตามกลุ่ม” โดยใช้ tag_list จริงจาก config (ไม่ hardcode ชื่อ plant)
    """
    tag_list = _clean_tag_list(tag_list)
    if not tag_list:
        return {}

    group = (group_name or "").lower()
    sorted_tags = sorted(tag_list, key=_extract_index)
    first = sorted_tags[0]
    second = sorted_tags[1] if len(sorted_tags) > 1 else None
    third = sorted_tags[2] if len(sorted_tags) > 2 else None

    if "chiller" in group and "power" in group:
        return {
            t: (200 if t == first else (0.0 if (second and t == second) else 0.0)) 
            for t in tag_list
        } 

    if "pump" in group and "power" in group:
        return {
            t: (20.0 if t == first else (15.0 if (second and t == second) else (13.0 if (third and t == third) else 0.0))) 
            for t in tag_list
        }

    if "flow" in group:
        return {t: (380.0 if (t == first or (second and t == second)) else 0.0) for t in tag_list}

    if "tank_temp" in group:
        
        return {
            t: (12.0 if t == first else (10.0 if (second and t == second) else 0.0))
            for t in tag_list
        }

    if "thermoform_power" in group and "power" in group:
        return {
            t: (80 if t == first else (90.0 if (second and t == second) else (100.0 if (third and t == third) else 0.0))) 
            for t in tag_list
        }

    return {t: 0.0 for t in tag_list}

def oneshot_df(tag_list: list[str], values_by_tag: dict[str, float], ts=None) -> pd.DataFrame:
    """snapshot: timestamp เดียว หลายแถวตาม tag"""
    tag_list = _clean_tag_list(tag_list)
    ts = pd.Timestamp.now() if ts is None else pd.to_datetime(ts)
    rows = [{"ts": ts, "value": float(values_by_tag.get(t, 0.0)), "Source_tag": t} for t in tag_list]
    return (pd.DataFrame(rows, columns=["ts", "value", "Source_tag"])
              .sort_values(["ts", "Source_tag"])
              .reset_index(drop=True))

def history_df(
    tag_list: list[str],
    base_by_tag: dict[str, float],
    start="-24h",
    every="15m",
    jitter=0.5,
    seed=None,
) -> pd.DataFrame:
    
    tag_list = _clean_tag_list(tag_list)
    if not tag_list:
        return pd.DataFrame(columns=["ts", "value", "Source_tag"])

    if seed is not None:
        np.random.seed(seed)

    hours_back = range_start_to_hours(start, 24.0)
    freq = _parse_every_to_freq(every)
    end = pd.Timestamp.now()
    begin = end - pd.Timedelta(hours=float(hours_back))
    ts_index = pd.date_range(start=begin, end=end, freq=freq)

    rows = []
    for t in tag_list:
        base = float(base_by_tag.get(t, 0.0))
        noise = np.random.normal(0.0, float(jitter), size=len(ts_index))
        vals = np.maximum(base + noise, 0.0)
        rows.extend({"ts": tt, "value": float(vv), "Source_tag": t} for tt, vv in zip(ts_index, vals))

    return (pd.DataFrame(rows, columns=["ts", "value", "Source_tag"])
              .sort_values(["ts", "Source_tag"])
              .reset_index(drop=True))

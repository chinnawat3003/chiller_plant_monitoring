from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .query import chiller_query
from . import control_service
import re
from typing import Optional


app = FastAPI(title="Chiller Monitoring")

def _range_args(from_ts: Optional[str], to_ts: Optional[str], fallback_start: str):
    if from_ts and to_ts:
        start = f'time(v: "{from_ts}")'
        stop = f'time(v: "{to_ts}")'
    else:
        start = fallback_start
        stop = "now()"
    return start, stop


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/chill_pw")
def api_chiller_pw():
    res = control_service.df_chiller_power()
    print(res)
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}


@app.get("/api/pump_pw")
def api_pump_pw():
    res = control_service.df_pump_power()
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}

@app.get("/api/pump_flow")
def api_pump_flow():
    res = control_service.df_pump_flow()
    return {"ok": True, **res}

@app.get("/api/chiller_temp")
def df_chiller_temp():
    res = control_service.df_chiller_temp()
    return {"ok": True, **res}

@app.get("/api/cop")
def api_cop():
    res = control_service.df_cop()
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}

@app.get("/api/chiller_pw_history")
def api_chiller_pw_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_chiller_power_history(start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/pump_pw_history")
def api_pump_pw_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_pump_power_history(start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/pump_flow_history")
def api_pump_flow_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_pump_flow_history(start=s, stop=e, every=every)
    return {"ok": True, "history": res}


@app.get("/api/chiller_temp_history")
def api_chiller_temp_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_chiller_temp_history(start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/pump_power_cost_history")
def api_pump_power_cost_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
    rate: float = Query(4.0)
):

    s, e = _range_args(from_ts, to_ts, start)
    return control_service.pump_power_cost_history(start=s, stop=e, every=every, rate=rate)



@app.get("/api/pump_total_predict_history")
def api_pump_total_predict_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
    rate: float = Query(4.0),
    rpm_drop: float = Query(0.8),
):
    s, e = _range_args(from_ts, to_ts, start)
    return control_service.df_pump_total_predict_history(start=s, stop=e, every=every, rate=rate, rpm_drop=rpm_drop)


@app.get("/api/recommend")
def api_suggestion():
    return control_service.suggestion()




#.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000


from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from .query import chiller_query
from . import control_service
from . import config
import re
from typing import Optional


app = FastAPI(title="Chiller Monitoring")


def get_plant_id(x_plant_id: str | None = Header(default=None)):
    """Read plant id from request header `X-Plant-ID`.
    Falls back to config.DEFAULT_PLANT when header is not provided.
    """
    return x_plant_id or config.DEFAULT_PLANT


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
def api_chiller_pw(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_chiller_power(plant_id)
    print(res)
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}


@app.get("/api/pump_pw")
def api_pump_pw(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_pump_power(plant_id)
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}

@app.get("/api/pump_flow")
def api_pump_flow(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_pump_flow(plant_id)
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}

@app.get("/api/chiller_temp")
def df_chiller_temp(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_chiller_temp(plant_id)
    return {"ok": True, **res}

@app.get("/api/thermoform_power")
def api_thermoform_power(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_thermoform_power(plant_id)
    
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}


@app.get("/api/chiller_tank_temp")
def api_chiller_tank_temp(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_chiller_tank_temp(plant_id)
    
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}


@app.get("/api/cop")
def api_cop(plant_id: str = Depends(get_plant_id)):
    res = control_service.df_cop(plant_id)
    if not res:
        raise HTTPException(404, "no data")
    return {"ok": True, **res}



@app.get("/api/chiller_pw_history")
def api_chiller_pw_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_chiller_power_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/pump_pw_history")
def api_pump_pw_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_pump_power_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/pump_flow_history")
def api_pump_flow_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_pump_flow_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}


@app.get("/api/chiller_temp_history")
def api_chiller_temp_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_chiller_temp_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/thermoform_power_history")
def api_thermoform_power_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_thermoform_power_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}

@app.get("/api/chiller_tank_temp_history")
def api_chiller_tank_temp_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
):
    s, e = _range_args(from_ts, to_ts, start)
    res = control_service.df_chiller_tank_temp_history(plant_id, start=s, stop=e, every=every)
    return {"ok": True, "history": res}



@app.get("/api/pump_power_cost_history")
def api_pump_power_cost_history(
    plant_id: str = Depends(get_plant_id),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    start: str = Query("-24h"),
    every: str = Query("10m"),
    rate: float = Query(4.0)
):

    s, e = _range_args(from_ts, to_ts, start)
    return control_service.pump_power_cost_history(plant_id, start=s, stop=e, every=every, rate=rate)



@app.get("/api/recommend")
def api_suggestion(plant_id: str = Depends(get_plant_id)):
    return control_service.suggestion(plant_id)


@app.get("/api/limit_chiller_power_input")
def api_limit_chiller_power_input(plant_id: str = Depends(get_plant_id)):
    return control_service.limit_chiller_power_input(plant_id)

#.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000


import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import pandas as pd
load_dotenv()  # อ่าน backend/.env

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

missing = [k for k, v in {
    "INFLUX_URL": INFLUX_URL,
    "INFLUX_TOKEN": INFLUX_TOKEN,
    "INFLUX_ORG": INFLUX_ORG,
    "INFLUX_BUCKET": BUCKET,
}.items() if not v]

if missing:
    raise RuntimeError(f"Missing env: {', '.join(missing)}")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=60_000)
query_api = client.query_api()

def flux_to_df(flux: str) -> pd.DataFrame:
    df = query_api.query_data_frame(flux)

    # บางครั้งได้ list[DataFrame] (หลาย table) -> concat
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    if df is None or df.empty:
        return pd.DataFrame(columns=["ts", "value"])

    # เอาคอลัมน์หลัก
    keep = [c for c in ["_time", "_value", "_measurement", "_field", "Source_tag"] if c in df.columns]
    df = df[keep].copy()

    # rename ให้ใช้ง่าย
    df = df.rename(columns={"_time": "ts", "_value": "value"})
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").reset_index(drop=True)
    return df


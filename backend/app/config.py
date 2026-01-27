# thresholds.py
DEFAULT_THRESHOLD = 8.0

THRESHOLD_BY_TAG = {
    "Winenergy.P2CHP09.kW": 10.0,
    "Winenergy.P2CHP10.kW": 10.0,
    "Winenergy.P2CHP11.kW": 10.0,

    # ตัวอย่างอื่น ๆ
    "Pump.Total.kW": 5.0,
    "Chiller.Temp.C": 5.0,
}

# --- recommendation thresholds (for LLM decision) ---
RECOMMEND_THRESHOLDS_BY_PLANT = {
    "P1": {
        "setpoint_return_c": 14.0,
        "cooling_th_kw": 550.0,
        "load_th_pct": 85.0,
        "rated_kw": 250.0,
        "chiller_on_th_kw": 50.0,
        "lookback": "-2h",
        "every": "10m",
        "n_up": 3,
        "n_down": 6,
    },
    "P2": {
        "setpoint_return_c": 14.0,
        "cooling_th_kw": 550.0,
        "load_th_pct": 85.0,
        "rated_kw": 250.0,
        "chiller_on_th_kw": 50.0,
        "lookback": "-2h",
        "every": "10m",
        "n_up": 3,
        "n_down": 6,
    },
}

def get_recommend_thresholds(plant_id: str | None = None) -> dict:
    pid = plant_id or DEFAULT_PLANT
    return RECOMMEND_THRESHOLDS_BY_PLANT.get(pid, RECOMMEND_THRESHOLDS_BY_PLANT[DEFAULT_PLANT])

PLANTS = {
    "P1": {
        "name": "plant 1",
        "tags": {
            "chiller_power": [
                "Winenergy.P1CH01.kW", 
                "Winenergy.P1CH02.kW"
                ],
            "pump_power": [
                ""
                ],
            "flow": [
                "Winenergy.P1CH01.Flow_Counter"
                ],
            "tank_temp": [
                "Chiller.PLANT_Node3.CLG1_TANK1_CHR_TEMP", 
                "Chiller.PLANT_Node3.CLG1_TANK1_CHS_TEMP"
                ],
            "chiller_temp": [
                "Chiller.PLANT_Node3.CLG1_CH01_EVAP_ENTERING_WATER_TEMP_1",
                "Chiller.PLANT_Node3.CLG1_CH01_EVAP_LEAVING_WATER_TEMP_1",
                "Chiller.PLANT_Node3.CLG1_CH02_EVAP_ENTERING_WATER_TEMP_1",
                "Chiller.PLANT_Node3.CLG1_CH02_EVAP_LEAVING_WATER_TEMP_1",
                ],
            "thermoform_power":[
                
            ],

        },
        "cop_map": { 
            "CH01": {
                "power": "Winenergy.P1CH01.kW", 
                "flow": "Winenergy.P1CH01.Flow_Counter", 
                "t_ret": "Chiller.PLANT_Node3.CLG1_TANK1_CHS_TEMP",
                "t_sup": "Chiller.PLANT_Node3.CLG1_TANK1_CHR_TEMP",
                
                },
            "CH02": {
                "power": "Winenergy.P1CH02.kW", 
                "flow": "Winenergy.P1CH01.Flow_Counter", 
                "t_ret": "Chiller.PLANT_Node3.CLG1_TANK1_CHS_TEMP",
                "t_sup": "Chiller.PLANT_Node3.CLG1_TANK1_CHR_TEMP",
                },  
        },
        "ui_slots": {
            "chiller_power": [
                {"id": "CH1", "label": "P1CH1", "tag": "Winenergy.P1CH01.kW", "unit": "kW"},
                {"id": "CH2", "label": "P1CH02", "tag": "Winenergy.P1CH02.kW", "unit": "kW"}
            ],
            "pump_power": [
            
            ],
            "chiller_temp": [
                {"id":"CH1_IN",  "label":"CH01 Entering", "unit":"°C", "tag":"Chiller.PLANT_Node3.CLG1_CH01_EVAP_ENTERING_WATER_TEMP_1"},
                {"id":"CH1_OUT", "label":"CH01 Leaving",  "unit":"°C", "tag":"Chiller.PLANT_Node3.CLG1_CH01_EVAP_LEAVING_WATER_TEMP_1"},
                {"id":"CH2_IN",  "label":"CH02 Entering", "unit":"°C", "tag":"Chiller.PLANT_Node3.CLG1_CH02_EVAP_ENTERING_WATER_TEMP_1"},
                {"id":"CH2_OUT", "label":"CH02 Leaving",  "unit":"°C", "tag":"Chiller.PLANT_Node3.CLG1_CH02_EVAP_LEAVING_WATER_TEMP_1"},
            ],
            "tank_temp": [
                {"id": "RETURN", "label": "Return", "tag": "Chiller.PLANT_Node3.CLG1_TANK1_CHR_TEMP", "unit": "°C"},
                {"id": "SUPPLY", "label": "Supply", "tag": "Chiller.PLANT_Node3.CLG1_TANK1_CHS_TEMP", "unit": "°C"},
            ],
            "flow": [
                {"id": "FLOW_RET", "label": "Return", "tag": "Winenergy.P1CH01.Flow_Counter", "unit": "m³/h"},
            ],
            "thermoform_power": [
            ],
        }
    },
    "P2": {
        "name": "plant 2",
        "tags": {
            "chiller_power": [
                "Winenergy.P2CH01.kW", 
                "Winenergy.P2CH02.kW"
                ],
            "pump_power": [
                "Winenergy.P2CHP09.kW", 
                "Winenergy.P2CHP10.kW", 
                "Winenergy.P2CHP11.kW"
                ],
            "flow": [
                "Winenergy.P2CH01.Flow_Counter"
                ],
            "tank_temp": [
                "Chiller.PLANT_Node2.CLG2_TEMP_CHWR", 
                "Chiller.PLANT_Node2.CLG2_TEMP_CHWS"
                ],
            "chiller_temp": [
                "Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1",
                "Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1",
                "Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1",
                "Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1",
                ],
            "thermoform_power":[
                "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal",
                "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal",
                "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal"
            ]
        },
        "cop_map": { 
            "CH01": {
                "power": "Winenergy.P2CH01.kW", 
                "flow": "Winenergy.P2CH01.Flow_Counter", 
                "t_ret": "Chiller.PLANT_Node2.CLG2_TEMP_CHWR",
                "t_sup": "Chiller.PLANT_Node2.CLG2_TEMP_CHWS"
                },
            "CH02": {
                "power": "Winenergy.P2CH02.kW", 
                "flow": "Winenergy.P2CH01.Flow_Counter", 
                "t_ret": "Chiller.PLANT_Node2.CLG2_TEMP_CHWR",
                "t_sup": "Chiller.PLANT_Node2.CLG2_TEMP_CHWS"
                },  
        },
        "ui_slots": {
            "chiller_power": [
                {"id": "CH1", "label": "P2CH1", "tag": "Winenergy.P2CH01.kW", "unit": "kW"},
                {"id": "CH2", "label": "P2CH02", "tag": "Winenergy.P2CH02.kW", "unit": "kW"}
            ],
            "pump_power": [
                {"id": "P9",  "label": "P2CHP09", "tag": "Winenergy.P2CHP09.kW", "unit": "kW"},
                {"id": "P10", "label": "P2CHP10", "tag": "Winenergy.P2CHP10.kW", "unit": "kW"},
                {"id": "P11", "label": "P2CHP11", "tag": "Winenergy.P2CHP11.kW", "unit": "kW"},
            ],
            "chiller_temp": [
                {"id":"CH1_IN",  "label":"CH01 Entering", "unit":"°C", "tag":"Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1"},
                {"id":"CH1_OUT", "label":"CH01 Leaving",  "unit":"°C", "tag":"Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1"},
                {"id":"CH2_IN",  "label":"CH02 Entering", "unit":"°C", "tag":"Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1"},
                {"id":"CH2_OUT", "label":"CH02 Leaving",  "unit":"°C", "tag":"Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1"},
            ],
            "tank_temp": [
                {"id": "RETURN", "label": "Return", "tag": "Chiller.PLANT_Node2.CLG2_TEMP_CHWR", "unit": "°C"},
                {"id": "SUPPLY", "label": "Supply", "tag": "Chiller.PLANT_Node2.CLG2_TEMP_CHWS", "unit": "°C"},
            ],
            "flow": [
                {"id": "FLOW_RET", "label": "Return", "tag": "Winenergy.P2CH01.Flow_Counter", "unit": "m³/h"},
            ],
            "thermoform_power": [
                {"id":"TF4", "label":"Thermoform 4", "unit":"kW", "tag":"Modbus_TF4.18CT1.Main_Thermoform_kW_Cal"},
                {"id":"TF5", "label":"Thermoform 5", "unit":"kW", "tag":"Modbus_TF5.18CT1.Main_Thermoform_kW_Cal"},
                {"id":"TF7", "label":"Thermoform 7", "unit":"kW", "tag":"Modbus_TF7.18CT1.Main_Thermoform_kW_Cal"},
            ],
        }
        
    }
}

DEFAULT_PLANT = "P2"

def get_plant(plant_id: str | None = None) -> dict:
    pid = plant_id or DEFAULT_PLANT
    plant = PLANTS.get(pid)
    if not plant:
        raise ValueError(f"Unknown plant_id: {pid}. Available: {list(PLANTS.keys())}")
    return plant
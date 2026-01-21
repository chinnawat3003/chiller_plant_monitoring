# thresholds.py
DEFAULT_THRESHOLD = 10.0

THRESHOLD_BY_TAG = {
    "Winenergy.P2CHP09.kW": 10.0,
    "Winenergy.P2CHP10.kW": 10.0,
    "Winenergy.P2CHP11.kW": 10.0,

    # ตัวอย่างอื่น ๆ
    "Pump.Total.kW": 5.0,
    "Chiller.Temp.C": 10.0,
}

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
            "TF":[
                
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
            "TF":[
                "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal",
                "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal",
                "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal"
            ]
        },
        "cop_map": { 
            "CH01": {
                "power": "Winenergy.P2CH01.kW", 
                "flow": "Winenergy.P1CH01.Flow_Counter", 
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
    }
}
DEFAULT_PLANT = "P1"

def get_plant(plant_id: str | None = None) -> dict:
    pid = plant_id or DEFAULT_PLANT
    plant = PLANTS.get(pid)
    if not plant:
        raise ValueError(f"Unknown plant_id: {pid}. Available: {list(PLANTS.keys())}")
    return plant
from .influx_client import query_api, BUCKET, flux_to_df

#Chiller_power
chiller_power_tag = [
    "Winenergy.P2CH01.kW",
    "Winenergy.P2CH02.kW"
]

#oneshot
def chiller_power():
    tags = '["' + '","'.join(chiller_power_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)

#history
def chiller_power_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in chiller_power_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#Pump_power
pump_power_tag = [
    "Winenergy.P2CHP09.kW",
    "Winenergy.P2CHP10.kW",
    "Winenergy.P2CHP11.kW"
]
def pump_power():
    tags = '["' + '","'.join(pump_power_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)

#history
def pump_power_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in pump_power_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#Flow
#need to convert from counter to m3/h first
flow_tag = [
    "Winenergy.P1CH01.Flow_Counter",
    "Winenergy.P2CH01.Flow_Counter"
]
def pump_flow():
    tags = '["' + '","'.join(flow_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r    ["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))   
        |> group(columns:["Source_tag"])
        |> sort(columns: ["_time"])
        |> derivative(unit: 1h, nonNegative: true)
        '''
    
    return flux_to_df(flux)
#history
def pump_flow_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in flow_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        |> group(columns:["Source_tag"])
        |> sort(columns: ["_time"])
        |> derivative(unit: 1h, nonNegative: true)
        '''
    return flux_to_df(flux)


#temp chiller
temp_tag = [
    "Chiller.PLANT_Node2.CLG2_CH01_EVAP_ENTERING_WATER_TEMP_1",
    "Chiller.PLANT_Node2.CLG2_CH01_EVAP_LEAVING_WATER_TEMP_1",
    "Chiller.PLANT_Node2.CLG2_CH02_EVAP_ENTERING_WATER_TEMP_1",
    "Chiller.PLANT_Node2.CLG2_CH02_EVAP_LEAVING_WATER_TEMP_1",
    

]
def chiller_temp():
    tags = '["' + '","'.join(temp_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)
#history
def chiller_temp_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in temp_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#chiller_tank_temp
tank_tag = [
    "Chiller.PLANT_Node2.CLG2_TEMP_CHWR",
    "Chiller.PLANT_Node2.CLG2_TEMP_CHWS"
]
#history
def chiller_tank_temp():
    tags = '["' + '","'.join(tank_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)

def chiller_tank_temp_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tank_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#Thermoform
tf_tag = [
    "Modbus_TF4.18CT1.Main_Thermoform_kW_Cal",
    "Modbus_TF5.18CT1.Main_Thermoform_kW_Cal",
    "Modbus_TF7.18CT1.Main_Thermoform_kW_Cal"

]

def thermoform_power():
    tags = '["' + '","'.join(tf_tag) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-5m)
        |> filter(fn:(r)=> r["_measurement"]=="PwrMeter")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)

#history
def thermoform_power_history(start="-24h", stop="now()", every="15m"):
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tf_tag])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "PwrMeter" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


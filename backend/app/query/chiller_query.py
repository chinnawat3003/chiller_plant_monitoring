from .influx_client import query_api, BUCKET, flux_to_df
from .. import config
#Chiller_power

def chiller_power_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["chiller_power"]
    return tag_list


#oneshot
def chiller_power(plant_id):
    tag_list = chiller_power_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
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
def chiller_power_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = chiller_power_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#Pump_power

def pump_power_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["pump_power"]
    return tag_list

def pump_power(plant_id):
    tag_list = pump_power_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
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
def pump_power_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = pump_power_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

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

def flow_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["flow"]
    return tag_list

def pump_flow(plant_id):
    tag_list = flow_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-15m)
        |> filter(fn:(r)=> r["_measurement"]=="UTIL")
        |> filter(fn:(r)=> r    ["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))   
        |> group(columns:["Source_tag"])
        |> sort(columns: ["_time"])
        |> derivative(unit: 1h, nonNegative: true)
        |> last()
        '''
    
    return flux_to_df(flux)

#history
def pump_flow_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = flow_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

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

def temp_chiller_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["chiller_temp"]
    return tag_list

def chiller_temp(plant_id):
    tag_list = temp_chiller_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
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
def chiller_temp_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = temp_chiller_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#chiller_tank_temp
def temp_tank_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["tank_temp"]
    return tag_list

def chiller_tank_temp(plant_id):
    tag_list = temp_tank_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
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
def chiller_tank_temp_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = temp_tank_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "UTIL" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


#Thermoform
def temp_tf_tag(plant_id):
    plant = config.get_plant(plant_id)
    tag_list = plant["tags"]["thermoform_power"]
    return tag_list

def thermoform_power(plant_id):
    tag_list = temp_tf_tag(plant_id)
    tags = '["' + '","'.join(tag_list) + '"]'
    
    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start:-20m)
        |> filter(fn:(r)=> r["_measurement"]=="PwrMeter")
        |> filter(fn:(r)=> r["_field"]=="value")
        |> filter(fn:(r)=> contains(value: r["Source_tag"], set: {tags}))
        |> group(columns:["Source_tag"])
        |> last()
        '''
    
    return flux_to_df(flux)

#history
def thermoform_power_history(plant_id, start="-24h", stop="now()", every="15m"):
    tag_list = temp_tf_tag(plant_id)
    tag_filter = " or ".join([f'r["Source_tag"] == "{t}"' for t in tag_list])

    flux = f'''
        from(bucket:"{BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn:(r) => r["_measurement"] == "PwrMeter" and r["_field"] == "value" and ({tag_filter}))
        |> aggregateWindow(every: {every}, fn: last, createEmpty: false)
        |> keep(columns: ["_time", "_value", "Source_tag"])
        '''
    return flux_to_df(flux)


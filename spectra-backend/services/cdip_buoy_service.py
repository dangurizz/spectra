from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

CDIP_THREDDS_URL = "http://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/realtime/{buoy_id}p1_rt.nc.ascii"


def _parse_time_array(lines: List[str], variable_name: str) -> List[int]:
    """
    Parse a time array from OPeNDAP ASCII output.
    
    Format example:
    Dataset {
        Int32 waveTime[waveTime = 52434];
    } cdip/realtime/100p1_rt.nc;
    ---------------------------------------------
    waveTime[52434]
    1095350400, 1095352200, ...
    """
    data_started = False
    values = []
    
    # Identify the header line that precedes the data
    # It usually looks like "variable_name[size]"
    # But checking for the separator "---------------------------------------------" 
    # and then expecting the variable name is safer.
    
    separator_found = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("---------------------------------------------"):
            separator_found = True
            continue
            
        if not separator_found:
            continue
            
        if line.startswith(f"{variable_name}["):
            data_started = True
            continue
            
        if data_started:
            # This line contains data (comma separated)
            parts = line.split(',')
            for part in parts:
                part = part.strip()
                if part:
                    try:
                        values.append(int(part))
                    except ValueError:
                        pass
    
    return values


def _parse_value(lines: List[str], variable_name: str) -> Optional[float]:
    """
    Parse a single float value from OPeNDAP ASCII output.
    """
    separator_found = False
    data_started = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("---------------------------------------------"):
            separator_found = True
            continue
            
        if not separator_found:
            continue
            
        if line.startswith(f"{variable_name}["):
            data_started = True
            continue
            
        if data_started:
            try:
                # Remove trailing comma if present
                val_str = line.rstrip(',')
                return float(val_str)
            except ValueError:
                return None
                
    return None


def get_cdip_data(buoy_id: str, timestamp: datetime) -> Optional[Dict[str, float]]:
    """
    Fetch CDIP buoy data closest to the given timestamp.
    
    Args:
        buoy_id: CDIP Station ID (e.g. "100", "028")
        timestamp: The target datetime
        
    Returns:
        Dictionary with keys: wave_height, wave_period, wave_direction, water_temp
        or None if data is unavailable or request fails.
    """
    # Ensure timestamp is UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)
        
    target_ts = int(timestamp.timestamp())
    
    # 1. Fetch time arrays
    # We fetch both waveTime and sstTime because they might have different indices/availability
    url = f"{CDIP_THREDDS_URL.format(buoy_id=buoy_id)}?waveTime,sstTime"
    
    try:
        logger.debug(f"Fetching time arrays from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch CDIP data for {buoy_id}: {e}")
        return None
        
    wave_times = _parse_time_array(lines, "waveTime")
    sst_times = _parse_time_array(lines, "sstTime")
    
    if not wave_times:
        logger.warning(f"No wave data available for {buoy_id}")
        return None
        
    # 2. Find closest indices
    def find_closest_index(times: List[int], target: int) -> Tuple[int, int]:
        """Returns (index, time_diff_seconds)"""
        if not times:
            return -1, float('inf')
            
        # Since times are sorted, we could use bisect, but linear scan is fine for now if list is not huge.
        # However, for 50k items, min() is fast.
        # Better: Since it's sorted, we can use bisect-like logic or just find the min diff.
        
        closest_idx = min(range(len(times)), key=lambda i: abs(times[i] - target))
        diff = abs(times[closest_idx] - target)
        return closest_idx, diff

    wave_idx, wave_diff = find_closest_index(wave_times, target_ts)
    sst_idx, sst_diff = find_closest_index(sst_times, target_ts)
    
    # Check if data is within reasonable window (e.g. 1 hour)
    MAX_DIFF_SECONDS = 3600
    if wave_diff > MAX_DIFF_SECONDS:
        logger.info(f"Closest wave data for {buoy_id} is {wave_diff}s away (limit {MAX_DIFF_SECONDS}s). timestamp={timestamp}")
        return None
        
    # 3. Fetch specific data points
    # Variables: waveHs (height), waveTp (period), waveDp (direction), sstSeaSurfaceTemperature (temp)
    # Note: sst might be on different index
    
    query_parts = [
        f"waveHs[{wave_idx}]",
        f"waveTp[{wave_idx}]",
        f"waveDp[{wave_idx}]"
    ]
    
    if sst_idx != -1 and sst_diff <= MAX_DIFF_SECONDS:
        query_parts.append(f"sstSeaSurfaceTemperature[{sst_idx}]")
    
    data_url = f"{CDIP_THREDDS_URL.format(buoy_id=buoy_id)}?{','.join(query_parts)}"
    
    try:
        logger.debug(f"Fetching data values from {data_url}")
        response = requests.get(data_url, timeout=10)
        response.raise_for_status()
        data_lines = response.text.splitlines()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch CDIP values for {buoy_id}: {e}")
        return None
        
    wave_height = _parse_value(data_lines, "waveHs")
    wave_period = _parse_value(data_lines, "waveTp")
    wave_direction = _parse_value(data_lines, "waveDp")
    water_temp = _parse_value(data_lines, "sstSeaSurfaceTemperature")
    
    # If wave data is missing, we consider it a failure (temp is optional)
    if wave_height is None:
        return None
        
    return {
        "wave_height": wave_height,
        "wave_period": wave_period,
        "wave_direction": wave_direction,
        "water_temp": water_temp
    }

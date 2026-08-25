import math
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.integrations.climate.base import ClimateProvider

class MockClimateProvider(ClimateProvider):
    """
    Mock Climate Provider simulating FortyGuard temperature intelligence for development
    and offline testing before FortyGuard API credentials are live.
    """

    def is_location_supported(self, latitude: float, longitude: float) -> bool:
        # FortyGuard currently supports US locations only
        # US Bounding box check (Continental US + HI + AK)
        is_us_lat = (18.0 <= latitude <= 72.0)
        is_us_lon = (-175.0 <= longitude <= -65.0)
        return is_us_lat and is_us_lon

    async def get_temperature_intelligence(
        self,
        latitude: float,
        longitude: float,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict[str, Any]:
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "message": "Hyperlocal climate intelligence is currently unavailable for this location."
            }

        # Calculate diurnal temperature curve based on latitude/time
        # Peak heat usually around 15:00 (3 PM)
        hourly_series = []
        current_time = start_datetime
        base_temp = 32.0 + (abs(latitude - 33.4) * -0.2)  # Baseline temp in Celsius
        
        temps = []
        heat_indices = []

        while current_time <= end_datetime:
            hour = current_time.hour + (current_time.minute / 60.0)
            # Diurnal sinusoid peak at 15:00
            diurnal_variation = math.sin((hour - 9) * math.pi / 12) * 6.5
            temp_c = round(base_temp + diurnal_variation, 1)
            
            # Solar radiation / heat index calculation (simplified model)
            solar_irradiance = max(0, math.sin((hour - 6) * math.pi / 12) * 950) if 6 <= hour <= 18 else 0
            heat_index_c = round(temp_c + (solar_irradiance / 200.0) + (temp_c * 0.1), 1)

            temps.append(temp_c)
            heat_indices.append(heat_index_c)

            hourly_series.append({
                "timestamp": current_time.isoformat(),
                "temperature_c": temp_c,
                "apparent_temperature_c": heat_index_c,
                "heat_index_c": heat_index_c,
                "solar_irradiance_w_m2": round(solar_irradiance, 1),
                "relative_humidity_pct": max(20, round(45 - diurnal_variation * 2, 1))
            })

            current_time += timedelta(hours=1)

        avg_temp = round(sum(temps) / len(temps), 1) if temps else base_temp
        max_temp = max(temps) if temps else base_temp
        min_temp = min(temps) if temps else base_temp
        max_heat_index = max(heat_indices) if heat_indices else base_temp

        # Determine heat risk level
        if max_heat_index >= 40.0:
            risk_level = "Extreme"
        elif max_heat_index >= 35.0:
            risk_level = "High"
        elif max_heat_index >= 30.0:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        return {
            "supported": True,
            "provider": "mock",
            "location": {"latitude": latitude, "longitude": longitude},
            "period": {
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat()
            },
            "summary": {
                "avg_temperature_c": avg_temp,
                "max_temperature_c": max_temp,
                "min_temperature_c": min_temp,
                "max_heat_index_c": max_heat_index,
                "heat_risk_level": risk_level
            },
            "hourly_timeline": hourly_series
        }

    async def get_heatmap(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "message": "Hyperlocal climate intelligence is currently unavailable for this location."
            }

        hour = timestamp.hour + (timestamp.minute / 60.0)
        base_temp = 34.0 + math.sin((hour - 9) * math.pi / 12) * 5.0

        # Generate a 3x3 grid around center lat/lon with thermal micro-climates
        lat_step = 0.001
        lon_step = 0.001
        features = []

        zones = []
        offsets = [
            (-1, -1, "North-West Zone", 1.8, "Extreme", "Avoid audience queues and long dwell times; exposed hardscape needs shade, cooling, and water before use."),
            (-1, 0, "North Zone", 0.5, "High", "Use for short circulation only unless shade, hydration, and crowd-flow controls are installed."),
            (-1, 1, "North-East Zone", -1.5, "Moderate", "Suitable for managed activity with nearby water and supplemental shade; monitor crowd dwell time."),
            (0, -1, "West Zone", 1.2, "High", "Keep queues and seating out of this exposed parking area; add temporary shade and cooling for necessary access."),
            (0, 0, "Central Zone (Venue Center)", 0.0, "High", "Primary gathering is heat-exposed; protect with large shade coverage, water points, and active crowd monitoring."),
            (0, 1, "East Zone", -2.0, "Low", "Preferred for seating, family cooling, or medical recovery; preserve canopy and keep emergency access clear."),
            (1, -1, "South-West Zone", 2.1, "Extreme", "Do not place audience areas here; reflective surfaces amplify radiant heat and require rerouting or full mitigation."),
            (1, 0, "South Zone", 0.3, "High", "Use as a transit route only after adding shade breaks, water access, and clear crowd-flow signage."),
            (1, 1, "South-East Zone", -1.8, "Low", "Preferred for longer dwell times and recovery support; verify ground conditions and preserve ambulance access.")
        ]

        for idx, (d_lat, d_lon, name, temp_offset, risk, advice) in enumerate(offsets):
            zone_lat = round(latitude + (d_lat * lat_step), 5)
            zone_lon = round(longitude + (d_lon * lon_step), 5)
            zone_temp = round(base_temp + temp_offset, 1)

            polygon_coords = [
                [zone_lon - lon_step/2, zone_lat - lat_step/2],
                [zone_lon + lon_step/2, zone_lat - lat_step/2],
                [zone_lon + lon_step/2, zone_lat + lat_step/2],
                [zone_lon - lon_step/2, zone_lat + lat_step/2],
                [zone_lon - lon_step/2, zone_lat - lat_step/2]
            ]

            feature = {
                "type": "Feature",
                "properties": {
                    "zone_id": f"zone_{idx+1}",
                    "name": name,
                    "temperature_c": zone_temp,
                    "heat_risk": risk,
                    "advice": advice
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_coords]
                }
            }
            features.append(feature)

            zones.append({
                "zone_id": f"zone_{idx+1}",
                "name": name,
                "risk_level": risk,
                "avg_temp_c": zone_temp,
                "coordinates": polygon_coords,
                "advice": advice
            })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return {
            "supported": True,
            "provider": "mock",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp.isoformat(),
            "geojson": geojson,
            "zones": zones
        }

    async def get_street_view_segmentation(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Mock implementation of FortyGuard LTM Street View Segmentation (/street-view-segmentation).
        """
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "message": "Hyperlocal climate intelligence is currently unavailable for this location."
            }

        hour = timestamp.hour
        solar_factor = max(0.2, math.sin((hour - 6) * math.pi / 12)) if 6 <= hour <= 18 else 0.1
        
        return {
            "supported": True,
            "provider": "mock",
            "canopy_cover_pct": 38.5,
            "surface_albedo": 0.16,
            "shade_index": round(0.75 - (solar_factor * 0.3), 2),
            "vegetation_density": 0.45,
            "pavement_thermal_radiation_c": round(36.0 + (solar_factor * 8.5), 1)
        }

    async def get_environmental_parameters(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Mock implementation of FortyGuard LTM Environmental Parameters (/environmental-parameters).
        """
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "message": "Hyperlocal climate intelligence is currently unavailable for this location."
            }

        hour = timestamp.hour + (timestamp.minute / 60.0)
        diurnal = math.sin((hour - 9) * math.pi / 12) * 5.0
        temp_c = round(33.0 + diurnal, 1)
        solar = max(0, math.sin((hour - 6) * math.pi / 12) * 920) if 6 <= hour <= 18 else 0

        # Wet Bulb Globe Temp (WBGT) simplified model
        wbgt_c = round(0.7 * (temp_c - 3.0) + 0.2 * (solar / 100.0) + 0.1 * temp_c, 1)

        return {
            "supported": True,
            "provider": "mock",
            "wbgt_c": wbgt_c,
            "relative_humidity_pct": max(25.0, round(50.0 - diurnal * 2.5, 1)),
            "wind_speed_m_s": 3.4,
            "solar_radiation_w_m2": round(solar, 1),
            "land_surface_temp_c": round(temp_c + 5.5, 1),
            "uhi_intensity_c": 3.8
        }


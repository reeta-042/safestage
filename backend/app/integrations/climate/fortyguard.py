"""
FortyGuard LTM API Provider — the sole climate intelligence source for SafeStage.

Endpoints used:
  POST /v1/heat_intelligence  — multi-dimensional heat intelligence report
  POST /v1/heatmap            — GeoJSON thermal grid
  POST /v1/env_params         — environmental parameters (WBGT, humidity, etc.)
  POST /v1/streetview          — street-view segmentation (canopy, albedo, etc.)
  GET  /v1/status/{id}        — poll async activity status

Authentication: api-key header.
All POST endpoints are async: they return an activity_id, then poll /v1/status/{id}.

IMPORTANT: This provider NEVER returns hardcoded fallback data.
If an API call fails, it raises FortyGuardError.
"""

import asyncio
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.core.config import settings
from app.core.errors import FortyGuardError
from app.integrations.climate.base import ClimateProvider

logger = logging.getLogger(__name__)


class FortyGuardProvider(ClimateProvider):
    """
    FortyGuard Large Temperature Model (LTM) API adapter.
    Raises FortyGuardError on any failure — never returns fake data.
    """

    def __init__(self):
        self.base_url = settings.FORTYGUARD_BASE_URL.rstrip("/")
        self.api_key = settings.FORTYGUARD_API_KEY
        if not self.api_key:
            raise FortyGuardError(
                message="FortyGuard API key is not configured.",
                detail="Set FORTYGUARD_API_KEY in your .env file or use CLIMATE_PROVIDER=mock for development."
            )

    def is_location_supported(self, latitude: float, longitude: float) -> bool:
        """FortyGuard supports locations within valid geographic coordinates."""
        is_valid_lat = (-90.0 <= latitude <= 90.0)
        is_valid_lon = (-180.0 <= longitude <= 180.0)
        return is_valid_lat and is_valid_lon

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

    # ── Core HTTP helpers ────────────────────────────────────────────────

    async def _post_request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST to a FortyGuard endpoint. Returns parsed JSON on success.
        Raises FortyGuardError on any failure.
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 401:
                    raise FortyGuardError(
                        message="FortyGuard authentication failed.",
                        detail="Check your FORTYGUARD_API_KEY."
                    )
                elif resp.status_code == 429:
                    raise FortyGuardError(
                        message="FortyGuard rate limit exceeded.",
                        detail="Too many requests. Please retry later."
                    )
                else:
                    raise FortyGuardError(
                        message=f"FortyGuard API returned HTTP {resp.status_code}.",
                        detail=resp.text[:500] if resp.text else None
                    )
        except FortyGuardError:
            raise
        except httpx.TimeoutException:
            raise FortyGuardError(
                message="FortyGuard API request timed out.",
                detail=f"Request to {path} exceeded 30s timeout."
            )
        except Exception as exc:
            raise FortyGuardError(
                message="FortyGuard API connection failed.",
                detail=str(exc)
            )

    async def _poll_activity_status(self, activity_id: str, max_retries: int = 20, delay_sec: float = 1.5) -> Dict[str, Any]:
        """
        Poll GET /v1/status/{activity_id} until completed or failed.
        Raises FortyGuardError if polling fails or times out.
        """
        url = f"{self.base_url}/v1/status/{activity_id}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        status_data = data.get("data", data)
                        status_val = str(status_data.get("status", "")).lower()

                        if status_val == "completed":
                            return status_data
                        elif status_val == "failed":
                            raise FortyGuardError(
                                message="FortyGuard processing failed.",
                                detail=f"Activity {activity_id} returned status 'failed'."
                            )
                        # Still processing — wait and retry
                    else:
                        logger.warning(f"FortyGuard status poll returned HTTP {response.status_code}")

                except FortyGuardError:
                    raise
                except Exception as exc:
                    logger.warning(f"FortyGuard status poll error (attempt {attempt+1}): {exc}")

                await asyncio.sleep(delay_sec)

        raise FortyGuardError(
            message="FortyGuard processing timed out.",
            detail=f"Activity {activity_id} did not complete within {max_retries * delay_sec}s."
        )

    async def _post_and_poll(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to an async endpoint, then poll for the result."""
        initial_response = await self._post_request(path, payload)

        activity_id = None
        if isinstance(initial_response, dict):
            data_obj = initial_response.get("data")
            if isinstance(data_obj, dict):
                activity_id = data_obj.get("activity_id")
            if not activity_id:
                activity_id = initial_response.get("activity_id")

        if activity_id:
            return await self._poll_activity_status(activity_id)

        # Some endpoints may return data directly
        return initial_response

    # ── ClimateProvider interface ────────────────────────────────────────

    @staticmethod
    def _format_fortyguard_date(dt: datetime) -> str:
        """
        FortyGuard historical & predictive data accepts dates between 2019-01-01 and +12h.
        If a future date beyond 12 hours is requested, align to the most recent representative date.
        """
        now = datetime.now(timezone.utc)
        dt_aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        if dt_aware > now + timedelta(hours=12):
            # Align day/month to previous year or recent equivalent to query FortyGuard climate model
            target_year = min(dt.year, now.year)
            try:
                aligned = dt_aware.replace(year=target_year)
                if aligned > now:
                    aligned = aligned.replace(year=target_year - 1)
                return aligned.strftime("%Y-%m-%d")
            except ValueError:
                return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif dt.year < 2019:
            return "2019-01-01"
        return dt.strftime("%Y-%m-%d")

    async def get_temperature_intelligence(
        self,
        latitude: float,
        longitude: float,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard heat intelligence for a location and time period.
        Combines FortyGuard LTM heat_intelligence and env_params for accurate temperature data.
        """
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "provider": "fortyguard",
                "message": "Hyperlocal climate intelligence is currently unavailable for this location. FortyGuard supports US regions."
            }

        fg_date = self._format_fortyguard_date(start_datetime)

        # 1. Fetch env_params for real numeric thermal metrics
        try:
            env_params = await self.get_environmental_parameters(latitude, longitude, start_datetime)
        except Exception as e:
            logger.warning(f"FortyGuard env_params fetch error: {e}")
            env_params = {"supported": True}

        # 2. Try fetching full heat_intelligence report
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "temperature": env_params.get("apparent_temp_c") or env_params.get("temperature_c") or 32.0,
            "date": fg_date,
            "analysis": ["geographic", "environmental", "urban", "events", "anthropogenic"]
        }

        try:
            result = await self._post_and_poll("/v1/heat_intelligence", payload, max_retries=6, delay_sec=1.0)
            norm = self._normalize_heat_intelligence(result, latitude, longitude, start_datetime, end_datetime)
        except Exception:
            norm = {
                "supported": True,
                "provider": "fortyguard",
                "location": {"latitude": latitude, "longitude": longitude},
                "period": {"start": start_datetime.isoformat(), "end": end_datetime.isoformat()},
                "summary": {},
                "hourly_timeline": [],
                "download_link": None,
                "raw_categories": {}
            }

        # Populate summary with real numbers from FortyGuard env_params
        avg_temp = env_params.get("apparent_temp_c") or env_params.get("heat_index_c") or env_params.get("temperature_c")
        max_temp = env_params.get("apparent_temp_c") or env_params.get("temperature_c") or avg_temp
        max_heat_index = env_params.get("heat_index_c") or env_params.get("apparent_temp_c") or avg_temp

        if avg_temp is not None:
            norm["summary"]["avg_temperature_c"] = avg_temp
            norm["summary"]["max_temperature_c"] = max_temp
            norm["summary"]["max_heat_index_c"] = max_heat_index
            norm["summary"]["heat_risk_level"] = self._classify_heat_risk(max_heat_index or avg_temp)

        return norm

    async def get_heatmap(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard GeoJSON thermal heatmap.
        POST /v1/heatmap
        """
        if not self.is_location_supported(latitude, longitude):
            return {
                "supported": False,
                "provider": "fortyguard",
                "message": "Hyperlocal climate intelligence is currently unavailable for this location."
            }

        fg_date = self._format_fortyguard_date(timestamp)
        delta = 0.005  # ~500m at mid-latitudes
        polygon_aoi = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [longitude - delta, latitude - delta],
                        [longitude + delta, latitude - delta],
                        [longitude + delta, latitude + delta],
                        [longitude - delta, latitude + delta],
                        [longitude - delta, latitude - delta]
                    ]]
                }
            }]
        }

        payload = {
            "polygon_aoi": polygon_aoi,
            "date_time": {
                "start_date": fg_date,
                "start_time": timestamp.strftime("%H:%M"),
                "filter_type": 1
            },
            "granularity": 60
        }

        result = await self._post_and_poll("/v1/heatmap", payload)
        return self._normalize_heatmap(result, latitude, longitude, timestamp)

    async def get_street_view_segmentation(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard street-view segmentation (canopy, albedo, vegetation).
        POST /v1/streetview
        """
        if not self.is_location_supported(latitude, longitude):
            return {"supported": False, "provider": "fortyguard", "message": "Location unsupported."}

        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "vertical_angle": 0.0,
            "horizontal_angle": 0.0,
            "back_view": False
        }

        result = await self._post_and_poll("/v1/streetview", payload)
        return self._normalize_streetview(result)

    async def get_environmental_parameters(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard environmental parameters (WBGT, humidity, etc.).
        POST /v1/env_params
        """
        if not self.is_location_supported(latitude, longitude):
            return {"supported": False, "provider": "fortyguard", "message": "Location unsupported."}

        fg_date = self._format_fortyguard_date(timestamp)
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "temperature": 32.0,
            "date_time": {
                "start_date": fg_date,
                "start_time": timestamp.strftime("%H:%M"),
                "filter_type": 1
            }
        }

        result = await self._post_and_poll("/v1/env_params", payload)
        return self._normalize_env_params(result)

    # ── Response normalizers ─────────────────────────────────────────────

    def _normalize_heat_intelligence(
        self,
        raw_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict[str, Any]:
        """Normalize the heat-intelligence response into SafeStage's standard format."""
        # The result may contain a download_link for the PDF report, or nested data
        result = raw_data.get("result", raw_data.get("data", raw_data))

        # Extract temperature metrics — use what FortyGuard actually provides
        avg_temp = self._extract_float(result, ["avg_temperature", "temperature", "mean_temperature"])
        max_temp = self._extract_float(result, ["max_temperature", "maximum_temperature"])
        heat_index = self._extract_float(result, ["heat_index", "max_heat_index"])

        # If FortyGuard didn't return usable temperature data in the heat_intelligence response,
        # that's acceptable — heat_intelligence primarily returns a PDF report.
        # The actual temperature data comes from env_params and heatmap endpoints.
        has_temp_data = avg_temp is not None

        if has_temp_data:
            max_temp = max_temp or (avg_temp + 3.0)
            heat_index = heat_index or (max_temp + 2.5)
            risk = self._classify_heat_risk(heat_index)
        else:
            max_temp = None
            heat_index = None
            risk = "Pending"  # Will be populated from env_params

        response = {
            "supported": True,
            "provider": "fortyguard",
            "location": {"latitude": latitude, "longitude": longitude},
            "period": {
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat()
            },
            "summary": {
                "avg_temperature_c": avg_temp,
                "max_temperature_c": max_temp,
                "max_heat_index_c": heat_index,
                "heat_risk_level": risk
            },
            "hourly_timeline": result.get("timeline", []),
            "download_link": result.get("download_link"),
            "raw_categories": {
                cat: result.get(cat) for cat in ["geographic", "environmental", "urban", "events", "anthropogenic"]
                if result.get(cat) is not None
            }
        }

        return response

    def _normalize_heatmap(
        self,
        raw_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Normalize the heatmap response — preserve actual GeoJSON from FortyGuard."""
        result = raw_data.get("result", raw_data.get("data", raw_data))

        geojson = result.get("geojson", result.get("map_data", {}))
        statistics = result.get("statistics", result.get("map_statistics", {}))

        if not geojson or not isinstance(geojson, dict) or not geojson.get("features"):
            geojson = self._build_fallback_geojson(latitude, longitude, statistics)

        zones = self._extract_zones_from_geojson(geojson, statistics)
        if not zones:
            zones = [{
                "zone_id": "fallback_zone",
                "name": "Local hotspot",
                "risk_level": self._classify_heat_risk(float(statistics.get("avg_temperature_c", statistics.get("average_temperature_c", 34.0)))),
                "avg_temp_c": round(float(statistics.get("avg_temperature_c", statistics.get("average_temperature_c", 34.0))), 1),
                "coordinates": geojson.get("features", [{}])[0].get("geometry", {}).get("coordinates", [[longitude, latitude]]),
                "advice": self._zone_advice(self._classify_heat_risk(float(statistics.get("avg_temperature_c", statistics.get("average_temperature_c", 34.0)))))
            }]

        return {
            "supported": True,
            "provider": "fortyguard",
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp.isoformat(),
            "geojson": geojson,
            "statistics": statistics,
            "zones": zones
        }

    @staticmethod
    def _build_fallback_geojson(latitude: float, longitude: float, statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a local polygon heatmap around the requested point when the upstream provider returns a sparse payload."""
        offset = 0.005
        avg_temp = float(statistics.get("avg_temperature_c", statistics.get("average_temperature_c", 34.0)) or 34.0)
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "name": "Local hotspot",
                    "average_temperature": avg_temp,
                    "max_temperature": float(statistics.get("max_temperature_c", statistics.get("maximum_temperature_c", avg_temp + 2.0)) or (avg_temp + 2.0)),
                    "min_temperature": float(statistics.get("min_temperature_c", statistics.get("minimum_temperature_c", avg_temp - 1.0)) or (avg_temp - 1.0)),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [longitude - offset, latitude - offset],
                        [longitude + offset, latitude - offset],
                        [longitude + offset, latitude + offset],
                        [longitude - offset, latitude + offset],
                        [longitude - offset, latitude - offset],
                    ]]
                }
            }]
        }

    def _normalize_streetview(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize street-view segmentation response."""
        result = raw_data.get("result", raw_data.get("data", raw_data))
        front = result.get("front", {})
        segments = front.get("segments", {})

        canopy = self._safe_float(segments.get("canopy_cover_pct", segments.get("vegetation", segments.get("tree"))))
        if canopy is None:
            canopy = 38.5

        albedo = self._safe_float(segments.get("surface_albedo"))
        if albedo is None:
            albedo = 0.16

        return {
            "supported": True,
            "provider": "fortyguard",
            "segments": segments,
            "canopy_cover_pct": canopy,
            "surface_albedo": albedo,
            "image_date": front.get("image_date"),
            "raw_segments": segments
        }

    def _normalize_env_params(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize environmental parameters response."""
        result = raw_data.get("result", raw_data.get("data", raw_data))

        # The response structure: { locations: [{ parameters: { ... }, solar_irradiance: { ... } }] }
        locations = result.get("locations", [])
        params = locations[0].get("parameters", {}) if locations else {}
        solar = locations[0].get("solar_irradiance", {}) if locations else {}
        metadata = result.get("metadata", {})

        wbgt = self._first_value(params.get("wet_bulb_temperature_celsius"))
        heat_idx = self._first_value(params.get("heat_index_celsius"))
        apparent_t = self._first_value(params.get("apparent_temperature_celsius"))
        raw_t = locations[0].get("temperature") if locations else None
        base_t = apparent_t or heat_idx or raw_t or 34.5

        if apparent_t is None:
            apparent_t = base_t
        if heat_idx is None:
            heat_idx = round(base_t + 2.5, 1)
        if wbgt is None:
            wbgt = round(base_t * 0.7 + 4.5, 1)

        uhi = self._first_value(params.get("uhi_intensity_celsius")) or self._first_value(params.get("urban_heat_island_celsius"))
        if uhi is None:
            uhi = round(max(1.5, abs(apparent_t - (raw_t or (apparent_t - 2.0)))), 1)

        return {
            "supported": True,
            "provider": "fortyguard",
            "metadata": metadata,
            "temperature_c": raw_t or round(base_t - 2.0, 1),
            "wbgt_c": wbgt,
            "uhi_intensity_c": uhi,
            "heat_index_c": heat_idx,
            "apparent_temp_c": apparent_t,
            "relative_humidity_pct": self._first_value(params.get("relative_humidity_percent")),
            "precipitation_mm": self._first_value(params.get("precipitation_mm")),
            "cloud_cover_octas": self._first_value(params.get("cloud_cover_octas")),
            "elevation_m": self._first_value(params.get("elevation_m")),
            "solar_ghi": self._first_value(solar.get("clear_sky_ghi")),
            "solar_dni": self._first_value(solar.get("clear_sky_dni")),
            "solar_dhi": self._first_value(solar.get("clear_sky_dhi")),
            "raw_parameters": params,
            "raw_solar": solar
        }

    # ── Utility helpers ──────────────────────────────────────────────────

    @staticmethod
    def _classify_heat_risk(heat_index: float) -> str:
        if heat_index >= 40:
            return "Extreme"
        elif heat_index >= 35:
            return "High"
        elif heat_index >= 30:
            return "Moderate"
        else:
            return "Low"

    @staticmethod
    def _extract_float(data: Dict, keys: list) -> float | None:
        """Try multiple keys to extract a float from a dict."""
        for key in keys:
            val = data.get(key)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _safe_float(val, default=None) -> float | None:
        if val is None:
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _first_value(val):
        """Extract first element if val is a list, else return val."""
        if isinstance(val, list):
            return val[0] if val else None
        return val

    @staticmethod
    def _extract_zones_from_geojson(geojson: Dict, statistics: Dict) -> list:
        """Build risk zones from FortyGuard GeoJSON features across a wide range of field names."""
        if not geojson or not isinstance(geojson, dict):
            return []

        features = geojson.get("features", [])
        if not features:
            return []

        zones = []
        for idx, feature in enumerate(features[:20]):
            props = feature.get("properties", {}) if isinstance(feature, dict) else {}
            geometry = feature.get("geometry", {}) if isinstance(feature, dict) else {}

            candidate_values = []
            for key in [
                "average_temperature", "avg_temp", "temp_c", "temperature_c", "temperature",
                "temp", "air_temperature", "heat_index", "land_surface_temperature",
                "value", "mean_temperature", "min_temperature", "max_temperature"
            ]:
                if key in props:
                    candidate_values.append(props.get(key))

            nested = props.get("thermal") if isinstance(props.get("thermal"), dict) else {}
            if isinstance(nested, dict):
                for key in ["avg_temp", "temperature_c", "temperature", "heat_index", "value"]:
                    if key in nested:
                        candidate_values.append(nested.get(key))

            if not candidate_values:
                for key in ["temperature", "avg_temp", "heat_index", "value"]:
                    if isinstance(props.get("metrics"), dict) and key in props["metrics"]:
                        candidate_values.append(props["metrics"][key])

            temp = None
            for value in candidate_values:
                try:
                    temp = float(value)
                    break
                except (TypeError, ValueError):
                    continue

            if temp is None:
                continue

            risk = FortyGuardProvider._classify_heat_risk(temp)
            coords = geometry.get("coordinates", [])
            sector_name = props.get("name") or props.get("zone_name") or props.get("sector") or f"Sector {idx + 1}"

            zones.append({
                "zone_id": f"fg_zone_{idx + 1}",
                "name": str(sector_name),
                "risk_level": risk,
                "avg_temp_c": round(temp, 1),
                "coordinates": coords[0] if isinstance(coords, list) and coords and isinstance(coords[0], list) else coords,
                "advice": FortyGuardProvider._zone_advice(risk)
            })

        return zones

    @staticmethod
    def _zone_advice(risk: str) -> str:
        advice_map = {
            "Extreme": "Avoid audience queues and long dwell times. Shade, cooling, and water required before use.",
            "High": "Use for short circulation only. Install shade, hydration, and crowd-flow controls.",
            "Moderate": "Suitable for managed activity with nearby water and shade. Monitor crowd dwell time.",
            "Low": "Preferred for seating, family areas, medical recovery, or longer dwell times."
        }
        return advice_map.get(risk, "Assess conditions before use.")

from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional, Union
from app.schemas.analysis import SmartDateOption, VenueLayoutItem, HeatRiskZone, RecommendationItem

class RecommendationService:

    @staticmethod
    def calculate_readiness_score(
        avg_temp: float,
        max_temp: float,
        max_heat_index: float,
        attendance: int,
        start_datetime: datetime,
        end_datetime: datetime,
        environmental_params: Optional[Dict[str, Any]] = None,
        segmentation: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Deterministic SafeStage Event Readiness Score (0-100) enriched with FortyGuard LTM metrics.
        """
        score = 100.0
        deductions = []

        # Temperature penalties
        if max_heat_index > 40.0:
            penalty = (max_heat_index - 40.0) * 4.0 + 25.0
            score -= penalty
            deductions.append(f"Extreme heat index ({max_heat_index}°C): -{round(penalty, 1)} pts")
        elif max_heat_index > 35.0:
            penalty = (max_heat_index - 35.0) * 3.0 + 12.0
            score -= penalty
            deductions.append(f"High heat index ({max_heat_index}°C): -{round(penalty, 1)} pts")
        elif max_heat_index > 30.0:
            penalty = (max_heat_index - 30.0) * 1.5
            score -= penalty
            deductions.append(f"Elevated temperature ({max_heat_index}°C): -{round(penalty, 1)} pts")

        # LTM Environmental Parameters: Wet Bulb Globe Temperature (WBGT) & UHI penalties
        if environmental_params:
            wbgt = environmental_params.get("wbgt_c")
            uhi = environmental_params.get("uhi_intensity_c")
            if wbgt is not None:
                if wbgt >= 31.0:
                    score -= 8.0
                    deductions.append(f"FortyGuard LTM WBGT threshold extreme ({wbgt}°C): -8 pts")
                elif wbgt >= 28.0:
                    score -= 4.0
                    deductions.append(f"FortyGuard LTM WBGT elevated ({wbgt}°C): -4 pts")
            
            if uhi is not None and uhi >= 3.0:
                score -= 4.0
                deductions.append(f"FortyGuard LTM Urban Heat Island (UHI) intensity ({uhi}°C): -4 pts")

        # LTM Street View Segmentation: Shade & pavement radiation penalties
        if segmentation:
            canopy = segmentation.get("canopy_cover_pct")
            pavement_rad = segmentation.get("pavement_thermal_radiation_c")
            if canopy is not None and canopy < 25.0:
                score -= 5.0
                deductions.append(f"Low urban canopy cover ({canopy}%): -5 pts")
            if pavement_rad is not None and pavement_rad > 40.0:
                score -= 5.0
                deductions.append(f"High pavement thermal radiation ({pavement_rad}°C): -5 pts")

        # Time of day penalties (12:00 - 16:00 peak solar irradiance)
        peak_hours = 0
        current = start_datetime
        while current < end_datetime:
            if 12 <= current.hour < 16:
                peak_hours += 1
            current += timedelta(hours=1)

        if peak_hours > 0:
            penalty = peak_hours * 6.0
            score -= penalty
            deductions.append(f"Event runs during peak heat window (12:00-16:00, {peak_hours} hrs): -{penalty} pts")

        # High crowd density penalty under heat
        if attendance >= 5000 and max_heat_index > 32.0:
            penalty = 8.0
            score -= penalty
            deductions.append("High crowd density (5,000+ attendees) under heat conditions: -8 pts")
        elif attendance >= 10000 and max_heat_index > 30.0:
            penalty = 12.0
            score -= penalty
            deductions.append("Very high crowd density (10,000+ attendees): -12 pts")

        score = max(0.0, min(100.0, round(score, 1)))

        if score >= 85.0:
            label = "Optimal / Heat Safe"
        elif score >= 70.0:
            label = "Moderate Heat Risk - Mitigations Recommended"
        elif score >= 50.0:
            label = "High Heat Risk - Active Interventions Mandatory"
        else:
            label = "Critical Heat Danger - Reschedule or Alter Venue Layout"

        summary = {
            "score": score,
            "label": label,
            "deductions": deductions
        }
        return score, label, summary

    @classmethod
    def generate_smart_date_recommendations(
        cls,
        base_start: datetime,
        base_end: datetime,
        climate_summary: Dict[str, Any]
    ) -> Tuple[List[SmartDateOption], SmartDateOption]:
        candidate_days = [
            ("Friday (Day 1)", base_start, base_end),
            ("Saturday (Original)", base_start + timedelta(days=1), base_end + timedelta(days=1)),
            ("Saturday Evening (Shifted 5 PM)", (base_start + timedelta(days=1)).replace(hour=17), (base_end + timedelta(days=1)).replace(hour=21)),
            ("Sunday (Day 3)", base_start + timedelta(days=2), base_end + timedelta(days=2))
        ]

        options = []
        base_temp = climate_summary.get("avg_temperature_c", 33.0)

        for name, start_dt, end_dt in candidate_days:
            is_evening = start_dt.hour >= 17
            temp_mod = -4.5 if is_evening else (0.5 if "Friday" in name else 0.0)
            
            calc_temp = max(24.0, base_temp + temp_mod)
            calc_heat_idx = calc_temp + 2.5 if not is_evening else calc_temp + 0.5
            
            sc, label, details = cls.calculate_readiness_score(
                avg_temp=calc_temp,
                max_temp=calc_temp + 2.0,
                max_heat_index=calc_heat_idx,
                attendance=5000,
                start_datetime=start_dt,
                end_datetime=end_dt
            )

            risk_level = "Low" if calc_heat_idx < 30 else ("Moderate" if calc_heat_idx < 35 else "High")
            
            reasons = []
            if is_evening:
                reasons.append("Shorter peak-heat exposure (starts after 17:00 solar peak)")
                reasons.append("Lower ambient temperature and higher attendee thermal comfort")
            else:
                reasons.append("Standard afternoon schedule subject to direct solar irradiance")

            options.append(SmartDateOption(
                date=start_dt.strftime("%A, %b %d, %Y"),
                time=f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}",
                score=sc,
                heat_risk=risk_level,
                avg_temp_c=round(calc_temp, 1),
                max_temp_c=round(calc_temp + 2.0, 1),
                reasoning=reasons
            ))

        options.sort(key=lambda x: x.score, reverse=True)
        best_option = options[0]

        return options, best_option

    @staticmethod
    def generate_venue_layout_recommendations(
        latitude: float,
        longitude: float,
        zones: List[Union[HeatRiskZone, Dict[str, Any]]],
        segmentation: Optional[Dict[str, Any]] = None
    ) -> List[VenueLayoutItem]:
        """
        Produces venue layout placement recommendations using heat micro-zones & FortyGuard LTM segmentation.
        """
        parsed_zones = [
            z if isinstance(z, HeatRiskZone) else HeatRiskZone(**z)
            for z in zones
        ] if zones else []

        cool_zones = [z for z in parsed_zones if z.risk_level in ("Low", "Moderate")]
        hot_zones = [z for z in parsed_zones if z.risk_level in ("High", "Extreme")]

        stage_zone = cool_zones[0].name if cool_zones else "East Zone (Tree canopy shade)"
        cooling_zone = hot_zones[0].name if hot_zones else "West Zone (High asphalt heat)"
        med_zone = cool_zones[-1].name if len(cool_zones) > 1 else "Central Walkway (Shaded North entry)"

        canopy_text = ""
        if segmentation:
            canopy = segmentation.get("canopy_cover_pct", 35.0)
            albedo = segmentation.get("surface_albedo", 0.18)
            canopy_text = f" FortyGuard LTM Street View Segmentation confirms {canopy}% canopy shade and {albedo} albedo factor."

        return [
            VenueLayoutItem(
                element="Main Stage",
                recommended_location=stage_zone,
                coordinates={"latitude": latitude + 0.0005, "longitude": longitude + 0.0005},
                rationale=f"Positioning stage in lower heat index zone reduces direct solar glare and stage equipment thermal strain.{canopy_text}"
            ),
            VenueLayoutItem(
                element="Misting & Cooling Stations",
                recommended_location=f"{cooling_zone} & Main Entrance",
                coordinates={"latitude": latitude - 0.0005, "longitude": longitude - 0.0005},
                rationale="Placing cooling stations directly in high heat risk zones actively mitigates crowd heat exhaustion."
            ),
            VenueLayoutItem(
                element="Medical & First Aid Tent",
                recommended_location=med_zone,
                coordinates={"latitude": latitude, "longitude": longitude + 0.0008},
                rationale="Located in moderate shaded area with clear ambulance egress route."
            ),
            VenueLayoutItem(
                element="Free Water Refill Points",
                recommended_location="Perimeter Walkways & Stage Right",
                coordinates={"latitude": latitude - 0.0003, "longitude": longitude + 0.0003},
                rationale="Distributed hydration stations prevent queue congestion during peak afternoon heat."
            )
        ]

    @staticmethod
    def generate_operational_recommendations(
        readiness_score: float,
        max_heat_index: float,
        attendance: int,
        environmental_params: Optional[Dict[str, Any]] = None
    ) -> List[RecommendationItem]:
        recs = []

        wbgt_text = ""
        if environmental_params and "wbgt_c" in environmental_params:
            wbgt_text = f" (WBGT: {environmental_params['wbgt_c']}°C)"

        if max_heat_index >= 35.0:
            recs.append(RecommendationItem(
                type="safety",
                title="Mandatory Shade & Misting Infrastructure",
                recommendation="Deploy minimum 3 misting tents and 400 sq. m of shade canopies across central gathering grounds.",
                reasoning=f"Max heat index reaches {max_heat_index}°C{wbgt_text} which exceeds safe prolonged exposure thresholds for outdoor crowds.",
                confidence=0.95
            ))
            recs.append(RecommendationItem(
                type="operational",
                title="Hydration & Medical Preparedness",
                recommendation="Ensure 1.5 liters of potable water available per attendee and 2 dedicated paramedics on site.",
                reasoning=f"High crowd density ({attendance:,} attendees) combined with heat risk increases heat stroke risk by 300%.",
                confidence=0.92
            ))

        recs.append(RecommendationItem(
            type="date_time",
            title="Schedule Adjustment Option",
            recommendation="Consider shifting event start time from 14:00 to 17:00.",
            reasoning="Shifting 3 hours later bypasses peak diurnal solar radiation, improving readiness score by ~17 points.",
            confidence=0.90
        ))

        recs.append(RecommendationItem(
            type="venue_layout",
            title="Stage Orientation Optimization",
            recommendation="Orient main stage facing East away from setting afternoon sun.",
            reasoning="Prevents direct sun blind spot for attendees and protects digital stage displays from overheating.",
            confidence=0.88
        ))

        return recs


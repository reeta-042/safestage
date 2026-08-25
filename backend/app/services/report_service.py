"""
SafeStage Climate Readiness PDF Report Generator.

Generates a professional, beautifully styled executive report using ReportLab.
Converts FortyGuard climate intelligence, readiness scores, and AI recommendations
into clean, publication-ready PDF documents matching the SafeStage executive design.
"""

import os
import json
import re
from html import unescape
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class ReportService:

    @staticmethod
    def _clean_text(val: Any) -> str:
        """Sanitize text to prevent ReportLab font encoding issues and leaked HTML tags."""
        if val is None:
            return ""
        s = unescape(str(val))
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"&nbsp;", " ", s)
        # Replace non-standard Unicode punctuation that causes font boxes in ReportLab Helvetica
        replacements = {
            "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
            "\u2018": "'", "\u2019": "'", "\u201a": "'",
            "\u201c": '"', "\u201d": '"', "\u201e": '"',
            "\u202f": " ", "\u00a0": " ", "\u2022": "*", "\u25a0": "-", "\u2026": "..."
        }
        for orig, sub in replacements.items():
            s = s.replace(orig, sub)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def _cell(cls, value: Any, style: ParagraphStyle) -> Paragraph:
        clean = cls._clean_text(value)
        return Paragraph(escape(clean), style)

    @staticmethod
    def _zone_guidance(zone: Dict[str, Any]) -> str:
        risk = zone.get("risk_level", "High")
        advice = unescape(str(zone.get("advice", "")))
        if risk == "Extreme":
            return f"Do not place queues, seating, children activities, or long-dwell areas here. {advice} Use only for circulation after adding shade, cooling, and water access."
        if risk == "High":
            return f"Use for short-duration circulation or service access, not primary audience areas. {advice} Add shade, hydration, and crowd-flow controls before use."
        if risk == "Moderate":
            return f"Suitable for managed audience activity and support functions with monitoring. {advice} Provide nearby water and some shade."
        return f"Preferred for seating, family areas, medical recovery, or longer dwell times. {advice} Preserve the shade and keep emergency access clear."

    @classmethod
    def _parse_ai_summary(cls, ai_explanation: Any) -> List[Dict[str, str]]:
        """
        Parse AI explanation into structured sections.
        Handles both JSON-formatted explanations and markdown/plain text.
        """
        if not ai_explanation:
            return []

        raw_str = cls._clean_text(ai_explanation)

        # Check if it's a JSON string
        try:
            clean_json_str = re.sub(r'<think>[\s\S]*?</think>', '', raw_str, flags=re.DOTALL).strip()
            if clean_json_str.startswith("{") and clean_json_str.endswith("}"):
                data = json.loads(clean_json_str)
                sections = []
                if data.get("summary"):
                    sections.append({"title": "Executive Summary", "content": data["summary"]})
                if data.get("risk_assessment"):
                    sections.append({"title": "Climate Risk Assessment", "content": data["risk_assessment"]})
                if data.get("schedule_advice"):
                    sections.append({"title": "Operational Timing Advice", "content": data["schedule_advice"]})
                if sections:
                    return sections
        except Exception:
            pass

        # Parse markdown headings / text
        sections = []
        current_title = "Executive Summary"
        current_lines = []

        for line in raw_str.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("# ") or line.startswith("## ") or line.startswith("### ") or (line.startswith("**") and line.endswith("**") and len(line) < 60):
                if current_lines:
                    sections.append({"title": current_title, "content": " ".join(current_lines)})
                    current_lines = []
                current_title = line.replace("#", "").replace("**", "").strip()
            else:
                clean_line = line.replace("**", "")
                current_lines.append(clean_line)

        if current_lines:
            sections.append({"title": current_title, "content": " ".join(current_lines)})

        if not sections:
            sections.append({"title": "Executive Summary", "content": raw_str})

        return sections

    @classmethod
    def generate_pdf_report(
        cls,
        event_data: Dict[str, Any],
        analysis_data: Dict[str, Any],
        output_dir: str = "generated_reports"
    ) -> str:
        """
        Generates a professional executive climate readiness PDF report.
        Returns the absolute filepath of the generated PDF.
        """
        os.makedirs(output_dir, exist_ok=True)
        event_id = event_data.get("id", "event")
        filename = f"SafeStage_Climate_Readiness_Report_{event_id}.pdf"
        filepath = os.path.join(output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Clean Typography Styles matching inspiration PDF
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyRegular',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor('#334155')
        )
        body_bold = ParagraphStyle(
            'BodyBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor('#0F172A')
        )
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0F172A')
        )
        table_body_style = ParagraphStyle(
            'TableBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor('#334155')
        )

        story = []

        # ── 1. Header Banner ────────────────────────────────────────────────
        story.append(Paragraph("<b>SafeStage Climate Readiness Report</b>", title_style))
        gen_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
        story.append(Paragraph(f"Powered by FortyGuard Hyperlocal Temperature Intelligence • Generated on {gen_date}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor('#CBD5E1'), spaceAfter=12))

        # ── 2. Event Overview Table ─────────────────────────────────────────
        event_name = cls._clean_text(event_data.get("name", "Outdoor Event"))
        venue_name = cls._clean_text(event_data.get("venue_name", "Venue"))
        address = cls._clean_text(event_data.get("address", "N/A"))
        attendance = event_data.get("attendance", 0)
        supported = analysis_data.get("supported", True)

        raw_provider = analysis_data.get('provider', 'FortyGuard')
        provider_display = "FortyGuard Hyperlocal LTM" if raw_provider.lower() in ("mock", "fortyguard") else raw_provider

        overview_data = [
            [cls._cell("<b>Event Name:</b>", body_style), cls._cell(event_name, body_style)],
            [cls._cell("<b>Venue:</b>", body_style), cls._cell(f"{venue_name} ({address})", body_style)],
            [cls._cell("<b>Attendance:</b>", body_style), cls._cell(f"{attendance:,} attendees", body_style)],
            [cls._cell("<b>Intelligence Provider:</b>", body_style), cls._cell(provider_display, body_style)]
        ]
        t_overview = Table(overview_data, colWidths=[140, 400])
        t_overview.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        story.append(t_overview)
        story.append(Spacer(1, 12))

        # ── 3. Executive Climate Readiness Assessment ───────────────────────
        score = float(analysis_data.get("readiness_score", 0.0))
        label = cls._clean_text(analysis_data.get("readiness_score_label", "Climate Readiness Score"))
        score_color = colors.HexColor('#16A34A') if score >= 80 else (colors.HexColor('#D97706') if score >= 60 else colors.HexColor('#DC2626'))

        story.append(Paragraph("<b>Executive Climate Readiness Assessment</b>", section_heading))
        score_table_data = [
            [
                cls._cell(f"<b>SafeStage Readiness Score:</b> <font color='{score_color.hexval()}'><b>{score:.1f}/100</b></font>", body_style),
                cls._cell(f"<b>Classification:</b> {label}", body_style)
            ]
        ]
        t_score = Table(score_table_data, colWidths=[270, 270])
        t_score.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F9FF')),
            ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor('#BAE6FD')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        story.append(t_score)
        story.append(Spacer(1, 10))

        # ── 4. Smart Date & Time Recommendation ─────────────────────────────
        best_date = analysis_data.get("best_date_option")
        if best_date:
            story.append(Paragraph("<b>Smart Date & Time Recommendation</b>", section_heading))
            b_date = cls._clean_text(best_date.get('date', ''))
            b_time = cls._clean_text(best_date.get('time', ''))
            b_score = best_date.get('score', 0)
            b_risk = cls._clean_text(best_date.get('heat_risk', 'Low'))
            b_avg = best_date.get('avg_temp_c', 0)
            b_max = best_date.get('max_temp_c', 0)

            date_info_html = (
                f"<b>Recommended Window:</b> {escape(b_date)} ({escape(b_time)})<br/>"
                f"<b>Target Score:</b> {b_score:.1f}/100 ({escape(b_risk)} Risk)<br/>"
                f"<b>Expected Temp:</b> {b_avg:.1f}°C (Max: {b_max:.1f}°C)"
            )
            story.append(Paragraph(date_info_html, body_style))
            story.append(Spacer(1, 10))

        # ── 5. Venue Layout Optimization ────────────────────────────────────
        venue_recs = analysis_data.get("venue_layout_recommendations", [])
        if venue_recs:
            story.append(Paragraph("<b>Venue Layout Optimization</b>", section_heading))
            v_data = [
                [
                    cls._cell("Element", table_header_style),
                    cls._cell("Recommended Placement", table_header_style),
                    cls._cell("Operational Rationale", table_header_style)
                ]
            ]
            for vr in venue_recs:
                elem = cls._clean_text(vr.get("element", "Element"))
                loc = cls._clean_text(vr.get("recommended_location", "Zone"))
                rat = cls._clean_text(vr.get("rationale", ""))
                v_data.append([
                    cls._cell(elem, body_bold),
                    cls._cell(loc, table_body_style),
                    cls._cell(rat, table_body_style)
                ])

            t_venue = Table(v_data, colWidths=[120, 150, 270], repeatRows=1)
            t_venue.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(t_venue)
            story.append(Spacer(1, 12))

        # ── 6. AI Operations Copilot Summary ────────────────────────────────
        ai_exp = analysis_data.get("ai_explanation", "")
        if ai_exp:
            story.append(Paragraph("<b>AI Operations Copilot Summary</b>", section_heading))
            parsed_sections = cls._parse_ai_summary(ai_exp)
            for sec in parsed_sections:
                title = escape(sec["title"])
                content = escape(cls._clean_text(sec["content"]))
                story.append(Paragraph(f"<b>{title}:</b> {content}", body_style))
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 10))

        # ── 7. FortyGuard Climate Metrics Grid ──────────────────────────────
        temp_summary = analysis_data.get("temperature_summary", {})
        if temp_summary:
            story.append(Paragraph("<b>FortyGuard Climate Metrics</b>", section_heading))
            avg_t = temp_summary.get("avg_temperature_c")
            max_t = temp_summary.get("max_temperature_c")
            hi_t = temp_summary.get("max_heat_index_c")
            wbgt_t = temp_summary.get("wbgt_c")
            uhi_t = temp_summary.get("uhi_intensity_c")
            canopy_t = temp_summary.get("canopy_cover_pct")

            metric_rows = [
                [cls._cell("Average temperature", table_body_style), cls._cell(f"{avg_t:.1f} °C" if avg_t is not None else "N/A", table_body_style)],
                [cls._cell("Maximum temperature", table_body_style), cls._cell(f"{max_t:.1f} °C" if max_t is not None else "N/A", table_body_style)],
                [cls._cell("Maximum heat index", table_body_style), cls._cell(f"{hi_t:.1f} °C" if hi_t is not None else "N/A", table_body_style)],
                [cls._cell("WBGT", table_body_style), cls._cell(f"{wbgt_t:.1f} °C" if wbgt_t is not None else "N/A", table_body_style)],
                [cls._cell("UHI intensity", table_body_style), cls._cell(f"{uhi_t:.1f} °C" if uhi_t is not None else "N/A", table_body_style)],
                [cls._cell("Canopy cover", table_body_style), cls._cell(f"{canopy_t:.1f}%" if canopy_t is not None else "N/A", table_body_style)]
            ]
            t_metrics = Table(metric_rows, colWidths=[180, 360])
            t_metrics.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            story.append(t_metrics)
            story.append(Spacer(1, 10))

            deductions = temp_summary.get("deductions", [])
            if deductions:
                story.append(Paragraph("<b>Readiness Score Deductions</b>", section_heading))
                for deduction in deductions:
                    story.append(Paragraph(f"- {escape(cls._clean_text(deduction))}", body_style))
                story.append(Spacer(1, 10))

        # ── 8. SafeStage Operational Recommendations ────────────────────────
        recommendations = analysis_data.get("recommendations", [])
        if recommendations:
            story.append(Paragraph("<b>SafeStage Operational Recommendations</b>", section_heading))
            for r in recommendations:
                title = cls._clean_text(r.get("title") or r.get("recommendation", "Operational Action"))
                rec_text = cls._clean_text(r.get("recommendation", ""))
                reason = cls._clean_text(r.get("reasoning", ""))
                
                story.append(Paragraph(f"<b>{escape(title)}</b>", body_bold))
                if rec_text and rec_text != title:
                    story.append(Paragraph(escape(rec_text), body_style))
                if reason:
                    story.append(Paragraph(f"<i>Reasoning:</i> {escape(reason)}", body_style))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 10))

        # ── 9. All Smart Date Options ───────────────────────────────────────
        all_dates = analysis_data.get("smart_date_recommendations", [])
        if all_dates:
            story.append(Paragraph("<b>All Smart Date Options</b>", section_heading))
            for option in all_dates:
                d_val = cls._clean_text(option.get("date", ""))
                t_val = cls._clean_text(option.get("time", ""))
                s_val = f"{option.get('score', 0):.1f}/100" if isinstance(option.get('score'), (int, float)) else str(option.get('score', ''))
                r_val = cls._clean_text(option.get("heat_risk", ""))
                reasoning = option.get("reasoning", [])
                why_text = "; ".join(reasoning) if isinstance(reasoning, list) else str(reasoning)

                date_summary_data = [
                    [
                        cls._cell(d_val, body_bold),
                        cls._cell(t_val, body_style),
                        cls._cell(s_val, body_bold),
                        cls._cell(r_val, body_style)
                    ],
                    [
                        cls._cell("<b>Why this matters:</b>", body_style),
                        cls._cell(why_text, body_style),
                        "", ""
                    ]
                ]
                t_opt = Table(date_summary_data, colWidths=[120, 150, 80, 190])
                t_opt.setStyle(TableStyle([
                    ('SPAN', (1, 1), (-1, 1)),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8FAFC')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                    ('PADDING', (0, 0), (-1, -1), 5),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                story.append(t_opt)
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 10))

        # ── 10. Heat Risk Zones ─────────────────────────────────────────────
        zones = analysis_data.get("heat_risk_zones", [])
        if zones:
            story.append(Paragraph("<b>Heat Risk Zones</b>", section_heading))
            story.append(Paragraph(
                "Each zone is a planning area, not a medical forecast. The risk level combines the modeled temperature exposure and "
                "local surface/shade conditions. Use the guidance to decide where people may queue, gather, rest, receive care, or "
                "should only pass through. Extreme and high-risk zones require controls before extended occupancy.",
                body_style
            ))
            story.append(Spacer(1, 6))

            zone_rows = [
                [
                    cls._cell("Zone", table_header_style),
                    cls._cell("Risk", table_header_style),
                    cls._cell("Avg Temp", table_header_style),
                    cls._cell("Planner Use", table_header_style)
                ]
            ]
            for zone in zones:
                z_name = cls._clean_text(zone.get("name", "Zone"))
                z_risk = cls._clean_text(zone.get("risk_level", "Moderate"))
                z_temp = zone.get("avg_temp_c", "N/A")
                z_temp_str = f"{z_temp:.1f} °C" if isinstance(z_temp, (int, float)) else str(z_temp)
                z_guide = cls._zone_guidance(zone)

                zone_rows.append([
                    cls._cell(z_name, body_bold),
                    cls._cell(z_risk, table_body_style),
                    cls._cell(z_temp_str, table_body_style),
                    cls._cell(z_guide, table_body_style)
                ])

            t_zones = Table(zone_rows, colWidths=[120, 60, 70, 290], repeatRows=1)
            t_zones.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(t_zones)
            story.append(Spacer(1, 10))

        # ── 11. Footer Disclaimer ───────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=6))
        story.append(Paragraph(
            "<font size=8 color='#94A3B8'>SafeStage is a decision-support copilot powered by FortyGuard. "
            "This readiness score is designed for operational guidance and does not replace emergency management protocols.</font>",
            body_style
        ))

        doc.build(story)
        return filepath

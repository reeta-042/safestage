import os
from app.services.report_service import ReportService


def test_clean_text_strips_html_markup():
    cleaned = ReportService._clean_text("This is <b>important</b> text with <font color='red'>markup</font>.")
    assert cleaned == "This is important text with markup."


def test_pdf_report_generation(tmp_path):
    event_data = {
        "id": "evt_test123",
        "name": "Phoenix Outdoor Concert",
        "venue_name": "Phoenix Arena",
        "address": "Phoenix, Arizona",
        "attendance": 5000
    }
    analysis_data = {
        "supported": True,
        "provider": "mock",
        "readiness_score": 82.5,
        "readiness_score_label": "Optimal / Heat Safe",
        "best_date_option": {
            "date": "Saturday, Aug 15, 2026",
            "time": "17:00 - 21:00",
            "score": 89.0,
            "heat_risk": "Low",
            "avg_temp_c": 28.5,
            "max_temp_c": 30.5
        },
        "venue_layout_recommendations": [
            {
                "element": "Main Stage",
                "recommended_location": "East Zone Shade",
                "rationale": "Avoids direct afternoon solar heat glare."
            }
        ],
        "ai_explanation": "Test AI Explanation summary for PDF rendering."
    }

    output_dir = str(tmp_path)
    filepath = ReportService.generate_pdf_report(event_data, analysis_data, output_dir=output_dir)

    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 1000

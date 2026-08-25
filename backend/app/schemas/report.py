from pydantic import BaseModel
from datetime import datetime

class ReportResponse(BaseModel):
    report_id: str
    event_id: str
    download_url: str
    created_at: datetime

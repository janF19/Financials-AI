from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ReportBase(BaseModel):
    file_name: str


class ReportCreate(ReportBase):
    user_id: UUID
    report_url: str
    original_file_path: str
    status: str = "processed"
    id: Optional[UUID] = None


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    report_url: Optional[str] = None


class ReportInDB(ReportBase):
    id: UUID
    user_id: UUID
    report_url: str
    created_at: datetime
    status: str
    
    class Config:
        from_attributes = True


class Report(ReportInDB):
    pass


class ReportResponse(BaseModel):
    id: UUID
    file_name: str
    report_url: str
    created_at: datetime
    status: str


class ReportSummary(BaseModel):
    total_reports: int
    recent_reports: List[ReportResponse]
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

#models for search by person name

class PersonInfo(BaseModel):
    """Person information model"""
    full_name: str
    birth_date: Optional[str] = None
    birth_date_iso: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None

class CompanyInfo(BaseModel):
    """Company information model"""
    company_name: str
    ico: str
    file_reference: Optional[str] = None
    registration_date: Optional[str] = None
    registration_date_iso: Optional[str] = None
    person: Optional[PersonInfo] = None
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "ISOTRA a.s.",
                "ico": "47679191",
                "file_reference": "B 3169 vedená u Krajského soudu v Ostravě",
                "registration_date": "14. září 1992",
                "registration_date_iso": "1992-09-14",
                "person": {
                    "full_name": "BOHUMÍR BLACHUT",
                    "birth_date": "20. ledna 1965",
                    "birth_date_iso": "1965-01-20",
                    "address": "Úzká 167, Borová, 747 23 Bolatice",
                    "role": "člen statutárního orgánu"
                }
            }
        }

class CompanySearchByPersonResponse(BaseModel):
    """Response model for company search endpoints"""
    companies: Dict[str, CompanyInfo] = Field(
        default_factory=dict,
        description="Dictionary of companies with ICO as key"
    )
    count: int = Field(
        default=0,
        description="Number of companies found"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "companies": {
                    "47679191": {
                        "company_name": "ISOTRA a.s.",
                        "ico": "47679191",
                        "file_reference": "B 3169 vedená u Krajského soudu v Ostravě",
                        "registration_date": "14. září 1992",
                        "registration_date_iso": "1992-09-14",
                        "person": {
                            "full_name": "BOHUMÍR BLACHUT",
                            "birth_date": "20. ledna 1965",
                            "birth_date_iso": "1965-01-20",
                            "address": "Úzká 167, Borová, 747 23 Bolatice",
                            "role": "člen statutárního orgánu"
                        }
                    }
                },
                "count": 1
            }
        }

class CompanySearchByNameResponse(BaseModel):
    """Response model for company search by name endpoints
    
    """
    companies: Dict[str, CompanyInfo] = Field(
        default_factory=dict,
        description="Dictionary of companies with ICO as key"
    )
    count: int = Field(
        default=0,
        description="Number of companies found"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "companies": {
                    "47679191": {
                        "company_name": "ISOTRA a.s.",
                        "ico": "47679191",
                        "file_reference": "B 3169 vedená u Krajského soudu v Ostravě",
                        "registration_date": "14. září 1992",
                        "registration_date_iso": "1992-09-14"
                    }
                },
                "count": 1
            }
        }
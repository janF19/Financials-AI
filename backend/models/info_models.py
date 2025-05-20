from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

class JusticeInfoSidlo(BaseModel):
    adresa_kompletni: Optional[str] = None

class JusticeInfo(BaseModel):
    obchodni_firma: Optional[str] = None
    sídlo: Optional[JusticeInfoSidlo] = None
    identifikacni_cislo: Optional[str] = None
    pravni_forma: Optional[str] = None
    datum_vzniku_a_zapisu: Optional[str] = None
    spisova_znacka: Optional[str] = None
    predmet_podnikani: List[str] = []
    statutarni_organ_predstavenstvo: Optional[Any] = None # Can be str, list of dicts
    dozorci_rada: Optional[Any] = None # Can be str, list of dicts
    prokura: Optional[Any] = None # Can be str, list of dicts
    jediny_akcionar: Optional[Any] = None # Can be str, list of dicts
    akcie: List[Any] = [] # Can be list of str or list of dicts
    zakladni_kapital: Optional[str] = None
    splaceno: Optional[str] = None
    ostatni_skutecnosti: List[str] = []

class DphInfo(BaseModel):
    nespolehlivy_platce: Optional[str] = None # e.g., "NE", "ANO"
    registrace_od_data: Optional[str] = None

class DotaceInfo(BaseModel):
    uvolnena: Optional[float] = None

# class WebSearchAnalysisItem(BaseModel):
#     title: Optional[str] = None
#     link: Optional[str] = None
#     snippet: Optional[str] = None
#     source: Optional[str] = None
    # Add other fields if present in the summary items

class WebSearchAnalysis(BaseModel):
    name: Optional[str] = None
    summary: Optional[List[str]] = None

class CompanyAllInfoResponse(BaseModel):
    justice_info: Optional[JusticeInfo] = None
    dph_info: Optional[DphInfo] = None
    dotace_info: Optional[DotaceInfo] = None
    web_search_analysis: Optional[WebSearchAnalysis] = None 
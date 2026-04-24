from pydantic import BaseModel
from typing import List, Optional

class Name(BaseModel):
    prefix: Optional[str] = None
    first: str
    middle: Optional[str] = None
    last: str
    suffix: Optional[str] = None
    preferred: Optional[str] = None
    use: str = "LEGAL"

class Address(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal: str
    country: str
    type: Optional[str] = None
    preferred: bool = False

class ContactMethod(BaseModel):
    method: str
    value: str
    note: Optional[str] = None
    preferred: bool = False
    active: bool = True

class Demographic(BaseModel):
    name: Name
    dob: str 
    gender: str
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    mrn: str

class Insurance(BaseModel):
    type: str
    insurer: str
    plan: str
    policy: str
    group: Optional[str] = None
    member_id: str
    effective: str
    termination: Optional[str] = None
    copay: float = 0.0
    status: Optional[str] = None

class EmergencyContact(BaseModel):
    priority: int
    name: Name
    relationship: str
    addresses: List[Address]
    methods: List[ContactMethod]
    note: Optional[str] = None

class PatientReport(BaseModel):
    demographic: Demographic
    addresses: List[Address]
    methods: List[ContactMethod]
    insurance: List[Insurance]
    emergency: List[EmergencyContact]
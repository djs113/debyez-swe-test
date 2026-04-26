from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

class Name(BaseModel):
    prefix: Optional[str] = None
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    suffix: Optional[str] = None
    preferred_name: Optional[str] = None
    name_use: str = "LEGAL"

class Address(BaseModel):
    street_line1: str
    street_line2: Optional[str] = None
    city: str
    state_province: str
    postal_code: str
    country_code: str
    address_type: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    preferred: bool = False

class ContactMethod(BaseModel):
    method: str
    value: str
    note: Optional[str] = None
    preferred: bool = False
    active: bool = True

class Demographic(BaseModel):
    name: Name
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    ethnicity: Optional[str] = None
    primary_language: Optional[str] = None
    interpreter_required: Optional[bool] = None
    religion: Optional[str] = None
    occupation: Optional[str] = None

class Insurance(BaseModel):
    insurance_type: str
    insurer_name: str
    plan_name: str
    policy_number: str
    group_number: Optional[str] = None
    member_id: str
    subscriber_name: Optional[Name] = None
    subscriber_dob: Optional[date] = None
    relationship_to_patient: Optional[str] = None
    effective_date: date
    termination_date: Optional[date] = None
    copay_amount: Optional[float] = None
    deductible_amount: Optional[float] = None
    verification_status: Optional[str] = None
    verified_date: Optional[date] = None
    pre_auth_required: Optional[bool] = None
    notes: Optional[str] = None
    active: bool = True

class EmergencyContact(BaseModel):
    priority: int
    name: Name
    relationship: str
    addresses: List[Address]
    methods: List[ContactMethod]
    note: Optional[str] = None
    legal_guardian: bool = False

class Allergy(BaseModel):
    allergen: str
    allergen_type: str
    severity: str
    reaction: Optional[str] = None
    onset_date: Optional[date] = None
    verified_by: Optional[str] = None
    status: str = "ACTIVE"
    recorded: Optional[datetime] = None

class ExternalId(BaseModel):
    id_type: str
    id_value: str
    issuer: Optional[str] = None

class RegistrationMetadata(BaseModel):
    registration_date: datetime
    registration_facility: str
    registered_by: str
    last_updated: Optional[datetime] = None
    last_updated_by: Optional[str] = None
    source_system: Optional[str] = None
    external_ids: List['ExternalId'] = []

class PatientReport(BaseModel):
    mrn: str
    status: str
    version: int = 1
    demographics: Demographic
    addresses: List[Address]
    methods: List[ContactMethod]
    insurance: List[Insurance]
    allergies: List['Allergy']
    emergency: List[EmergencyContact]
    registration_metadata: RegistrationMetadata
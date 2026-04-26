from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

class ProviderReference(BaseModel):
    role: str
    provider_id: str
    provider_name: str
    specialty: Optional[str] = None
    npi_number: Optional[str] = None
    department: Optional[str] = None

class VitalSignObservation(BaseModel):
    recorded_at: datetime
    recorded_by: Optional[str] = None
    abnormal: bool = False
    code: str
    value: Decimal
    unit: str
    reference_range_low: Optional[Decimal] = None
    reference_range_high: Optional[Decimal] = None
    interpretation: Optional[str] = None
    method_note: Optional[str] = None

class ICD10Code(BaseModel):
    code: str
    description: str
    code_system: str = "ICD-10-CM"

class Diagnosis(BaseModel):
    diagnosis_id: str
    primary: bool = False
    rank: Optional[int] = None
    icd10_code: ICD10Code
    clinical_description: Optional[str] = None
    onset_date: Optional[date] = None
    resolved_date: Optional[date] = None
    confirmation_status: str
    diagnosed_by: Optional[str] = None
    notes: Optional[str] = None

class MedicationOrder(BaseModel):
    order_id: str
    status: str = "PENDING"
    controlled: bool = False
    medication_name: str
    generic_name: Optional[str] = None
    rx_norm_code: Optional[str] = None
    dosage: str
    route: str
    frequency: str
    duration: Optional[str] = None
    quantity: Optional[Decimal] = None
    refills: Optional[int] = None
    instructions: Optional[str] = None
    ordered_by: str
    ordered_at: datetime
    pharmacy_notes: Optional[str] = None
    linked_diagnosis_id: Optional[str] = None

class LabOrder(BaseModel):
    order_id: str
    status: str = "PENDING"
    stat: bool = False
    test_name: str
    loinc_code: Optional[str] = None
    priority: str = "ROUTINE"
    collection_method: Optional[str] = None
    specimen_type: Optional[str] = None
    ordered_by: str
    ordered_at: datetime
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None
    abnormal_flags: Optional[str] = None
    linked_diagnosis_id: Optional[str] = None
    notes: Optional[str] = None

class Procedure(BaseModel):
    procedure_id: str
    status: str = "PERFORMED"
    billable: bool = True
    procedure_name: str
    cpt_code: Optional[str] = None
    description: Optional[str] = None
    performed_by: str
    performed_at: datetime
    duration_minutes: Optional[int] = None
    anesthesia_type: Optional[str] = None
    complications: Optional[str] = None
    outcome: Optional[str] = None
    linked_diagnosis_id: Optional[str] = None
    notes: Optional[str] = None

class ClinicalNote(BaseModel):
    note_id: str
    signed: bool = False
    locked: bool = False
    note_type: str
    author_id: str
    author_name: str
    created_at: datetime
    last_amended_at: Optional[datetime] = None
    content: str
    tags: List[str] = []

class DischargeInfo(BaseModel):
    discharged_by: Optional[str] = None
    disposition: str
    discharge_date_time: Optional[datetime] = None
    discharge_condition: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    follow_up_appointment: Optional[datetime] = None
    referred_to: Optional[str] = None
    discharge_notes: Optional[str] = None

class ClinicalEncounter(BaseModel):
    encounter_id: str
    patient_mrn: str
    status: str = "IN_PROGRESS"
    version: int = 1
    confidential: bool = False
    encounter_type: str
    admission_date_time: datetime
    discharge_date_time: Optional[datetime] = None
    chief_complaint: str
    facility: str
    department: Optional[str] = None
    room: Optional[str] = None
    providers: List[ProviderReference]
    vitals_history: List[List[VitalSignObservation]] = []
    diagnoses: List[Diagnosis] = []
    medication_orders: List[MedicationOrder] = []
    lab_orders: List[LabOrder] = []
    procedures: List[Procedure] = []
    clinical_notes: List[ClinicalNote] = []
    discharge_info: Optional[DischargeInfo] = None
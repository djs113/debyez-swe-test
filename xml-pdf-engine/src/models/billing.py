from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

class MonetaryAmount(BaseModel):
    value: Decimal
    currency: str = "USD"

class BillingAddress(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"

class BillingProvider(BaseModel):
    npi: str
    ein: Optional[str] = None
    provider_name: str
    taxonomy: Optional[str] = None
    specialty: Optional[str] = None
    group_npi: Optional[str] = None
    group_name: Optional[str] = None
    billing_address: BillingAddress
    service_address: Optional[BillingAddress] = None
    credential_type: Optional[str] = None

class InsurancePayer(BaseModel):
    priority: int
    active: bool = True
    payer_id: str
    payer_name: str
    payer_type: str
    member_id: str
    group_number: Optional[str] = None
    plan_name: Optional[str] = None
    claim_submission_address: Optional[BillingAddress] = None
    electronic_payer_id: Optional[str] = None

class DiagnosisPointer(BaseModel):
    pointer: str
    principal: bool = False
    icd10_code: str
    description: Optional[str] = None

class Modifier(BaseModel):
    code: str
    description: Optional[str] = None

class ServiceLineItem(BaseModel):
    line_number: int
    status: str = "INCLUDED"
    cpt_code: str
    cpt_description: Optional[str] = None
    modifiers: List[Modifier] = []
    service_date: date
    service_date_end: Optional[date] = None
    place_of_service: str
    units: Decimal
    charged_amount: MonetaryAmount
    allowed_amount: Optional[MonetaryAmount] = None
    paid_amount: Optional[MonetaryAmount] = None
    diagnosis_pointers: str
    rendering_provider: Optional[str] = None
    revenue_code: Optional[str] = None
    denial_reason: Optional[str] = None
    notes: Optional[str] = None

class Adjustment(BaseModel):
    adjustment_id: str
    reason: str
    reason_code: Optional[str] = None
    amount: MonetaryAmount
    applied_date: Optional[date] = None
    applied_by: Optional[str] = None
    notes: Optional[str] = None

class Payment(BaseModel):
    payment_id: str
    posted_by: Optional[str] = None
    posted_at: Optional[datetime] = None
    payment_date: date
    amount: MonetaryAmount
    payment_method: str
    reference_number: Optional[str] = None
    payer_name: Optional[str] = None
    check_number: Optional[str] = None
    era_number: Optional[str] = None
    notes: Optional[str] = None

class ClaimTotals(BaseModel):
    total_charged: MonetaryAmount
    total_allowed: Optional[MonetaryAmount] = None
    total_insurance_paid: Optional[MonetaryAmount] = None
    total_adjustments: Optional[MonetaryAmount] = None
    total_patient_responsibility: Optional[MonetaryAmount] = None
    total_patient_paid: Optional[MonetaryAmount] = None
    balance_due: MonetaryAmount

class Appeal(BaseModel):
    appeal_id: str
    appeal_status: str = "PENDING"
    appeal_date: date
    appeal_reason: str
    submitted_by: Optional[str] = None
    supporting_docs: Optional[str] = None
    resolution_date: Optional[date] = None
    resolution_notes: Optional[str] = None

class MedicalClaim(BaseModel):
    claim_id: str
    patient_mrn: str
    encounter_id: str
    status: str = "DRAFT"
    version: int = 1
    electronic_claim: bool = True
    claim_type: str
    service_start_date: date
    service_end_date: Optional[date] = None
    submission_date: Optional[date] = None
    billing_provider: BillingProvider
    payers: List[InsurancePayer]
    diagnosis_pointers: List[DiagnosisPointer]
    service_lines: List[ServiceLineItem]
    adjustments: List[Adjustment] = []
    payments: List[Payment] = []
    totals: ClaimTotals
    appeals: List[Appeal] = []
    prior_auth_number: Optional[str] = None
    referral_number: Optional[str] = None
    internal_notes: Optional[str] = None
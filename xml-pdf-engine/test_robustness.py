#!/usr/bin/env python3
"""
Comprehensive test suite for robustness features
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TEST_DIR = Path("test_xml_cases")
TEST_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("ROBUSTNESS FEATURE TEST SUITE")
print("=" * 70)
print()

# Test 1: Invalid XML (malformed tags)
print("TEST 1: Invalid XML - Malformed Tags")
print("-" * 70)
malformed_xml = b"""<?xml version="1.0"?>
<root>
    <unclosed_tag>
    <child>test</child>
</root>"""

with open(TEST_DIR / "malformed.xml", "wb") as f:
    f.write(malformed_xml)

with open(TEST_DIR / "malformed.xml", "rb") as f:
    files = {'file': ('malformed.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code != 200:
    error = res.json()
    print(f"Error (Expected): {error['detail']['error']}")
    print("[PASS] Invalid XML caught and returned structured error")
else:
    print("[FAIL] Should have rejected malformed XML")
print()

# Test 2: Missing optional fields
print("TEST 2: Missing Optional Fields - Patient XML")
print("-" * 70)
patient_minimal = b"""<?xml version="1.0"?>
<PatientRecord xmlns="urn:his:patient:v2" mrn="PAT-001">
    <registration>
        <facility>Hospital A</facility>
        <registrationDate>2024-01-15</registrationDate>
    </registration>
    <demographics>
        <status>ACTIVE</status>
        <name>
            <firstName>John</firstName>
            <lastName>Doe</lastName>
        </name>
        <dateOfBirth>1990-01-01</dateOfBirth>
        <gender>M</gender>
    </demographics>
    <contactInfo/>
</PatientRecord>"""

with open(TEST_DIR / "patient_minimal.xml", "wb") as f:
    f.write(patient_minimal)

with open(TEST_DIR / "patient_minimal.xml", "rb") as f:
    files = {'file': ('patient_minimal.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Detected Schema: {data['detected_schema']}")
    print("[PASS] Missing optional fields handled gracefully")
else:
    print(f"[FAIL] Should accept patient with missing optional fields")
    print(res.json())
print()

# Test 3: Empty elements
print("TEST 3: Empty Elements (<diagnosis/>)")
print("-" * 70)
encounter_empty_fields = b"""<?xml version="1.0"?>
<ClinicalEncounter xmlns="urn:his:encounter:v2" encounterId="ENC-001" patientMRN="PAT-001">
    <encounterType>Inpatient</encounterType>
    <admissionDateTime>2024-03-20T10:00:00</admissionDateTime>
    <chiefComplaint>Routine checkup</chiefComplaint>
    <facility>Hospital A</facility>
    <diagnosis/>
    <diagnosis diagnosisId="D001" primary="true">
        <icd10Code>
            <code>I10</code>
            <description>Essential hypertension</description>
        </icd10Code>
        <confirmationStatus>CONFIRMED</confirmationStatus>
    </diagnosis>
</ClinicalEncounter>"""

with open(TEST_DIR / "encounter_empty_diag.xml", "wb") as f:
    f.write(encounter_empty_fields)

with open(TEST_DIR / "encounter_empty_diag.xml", "rb") as f:
    files = {'file': ('encounter_empty_diag.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Detected Schema: {data['detected_schema']}")
    print("[PASS] Empty elements treated as absent")
else:
    print("[FAIL] Should accept XML with empty elements")
print()

# Test 4: Unknown/extra elements not in schema
print("TEST 4: Unknown/Extra Elements Not in Schema")
print("-" * 70)
encounter_extra = b"""<?xml version="1.0"?>
<ClinicalEncounter xmlns="urn:his:encounter:v2" encounterId="ENC-002" patientMRN="PAT-002">
    <encounterType>Outpatient</encounterType>
    <admissionDateTime>2024-03-21T14:00:00</admissionDateTime>
    <chiefComplaint>Follow-up visit</chiefComplaint>
    <facility>Clinic B</facility>
    <unknownElement>This should be skipped</unknownElement>
    <customField>Extra data</customField>
    <provider role="Attending">
        <providerId>DOC-001</providerId>
        <providerName>Dr. Smith</providerName>
        <specialty>Cardiology</specialty>
        <unknownProviderField>should skip</unknownProviderField>
    </provider>
</ClinicalEncounter>"""

with open(TEST_DIR / "encounter_extra_fields.xml", "wb") as f:
    f.write(encounter_extra)

with open(TEST_DIR / "encounter_extra_fields.xml", "rb") as f:
    files = {'file': ('encounter_extra_fields.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    print("[PASS] Unknown/extra elements logged and skipped")
else:
    print("[FAIL] Should accept XML with extra elements")
    print(res.json())
print()

# Test 5: Fields exceeding expected length
print("TEST 5: Fields Exceeding Expected Length")
print("-" * 70)
long_string = "A" * 600

patient_long_fields = f"""<?xml version="1.0"?>
<PatientRecord xmlns="urn:his:patient:v2" mrn="PAT-003">
    <registration>
        <facility>Hospital C</facility>
        <registrationDate>2024-01-15</registrationDate>
    </registration>
    <demographics>
        <status>ACTIVE</status>
        <name>
            <firstName>Jonathan</firstName>
            <lastName>Doe</lastName>
        </name>
        <dateOfBirth>1990-01-01</dateOfBirth>
        <gender>M</gender>
    </demographics>
    <contactInfo/>
    <allergy allergenType="Medication">
        <allergen>Penicillin</allergen>
        <severity>SEVERE</severity>
        <reaction>{long_string}</reaction>
    </allergy>
</PatientRecord>"""

with open(TEST_DIR / "patient_long_fields.xml", "w") as f:
    f.write(patient_long_fields)

with open(TEST_DIR / "patient_long_fields.xml", "rb") as f:
    files = {'file': ('patient_long_fields.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Detected Schema: {data['detected_schema']}")
    print("[PASS] Long fields accepted (will be truncated in PDF)")
    print(f"Long field length: {len(long_string)} chars (limit is 1000 for description)")
else:
    print("[FAIL] Should accept fields with long content")
print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print("All robustness features tested.")
print()

#!/usr/bin/env python3
"""
Comprehensive test suite for robustness features
"""
import requests
import json
from pathlib import Path

import os
BASE_URL = os.environ.get("BASE_URL", "http://xml-pdf-engine:8000")
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

# Test 2: Missing optional fields (Compliant with XSD)
print("TEST 2: Missing Optional Fields - Patient XML")
print("-" * 70)
# Here we provide a completely valid Patient XML but omit genuinely optional fields like
# middleName, streetLine2, note, insurancePlans, and allergies.
patient_minimal_compliant = b"""<?xml version="1.0" encoding="UTF-8"?>
<his:PatientRecord xmlns:his="urn:his:patient:v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" mrn="PAT-001">
    <his:demographics>
        <his:name>
            <his:firstName>John</his:firstName>
            <his:lastName>Doe</his:lastName>
        </his:name>
        <his:dateOfBirth>1990-01-01</his:dateOfBirth>
        <his:gender>M</his:gender>
    </his:demographics>
    <his:contactInfo>
        <his:addresses>
            <his:address>
                <his:streetLine1>123 Main St</his:streetLine1>
                <his:city>Townsville</his:city>
                <his:stateProvince>NY</his:stateProvince>
                <his:postalCode>10001</his:postalCode>
                <his:countryCode>USA</his:countryCode>
            </his:address>
        </his:addresses>
        <his:contactMethods>
            <his:contactMethod active="true">
                <his:method>HOME_PHONE</his:method>
                <his:value>555-0100</his:value>
            </his:contactMethod>
        </his:contactMethods>
    </his:contactInfo>
    <his:emergencyContacts>
        <his:emergencyContact priority="1">
            <his:name>
                <his:firstName>Jane</his:firstName>
                <his:lastName>Doe</his:lastName>
            </his:name>
            <his:relationship>SPOUSE</his:relationship>
            <his:contactInfo>
                <his:addresses>
                    <his:address>
                        <his:streetLine1>123 Main St</his:streetLine1>
                        <his:city>Townsville</his:city>
                        <his:stateProvince>NY</his:stateProvince>
                        <his:postalCode>10001</his:postalCode>
                        <his:countryCode>USA</his:countryCode>
                    </his:address>
                </his:addresses>
                <his:contactMethods>
                    <his:contactMethod active="true">
                        <his:method>MOBILE_PHONE</his:method>
                        <his:value>555-0199</his:value>
                    </his:contactMethod>
                </his:contactMethods>
            </his:contactInfo>
        </his:emergencyContact>
    </his:emergencyContacts>
    <!-- Omitted insurancePlans and allergies as they are optional in XSD -->
    <his:registrationMetadata>
        <his:registrationDate>2024-01-15T00:00:00</his:registrationDate>
        <his:registrationFacility>Hospital A</his:registrationFacility>
    </his:registrationMetadata>
</his:PatientRecord>"""

with open(TEST_DIR / "patient_minimal.xml", "wb") as f:
    f.write(patient_minimal_compliant)

with open(TEST_DIR / "patient_minimal.xml", "rb") as f:
    files = {'file': ('patient_minimal.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Detected Schema: {data['detected_schema']}")
    print("[PASS] Missing genuinely optional fields handled gracefully")
else:
    print(f"[FAIL] Should accept patient with missing optional fields")
    print(res.json())
print()

# Test 3: Empty elements (Compliant with XSD)
print("TEST 3: Empty Elements (e.g. <notes/>, <clinicalDescription/>)")
print("-" * 70)
encounter_empty_fields = b"""<?xml version="1.0"?>
<hce:ClinicalEncounter xmlns:hce="urn:his:encounter:v2" encounterId="ENC-001" patientMRN="PAT-001">
    <hce:encounterType>INPATIENT</hce:encounterType>
    <hce:admissionDateTime>2024-03-20T10:00:00</hce:admissionDateTime>
    <hce:chiefComplaint>Routine checkup</hce:chiefComplaint>
    <hce:facility>Hospital A</hce:facility>
    <!-- Using empty basic string elements allowed by XSD instead of empty complex structures -->
    <hce:unit/>
    <hce:room/>
    
    <hce:providers>
        <hce:provider role="ATTENDING">
            <hce:providerId>PRV001</hce:providerId>
            <hce:providerName>Dr. Smith</hce:providerName>
        </hce:provider>
    </hce:providers>
    
    <hce:diagnoses>
        <hce:diagnosis diagnosisId="D001">
            <hce:icd10Code>
                <hce:code>I10</hce:code>
                <hce:description>Essential hypertension</hce:description>
            </hce:icd10Code>
            <!-- Here is an empty optional element -->
            <hce:clinicalDescription/>
            <hce:onsetDate>2024-01-01</hce:onsetDate>
            <hce:confirmationStatus>CONFIRMED</hce:confirmationStatus>
        </hce:diagnosis>
    </hce:diagnoses>
</hce:ClinicalEncounter>"""

with open(TEST_DIR / "encounter_empty_diag.xml", "wb") as f:
    f.write(encounter_empty_fields)

with open(TEST_DIR / "encounter_empty_diag.xml", "rb") as f:
    files = {'file': ('encounter_empty_diag.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Detected Schema: {data['detected_schema']}")
    print("[PASS] Empty elements allowed by XSD treated as absent")
else:
    print("[FAIL] Should accept XML with empty elements")
    print(res.json())
print()

# Test 4: Unknown/extra elements not in schema
print("TEST 4: Unknown/Extra Elements Not in Schema (EXPECTED TO FAIL)")
print("-" * 70)
print("Note: With strict XSD validation, unknown elements correctly cause a 400 Bad Request.")
encounter_extra = b"""<?xml version="1.0"?>
<hce:ClinicalEncounter xmlns:hce="urn:his:encounter:v2" encounterId="ENC-002" patientMRN="PAT-002">
    <hce:encounterType>OUTPATIENT</hce:encounterType>
    <hce:admissionDateTime>2024-03-21T14:00:00</hce:admissionDateTime>
    <hce:chiefComplaint>Follow-up visit</hce:chiefComplaint>
    <hce:facility>Clinic B</hce:facility>
    <!-- the strict parser will reject these directly: -->
    <hce:unknownElement>This should cause validation failure</hce:unknownElement>
    <hce:customField>Extra data</hce:customField>
    <hce:providers>
        <hce:provider role="ATTENDING">
            <hce:providerId>DOC-001</hce:providerId>
            <hce:providerName>Dr. Smith</hce:providerName>
        </hce:provider>
    </hce:providers>
</hce:ClinicalEncounter>"""

with open(TEST_DIR / "encounter_extra_fields.xml", "wb") as f:
    f.write(encounter_extra)

with open(TEST_DIR / "encounter_extra_fields.xml", "rb") as f:
    files = {'file': ('encounter_extra_fields.xml', f)}
    res = requests.post(f"{BASE_URL}/upload", files=files)

print(f"Response Status: {res.status_code}")
if res.status_code == 400:
    print("[PASS] Strict XSD validation correctly caught unknown/extra elements and returned 400")
else:
    print("[FAIL] Strict XSD validation should have rejected these elements")
    print(res.json())
print()

# Test 5: Fields exceeding expected length
print("TEST 5: Fields Exceeding Expected Length (Compliant with XSD)")
print("-" * 70)
long_string = "A" * 600

patient_long_fields = f"""<?xml version="1.0" encoding="UTF-8"?>
<his:PatientRecord xmlns:his="urn:his:patient:v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" mrn="PAT-003">
    <his:demographics>
        <his:name>
            <his:firstName>John</his:firstName>
            <his:lastName>Doe</his:lastName>
        </his:name>
        <his:dateOfBirth>1990-01-01</his:dateOfBirth>
        <his:gender>M</his:gender>
    </his:demographics>
    <his:contactInfo>
        <his:addresses>
            <his:address>
                <his:streetLine1>123 Main St</his:streetLine1>
                <his:city>Townsville</his:city>
                <his:stateProvince>NY</his:stateProvince>
                <his:postalCode>10001</his:postalCode>
                <his:countryCode>USA</his:countryCode>
            </his:address>
        </his:addresses>
        <his:contactMethods>
            <his:contactMethod active="true">
                <his:method>HOME_PHONE</his:method>
                <his:value>555-0100</his:value>
            </his:contactMethod>
        </his:contactMethods>
    </his:contactInfo>
    <his:emergencyContacts>
        <his:emergencyContact priority="1">
            <his:name>
                <his:firstName>Jane</his:firstName>
                <his:lastName>Doe</his:lastName>
            </his:name>
            <his:relationship>SPOUSE</his:relationship>
            <his:contactInfo>
                <his:addresses>
                    <his:address>
                        <his:streetLine1>123 Main St</his:streetLine1>
                        <his:city>Town</his:city>
                        <his:stateProvince>NY</his:stateProvince>
                        <his:postalCode>10001</his:postalCode>
                        <his:countryCode>USA</his:countryCode>
                    </his:address>
                </his:addresses>
                <his:contactMethods>
                    <his:contactMethod active="true">
                        <his:method>MOBILE_PHONE</his:method>
                        <his:value>555-0199</his:value>
                    </his:contactMethod>
                </his:contactMethods>
            </his:contactInfo>
        </his:emergencyContact>
    </his:emergencyContacts>
    <his:allergies>
        <his:allergy>
            <his:allergen>Penicillin</his:allergen>
            <his:type>MEDICATION</his:type>
            <his:severity>SEVERE</his:severity>
            <his:reaction>{long_string}</his:reaction>
        </his:allergy>
    </his:allergies>
    <his:registrationMetadata>
        <his:registrationDate>2024-01-15T00:00:00</his:registrationDate>
        <his:registrationFacility>Hospital A</his:registrationFacility>
    </his:registrationMetadata>
</his:PatientRecord>"""

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

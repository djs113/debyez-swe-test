import pytest
from src.parser.patient_parser import PatientParser

def test_patient_parser():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Patient>
    <ID>PT-001</ID>
    <FirstName>John</FirstName>
    <LastName>Doe</LastName>
    <DateOfBirth>1985-05-15</DateOfBirth>
    <Gender>Male</Gender>
    <RegistrationDate>2023-10-27T10:30:00</RegistrationDate>
</Patient>
"""
    parser = PatientParser()
    patient = parser.parse(xml_content)
    
    assert patient.id == "PT-001"
    assert patient.first_name == "John"
    assert patient.last_name == "Doe"
    assert patient.gender == "Male"

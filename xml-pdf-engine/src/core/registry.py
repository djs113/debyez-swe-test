from src.parsers.patient import PatientParser
from src.parsers.encounter import EncounterParser
from src.parsers.billing import BillingParser

SCHEMA_REGISTRY = {
    "PATIENT": {
        "parser": PatientParser(),
        "templates": ["patient_template.html", "patient_summary_template.html"]
    },
    "ENCOUNTER": {
        "parser": EncounterParser(),
        "templates": ["encounter_template.html", "encounter_summary_template.html"]
    },
    "BILLING": {
        "parser": BillingParser(),
        "templates": ["billing_template.html", "billing_summary_template.html"]
    }
}
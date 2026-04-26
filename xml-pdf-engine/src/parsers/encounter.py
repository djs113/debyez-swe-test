from lxml import etree
from src.models.encounter import *
from src.parsers.base import BaseParser
from datetime import datetime, date

class EncounterParser(BaseParser):
    def parse(self, xml_path):
        ns = {'hce': 'urn:his:encounter:v2'}
        parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()

        def get_text(node, path):
            result = node.xpath(path, namespaces=ns)
            return result[0].text if result else None

        # 1. Providers
        providers = [ProviderReference(
            role=p.get('role'),
            provider_id=get_text(p, 'hce:providerId'),
            provider_name=get_text(p, 'hce:providerName'),
            specialty=get_text(p, 'hce:specialty'),
            npi_number=get_text(p, 'hce:npiNumber'),
            department=get_text(p, 'hce:department')
        ) for p in root.xpath('.//hce:provider', namespaces=ns)]

        # 2. Diagnoses
        diagnoses = [Diagnosis(
            diagnosis_id=d.get('diagnosisId'),
            primary=d.get('primary', 'false').lower() == 'true',
            rank=int(d.get('rank')) if d.get('rank') else None,
            icd10_code=ICD10Code(
                code=get_text(d, 'hce:icd10Code/hce:code'),
                description=get_text(d, 'hce:icd10Code/hce:description'),
                code_system=get_text(d, 'hce:icd10Code/hce:codeSystem') or "ICD-10-CM"
            ),
            clinical_description=get_text(d, 'hce:clinicalDescription'),
            onsetDate=date.fromisoformat(get_text(d, 'hce:onsetDate')) if get_text(d, 'hce:onsetDate') else None,
            confirmation_status=get_text(d, 'hce:confirmationStatus'),
            diagnosed_by=get_text(d, 'hce:diagnosedBy'),
            notes=get_text(d, 'hce:notes')
        ) for d in root.xpath('.//hce:diagnosis', namespaces=ns)]

        # 3. Orders (Medication & Lab)
        meds = [MedicationOrder(
            order_id=m.get('orderId'),
            status=m.get('status', 'PENDING'),
            controlled=m.get('controlled', 'false').lower() == 'true',
            medication_name=get_text(m, 'hce:medicationName'),
            dosage=get_text(m, 'hce:dosage'),
            route=get_text(m, 'hce:route'),
            frequency=get_text(m, 'hce:frequency'),
            ordered_by=get_text(m, 'hce:orderedBy'),
            ordered_at=datetime.fromisoformat(get_text(m, 'hce:orderedAt'))
        ) for m in root.xpath('.//hce:medicationOrder', namespaces=ns)]

        labs = [LabOrder(
            order_id=l.get('orderId'),
            status=l.get('status', 'PENDING'),
            stat=l.get('stat', 'false').lower() == 'true',
            test_name=get_text(l, 'hce:testName'),
            ordered_by=get_text(l, 'hce:orderedBy'),
            ordered_at=datetime.fromisoformat(get_text(l, 'hce:orderedAt'))
        ) for l in root.xpath('.//hce:labOrder', namespaces=ns)]

        # 4. Procedures
        procedures = [Procedure(
            procedure_id=proc.get('procedureId'),
            status=proc.get('status', 'PERFORMED'),
            billable=proc.get('billable', 'true').lower() == 'true',
            procedure_name=get_text(proc, 'hce:procedureName'),
            performed_by=get_text(proc, 'hce:performedBy'),
            performed_at=datetime.fromisoformat(get_text(proc, 'hce:performedAt'))
        ) for proc in root.xpath('.//hce:procedure', namespaces=ns)]

        # 5. Clinical Notes
        notes = [ClinicalNote(
            note_id=n.get('noteId'),
            signed=n.get('signed', 'false').lower() == 'true',
            locked=n.get('locked', 'false').lower() == 'true',
            note_type=get_text(n, 'hce:noteType'),
            author_id=get_text(n, 'hce:authorId'),
            author_name=get_text(n, 'hce:authorName'),
            created_at=datetime.fromisoformat(get_text(n, 'hce:createdAt')),
            content=get_text(n, 'hce:content')
        ) for n in root.xpath('.//hce:clinicalNote', namespaces=ns)]

        # Return root object
        return ClinicalEncounter(
            encounter_id=root.get('encounterId'),
            patient_mrn=root.get('patientMRN'),
            encounter_type=get_text(root, 'hce:encounterType'),
            admission_date_time=datetime.fromisoformat(get_text(root, 'hce:admissionDateTime')),
            chief_complaint=get_text(root, 'hce:chiefComplaint'),
            facility=get_text(root, 'hce:facility'),
            providers=providers,
            diagnoses=diagnoses,
            medication_orders=meds,
            lab_orders=labs,
            procedures=procedures,
            clinical_notes=notes
        )
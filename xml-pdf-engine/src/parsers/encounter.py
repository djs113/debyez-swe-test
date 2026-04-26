from lxml import etree
from src.models.encounter import *
from src.parsers.base import BaseParser
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class EncounterParser(BaseParser):
    def parse(self, xml_path):
        ns = {'hce': 'urn:his:encounter:v2'}

        try:
            parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
            tree = etree.parse(xml_path, parser)
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            logger.error(f"Invalid XML syntax in {xml_path}: {e}")
            raise ValueError(f"Invalid XML: {e}")
        except Exception as e:
            logger.error(f"Error parsing XML {xml_path}: {e}")
            raise ValueError(f"Error parsing XML: {e}")

        # 1. Providers
        providers = []
        for p in root.xpath('.//hce:provider', namespaces=ns) or []:
            try:
                providers.append(ProviderReference(
                    role=self.safe_get_attr(p, 'role'),
                    provider_id=self.safe_get_text(p, 'hce:providerId', ns, field_type='identifier'),
                    provider_name=self.safe_get_text(p, 'hce:providerName', ns, field_type='name'),
                    specialty=self.safe_get_text(p, 'hce:specialty', ns),
                    npi_number=self.safe_get_text(p, 'hce:npiNumber', ns, field_type='identifier'),
                    department=self.safe_get_text(p, 'hce:department', ns)
                ))
            except Exception as e:
                logger.warning(f"Error parsing provider: {e}")
                continue

        # 2. Diagnoses
        diagnoses = []
        for d in root.xpath('.//hce:diagnosis', namespaces=ns) or []:
            try:
                onset_str = self.safe_get_text(d, 'hce:onsetDate', ns)
                onset_date = date.fromisoformat(onset_str) if onset_str else None

                diagnoses.append(Diagnosis(
                    diagnosis_id=self.safe_get_attr(d, 'diagnosisId'),
                    primary=self.safe_get_attr(d, 'primary', 'false').lower() == 'true',
                    rank=int(self.safe_get_attr(d, 'rank', '0')) if self.safe_get_attr(d, 'rank') else None,
                    icd10_code=ICD10Code(
                        code=self.safe_get_text(d, 'hce:icd10Code/hce:code', ns, field_type='code'),
                        description=self.safe_get_text(d, 'hce:icd10Code/hce:description', ns, field_type='description'),
                        code_system=self.safe_get_text(d, 'hce:icd10Code/hce:codeSystem', ns, default="ICD-10-CM")
                    ),
                    clinical_description=self.safe_get_text(d, 'hce:clinicalDescription', ns, field_type='description'),
                    onsetDate=onset_date,
                    confirmation_status=self.safe_get_text(d, 'hce:confirmationStatus', ns),
                    diagnosed_by=self.safe_get_text(d, 'hce:diagnosedBy', ns, field_type='name'),
                    notes=self.safe_get_text(d, 'hce:notes', ns, field_type='description')
                ))
            except ValueError as e:
                logger.warning(f"Error parsing diagnosis date: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing diagnosis: {e}")
                continue

        # 3. Medication Orders
        meds = []
        for m in root.xpath('.//hce:medicationOrder', namespaces=ns) or []:
            try:
                ordered_at_str = self.safe_get_text(m, 'hce:orderedAt', ns)
                ordered_at = datetime.fromisoformat(ordered_at_str) if ordered_at_str else None

                meds.append(MedicationOrder(
                    order_id=self.safe_get_attr(m, 'orderId'),
                    status=self.safe_get_attr(m, 'status', 'PENDING'),
                    controlled=self.safe_get_attr(m, 'controlled', 'false').lower() == 'true',
                    medication_name=self.safe_get_text(m, 'hce:medicationName', ns, field_type='text'),
                    dosage=self.safe_get_text(m, 'hce:dosage', ns),
                    route=self.safe_get_text(m, 'hce:route', ns),
                    frequency=self.safe_get_text(m, 'hce:frequency', ns),
                    ordered_by=self.safe_get_text(m, 'hce:orderedBy', ns, field_type='name'),
                    ordered_at=ordered_at
                ))
            except ValueError as e:
                logger.warning(f"Error parsing medication order datetime: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing medication order: {e}")
                continue

        # 4. Lab Orders
        labs = []
        for l in root.xpath('.//hce:labOrder', namespaces=ns) or []:
            try:
                ordered_at_str = self.safe_get_text(l, 'hce:orderedAt', ns)
                ordered_at = datetime.fromisoformat(ordered_at_str) if ordered_at_str else None

                labs.append(LabOrder(
                    order_id=self.safe_get_attr(l, 'orderId'),
                    status=self.safe_get_attr(l, 'status', 'PENDING'),
                    stat=self.safe_get_attr(l, 'stat', 'false').lower() == 'true',
                    test_name=self.safe_get_text(l, 'hce:testName', ns, field_type='text'),
                    ordered_by=self.safe_get_text(l, 'hce:orderedBy', ns, field_type='name'),
                    ordered_at=ordered_at
                ))
            except ValueError as e:
                logger.warning(f"Error parsing lab order datetime: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing lab order: {e}")
                continue

        # 5. Procedures
        procedures = []
        for proc in root.xpath('.//hce:procedure', namespaces=ns) or []:
            try:
                performed_at_str = self.safe_get_text(proc, 'hce:performedAt', ns)
                performed_at = datetime.fromisoformat(performed_at_str) if performed_at_str else None

                procedures.append(Procedure(
                    procedure_id=self.safe_get_attr(proc, 'procedureId'),
                    status=self.safe_get_attr(proc, 'status', 'PERFORMED'),
                    billable=self.safe_get_attr(proc, 'billable', 'true').lower() == 'true',
                    procedure_name=self.safe_get_text(proc, 'hce:procedureName', ns, field_type='text'),
                    performed_by=self.safe_get_text(proc, 'hce:performedBy', ns, field_type='name'),
                    performed_at=performed_at
                ))
            except ValueError as e:
                logger.warning(f"Error parsing procedure datetime: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing procedure: {e}")
                continue

        # 6. Clinical Notes
        notes = []
        for n in root.xpath('.//hce:clinicalNote', namespaces=ns) or []:
            try:
                created_at_str = self.safe_get_text(n, 'hce:createdAt', ns)
                created_at = datetime.fromisoformat(created_at_str) if created_at_str else None

                notes.append(ClinicalNote(
                    note_id=self.safe_get_attr(n, 'noteId'),
                    signed=self.safe_get_attr(n, 'signed', 'false').lower() == 'true',
                    locked=self.safe_get_attr(n, 'locked', 'false').lower() == 'true',
                    note_type=self.safe_get_text(n, 'hce:noteType', ns),
                    author_id=self.safe_get_text(n, 'hce:authorId', ns, field_type='identifier'),
                    author_name=self.safe_get_text(n, 'hce:authorName', ns, field_type='name'),
                    created_at=created_at,
                    content=self.safe_get_text(n, 'hce:content', ns, field_type='description')
                ))
            except ValueError as e:
                logger.warning(f"Error parsing clinical note datetime: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error parsing clinical note: {e}")
                continue

        # Return root object
        admission_str = self.safe_get_text(root, 'hce:admissionDateTime', ns)
        admission_dt = datetime.fromisoformat(admission_str) if admission_str else None

        return ClinicalEncounter(
            encounter_id=self.safe_get_attr(root, 'encounterId'),
            patient_mrn=self.safe_get_attr(root, 'patientMRN'),
            encounter_type=self.safe_get_text(root, 'hce:encounterType', ns),
            admission_date_time=admission_dt,
            chief_complaint=self.safe_get_text(root, 'hce:chiefComplaint', ns, field_type='description'),
            facility=self.safe_get_text(root, 'hce:facility', ns),
            providers=providers,
            diagnoses=diagnoses,
            medication_orders=meds,
            lab_orders=labs,
            procedures=procedures,
            clinical_notes=notes
        )
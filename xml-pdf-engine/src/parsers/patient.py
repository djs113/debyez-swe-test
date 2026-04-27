from lxml import etree
from datetime import datetime
import logging
from src.models.patient import (
    PatientReport, Demographic, Insurance, EmergencyContact, Address,
    ContactMethod, Name, RegistrationMetadata, Allergy, ExternalId
)
from src.parsers.base import BaseParser

logger = logging.getLogger(__name__)

class PatientParser(BaseParser):
    def parse(self, xml_path):
        ns = {'his': 'urn:his:patient:v2'}

        try:
            # Create a secure parser that disables external entity resolution
            parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
            tree = etree.parse(xml_path, parser)
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}" if e.lineno else str(e)
            logger.error(f"Invalid XML syntax in {xml_path}: {error_msg}")
            raise ValueError(f"Invalid XML: {error_msg}")
        except Exception as e:
            logger.error(f"Error parsing XML {xml_path}: {e}")
            raise ValueError(f"Error parsing XML: {e}")

        # Log any unknown elements at root level (defensive robustness)
        expected_root_elements = {
            'demographics', 'contactInfo', 'insurancePlan', 'emergencyContacts',
            'allergy', 'registration'
        }
        self.log_unknown_elements(root, expected_root_elements)

        # 1. Demographic
        demo_node = self.safe_get_element(root, '//his:demographics', namespaces=ns, required=True)
        if demo_node is None:
            raise ValueError("Required demographics section not found")

        name_node = self.safe_get_element(demo_node, 'his:name', namespaces=ns, required=True)

        demographic = Demographic(
            name=Name(
                prefix=self.safe_get_text(name_node, 'his:prefix', ns, field_type='name'),
                first_name=self.safe_get_text(name_node, 'his:firstName', ns, default="", field_type='name'),
                middle_name=self.safe_get_text(name_node, 'his:middleName', ns, field_type='name'),
                last_name=self.safe_get_text(name_node, 'his:lastName', ns, default="", field_type='name'),
                suffix=self.safe_get_text(name_node, 'his:suffix', ns, field_type='name'),
                preferred_name=self.safe_get_text(name_node, 'his:preferredName', ns, field_type='name'),
                name_use=self.safe_get_attr(name_node, 'nameUse', 'LEGAL')
            ),
            date_of_birth=self.safe_get_text(demo_node, 'his:dateOfBirth', ns, default=""),
            gender=self.safe_get_text(demo_node, 'his:gender', ns, default=""),
            blood_group=self.safe_get_text(demo_node, 'his:bloodGroup', ns),
            marital_status=self.safe_get_text(demo_node, 'his:maritalStatus', ns),
            nationality=self.safe_get_text(demo_node, 'his:nationality', ns),
            ethnicity=self.safe_get_text(demo_node, 'his:ethnicity', ns),
            primary_language=self.safe_get_text(demo_node, 'his:primaryLanguage', ns),
            interpreter_required=self.safe_get_text(self.safe_get_element(demo_node, 'his:interpreterRequired', ns), '.', ns) == 'true' if self.safe_get_element(demo_node, 'his:interpreterRequired', ns) else None,
            religion=self.safe_get_text(demo_node, 'his:religion', ns),
            occupation=self.safe_get_text(demo_node, 'his:occupation', ns)
        )

        # 2. Contacts (Main Patient - Scoped)
        contact_info_node = self.safe_get_element(root, 'his:contactInfo', namespaces=ns, required=False)

        addresses = []
        if contact_info_node is not None:
            for a in contact_info_node.xpath('his:addresses/his:address', namespaces=ns) or []:
                try:
                    eff_from = self.safe_get_text(a, 'his:effectiveFrom', ns)
                    eff_to = self.safe_get_text(a, 'his:effectiveTo', ns)
                    addresses.append(Address(
                        street_line1=self.safe_get_text(a, 'his:streetLine1', ns, default="", field_type='address'),
                        street_line2=self.safe_get_text(a, 'his:streetLine2', ns, field_type='address'),
                        city=self.safe_get_text(a, 'his:city', ns, default="", field_type='address'),
                        state_province=self.safe_get_text(a, 'his:stateProvince', ns, default="", field_type='address'),
                        postal_code=self.safe_get_text(a, 'his:postalCode', ns, default="", field_type='code'),
                        country_code=self.safe_get_text(a, 'his:countryCode', ns, default="", field_type='code'),
                        address_type=self.safe_get_text(a, 'his:addressType', ns),
                        effective_from=eff_from if eff_from else None,
                        effective_to=eff_to if eff_to else None,
                        preferred=a.get('preferred') == 'true'
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing address: {e}")
                    continue

        methods = []
        if contact_info_node is not None:
            for cm in contact_info_node.xpath('his:contactMethods/his:contactMethod', namespaces=ns) or []:
                try:
                    methods.append(ContactMethod(
                        method=self.safe_get_text(cm, 'his:method', ns, default=""),
                        value=self.safe_get_text(cm, 'his:value', ns, default="", field_type='phone'),
                        note=self.safe_get_text(cm, 'his:note', ns),
                        preferred=cm.get('preferred') == 'true',
                        active=cm.get('active', 'true') == 'true'
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing contact method: {e}")
                    continue

        # 3. Insurance
        insurance = []
        for i in root.xpath('.//his:insurancePlan', namespaces=ns) or []:
            try:
                # Parse subscriber info if present
                sub_name_node = self.safe_get_element(i, 'his:subscriberName', ns)
                subscriber_info = None
                if sub_name_node:
                    subscriber_info = Name(
                        prefix=self.safe_get_text(sub_name_node, 'his:prefix', ns, field_type='name'),
                        first_name=self.safe_get_text(sub_name_node, 'his:firstName', ns, default="", field_type='name'),
                        middle_name=self.safe_get_text(sub_name_node, 'his:middleName', ns, field_type='name'),
                        last_name=self.safe_get_text(sub_name_node, 'his:lastName', ns, default="", field_type='name'),
                        suffix=self.safe_get_text(sub_name_node, 'his:suffix', ns, field_type='name'),
                        preferred_name=self.safe_get_text(sub_name_node, 'his:preferredName', ns, field_type='name')
                    )

                copay = self.safe_get_text(i, 'his:copayAmount', ns, default="0")
                deductible = self.safe_get_text(i, 'his:deductibleAmount', ns)

                insurance.append(Insurance(
                    insurance_type=self.safe_get_attr(i, 'insuranceType', default=""),
                    insurer_name=self.safe_get_text(i, 'his:insurerName', ns, default="", field_type='text'),
                    plan_name=self.safe_get_text(i, 'his:planName', ns, default="", field_type='text'),
                    policy_number=self.safe_get_text(i, 'his:policyNumber', ns, default="", field_type='identifier'),
                    group_number=self.safe_get_text(i, 'his:groupNumber', ns, field_type='identifier'),
                    member_id=self.safe_get_text(i, 'his:memberId', ns, default="", field_type='identifier'),
                    subscriber_name=subscriber_info,
                    subscriber_dob=self.safe_get_text(i, 'his:subscriberDOB', ns),
                    relationship_to_patient=self.safe_get_text(i, 'his:relationshipToPatient', ns),
                    effective_date=self.safe_get_text(i, 'his:effectiveDate', ns, default=""),
                    termination_date=self.safe_get_text(i, 'his:terminationDate', ns),
                    copay_amount=float(copay) if copay else 0.0,
                    deductible_amount=float(deductible) if deductible else None,
                    verification_status=self.safe_get_text(i, 'his:verificationStatus', ns),
                    verified_date=self.safe_get_text(i, 'his:verifiedDate', ns),
                    pre_auth_required=self.safe_get_text(self.safe_get_element(i, 'his:preAuthRequired', ns), '.', ns) == 'true' if self.safe_get_element(i, 'his:preAuthRequired', ns) else None,
                    notes=self.safe_get_text(i, 'his:notes', ns, field_type='description'),
                    active=i.get('active', 'true') == 'true'
                ))
            except Exception as e:
                logger.warning(f"Error parsing insurance plan: {e}")
                continue

        # 4. Emergency Contacts (Full Mapping)
        def parse_contact_info(ci_node):
            ec_addresses = []
            if ci_node is not None:
                for a in ci_node.xpath('.//his:address', namespaces=ns) or []:
                    try:
                        ec_addresses.append(Address(
                            street_line1=self.safe_get_text(a, 'his:streetLine1', ns, default="", field_type='address'),
                            street_line2=self.safe_get_text(a, 'his:streetLine2', ns, field_type='address'),
                            city=self.safe_get_text(a, 'his:city', ns, default="", field_type='address'),
                            state_province=self.safe_get_text(a, 'his:stateProvince', ns, default="", field_type='address'),
                            postal_code=self.safe_get_text(a, 'his:postalCode', ns, default="", field_type='code'),
                            country_code=self.safe_get_text(a, 'his:countryCode', ns, default="", field_type='code'),
                            address_type=self.safe_get_text(a, 'his:addressType', ns),
                            effective_from=None,
                            effective_to=None,
                            preferred=a.get('preferred') == 'true'
                        ))
                    except Exception as e:
                        logger.warning(f"Error parsing emergency contact address: {e}")
                        continue

            ec_methods = []
            if ci_node is not None:
                for cm in ci_node.xpath('.//his:contactMethod', namespaces=ns) or []:
                    try:
                        ec_methods.append(ContactMethod(
                            method=self.safe_get_text(cm, 'his:method', ns, default=""),
                            value=self.safe_get_text(cm, 'his:value', ns, default="", field_type='phone'),
                            note=self.safe_get_text(cm, 'his:note', ns),
                            preferred=cm.get('preferred') == 'true',
                            active=cm.get('active', 'true') == 'true'
                        ))
                    except Exception as e:
                        logger.warning(f"Error parsing emergency contact method: {e}")
                        continue
            return ec_addresses, ec_methods

        emergency = []
        for ec in root.xpath('.//his:emergencyContact', namespaces=ns) or []:
            try:
                name_n = self.safe_get_element(ec, 'his:name', ns)
                ci_n = self.safe_get_element(ec, 'his:contactInfo', ns)
                addr_list, method_list = parse_contact_info(ci_n) if ci_n is not None else ([], [])

                emergency.append(EmergencyContact(
                    priority=int(ec.get('priority', 0)),
                    name=Name(
                        prefix=self.safe_get_text(name_n, 'his:prefix', ns, field_type='name') if name_n is not None else None,
                        first_name=self.safe_get_text(name_n, 'his:firstName', ns, default="", field_type='name') if name_n is not None else "",
                        middle_name=self.safe_get_text(name_n, 'his:middleName', ns, field_type='name') if name_n is not None else None,
                        last_name=self.safe_get_text(name_n, 'his:lastName', ns, default="", field_type='name') if name_n is not None else "",
                        suffix=self.safe_get_text(name_n, 'his:suffix', ns, field_type='name') if name_n is not None else None,
                        preferred_name=self.safe_get_text(name_n, 'his:preferredName', ns, field_type='name') if name_n is not None else None,
                        name_use=name_n.get('nameUse', 'LEGAL') if name_n is not None else 'LEGAL'
                    ),
                    relationship=self.safe_get_text(ec, 'his:relationship', ns, default=""),
                    addresses=addr_list,
                    methods=method_list,
                    note=self.safe_get_text(ec, 'his:note', ns, field_type='description'),
                    legal_guardian=ec.get('legalGuardian') == 'true'
                ))
            except Exception as e:
                logger.warning(f"Error parsing emergency contact: {e}")
                continue

        # 5. Allergies
        allergies = []
        for allergy_node in root.xpath('.//his:allergy', namespaces=ns) or []:
            try:
                onset_date_str = self.safe_get_text(allergy_node, 'his:onsetDate', ns)
                allergies.append(Allergy(
                    allergen=self.safe_get_text(allergy_node, 'his:allergen', ns, default="", field_type='text'),
                    allergen_type=self.safe_get_text(allergy_node, 'his:allergenType', ns, default=""),
                    severity=self.safe_get_text(allergy_node, 'his:severity', ns, default=""),
                    reaction=self.safe_get_text(allergy_node, 'his:reaction', ns, field_type='description'),
                    onset_date=onset_date_str if onset_date_str else None,
                    verified_by=self.safe_get_text(allergy_node, 'his:verifiedBy', ns, field_type='name'),
                    status=self.safe_get_text(allergy_node, 'his:status', ns, default="ACTIVE"),
                    recorded=allergy_node.get('recorded')
                ))
            except Exception as e:
                logger.warning(f"Error parsing allergy: {e}")
                continue

        # 6. Registration Metadata
        reg_node = self.safe_get_element(root, '//his:registration', ns)

        # Parse external IDs
        external_ids = []
        if reg_node:
            for ext_id_node in reg_node.xpath('.//his:externalId', namespaces=ns) or []:
                try:
                    external_ids.append(ExternalId(
                        id_type=self.safe_get_text(ext_id_node, 'his:idType', ns, default="", field_type='code'),
                        id_value=self.safe_get_text(ext_id_node, 'his:idValue', ns, default="", field_type='identifier'),
                        issuer=self.safe_get_text(ext_id_node, 'his:issuer', ns)
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing external ID: {e}")
                    continue

        try:
            reg_facility = self.safe_get_text(reg_node, 'his:facility', ns, default="Unknown") if reg_node else "Unknown"
            reg_date_str = self.safe_get_text(reg_node, 'his:registrationDate', ns) if reg_node else None
            reg_date = datetime.fromisoformat(reg_date_str) if reg_date_str else datetime.now()
            last_upd_str = self.safe_get_text(reg_node, 'his:lastUpdated', ns) if reg_node else None
            last_upd = datetime.fromisoformat(last_upd_str) if last_upd_str else None
        except ValueError as e:
            logger.warning(f"Error parsing registration dates: {e}")
            reg_date = datetime.now()
            last_upd = None

        registration_metadata = RegistrationMetadata(
            registration_facility=reg_facility,
            registration_date=reg_date,
            registered_by=self.safe_get_text(reg_node, 'his:registeredBy', ns, default="") if reg_node else "",
            last_updated=last_upd,
            last_updated_by=self.safe_get_text(reg_node, 'his:lastUpdatedBy', ns) if reg_node else None,
            source_system=self.safe_get_text(reg_node, 'his:sourceSystem', ns, default="HIS") if reg_node else "HIS",
            external_ids=external_ids
        )

        return PatientReport(
            mrn=self.safe_get_attr(root, 'mrn', default="", field_type='identifier'),
            status=self.safe_get_text(demo_node, 'his:status', ns, default="ACTIVE") if demo_node is not None else "ACTIVE",
            demographics=demographic,
            addresses=addresses,
            methods=methods,
            insurance=insurance,
            allergies=allergies,
            emergency=emergency,
            registration_metadata=registration_metadata
        )
from lxml import etree
from datetime import datetime
from src.models.patient import (
    PatientReport, Demographic, Insurance, EmergencyContact, Address, 
    ContactMethod, Name, RegistrationMetadata, Allergy, ExternalId
)
from src.parsers.base import BaseParser

class PatientParser(BaseParser):
    def parse(self, xml_path):
        ns = {'his': 'urn:his:patient:v2'}
        
        # Create a secure parser that disables external entity resolution
        parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()

        def get_text(node, path):
            result = node.xpath(path, namespaces=ns)
            return result[0].text if result else None

        # 1. Demographic
        demo_node = root.xpath('//his:demographics', namespaces=ns)[0]
        name_node = demo_node.xpath('his:name', namespaces=ns)[0]
        
        demographic = Demographic(
            name=Name(
                prefix=get_text(name_node, 'his:prefix'),
                first_name=get_text(name_node, 'his:firstName') or "",
                middle_name=get_text(name_node, 'his:middleName'),
                last_name=get_text(name_node, 'his:lastName') or "",
                suffix=get_text(name_node, 'his:suffix'),
                preferred_name=get_text(name_node, 'his:preferredName'),
                name_use=name_node.get('nameUse', 'LEGAL')
            ),
            date_of_birth=get_text(demo_node, 'his:dateOfBirth') or "",
            gender=get_text(demo_node, 'his:gender') or "",
            blood_group=get_text(demo_node, 'his:bloodGroup'),
            marital_status=get_text(demo_node, 'his:maritalStatus'),
            nationality=get_text(demo_node, 'his:nationality'),
            ethnicity=get_text(demo_node, 'his:ethnicity'),
            primary_language=get_text(demo_node, 'his:primaryLanguage'),
            interpreter_required=demo_node.xpath('his:interpreterRequired', namespaces=ns)[0].text == 'true' if demo_node.xpath('his:interpreterRequired', namespaces=ns) else None,
            religion=get_text(demo_node, 'his:religion'),
            occupation=get_text(demo_node, 'his:occupation')
        )

        # 2. Contacts (Main Patient - Scoped)
        contact_info_node = root.xpath('his:contactInfo', namespaces=ns)[0]
        
        addresses = [Address(
            street_line1=get_text(a, 'his:streetLine1') or "",
            street_line2=get_text(a, 'his:streetLine2'),
            city=get_text(a, 'his:city') or "",
            state_province=get_text(a, 'his:stateProvince') or "",
            postal_code=get_text(a, 'his:postalCode') or "",
            country_code=get_text(a, 'his:countryCode') or "",
            address_type=get_text(a, 'his:addressType'),
            effective_from=get_text(a, 'his:effectiveFrom'),
            effective_to=get_text(a, 'his:effectiveTo'),
            preferred=a.get('preferred') == 'true'
        ) for a in contact_info_node.xpath('his:addresses/his:address', namespaces=ns)]

        methods = [ContactMethod(
            method=get_text(cm, 'his:method') or "",
            value=get_text(cm, 'his:value') or "",
            note=get_text(cm, 'his:note'),
            preferred=cm.get('preferred') == 'true',
            active=cm.get('active', 'true') == 'true'
        ) for cm in contact_info_node.xpath('his:contactMethods/his:contactMethod', namespaces=ns)]

        # 3. Insurance
        insurance = []
        for i in root.xpath('.//his:insurancePlan', namespaces=ns):
            # Parse subscriber info if present
            subscriber_node = i.xpath('his:subscriberName', namespaces=ns)
            subscriber_info = None
            if subscriber_node:
                sub_name_node = subscriber_node[0]
                subscriber_info = Name(
                    prefix=get_text(sub_name_node, 'his:prefix'),
                    first_name=get_text(sub_name_node, 'his:firstName') or "",
                    middle_name=get_text(sub_name_node, 'his:middleName'),
                    last_name=get_text(sub_name_node, 'his:lastName') or "",
                    suffix=get_text(sub_name_node, 'his:suffix'),
                    preferred_name=get_text(sub_name_node, 'his:preferredName')
                )
            
            insurance.append(Insurance(
                insurance_type=i.get('insuranceType') or "",
                insurer_name=get_text(i, 'his:insurerName') or "",
                plan_name=get_text(i, 'his:planName') or "",
                policy_number=get_text(i, 'his:policyNumber') or "",
                group_number=get_text(i, 'his:groupNumber'),
                member_id=get_text(i, 'his:memberId') or "",
                subscriber_name=subscriber_info,
                subscriber_dob=get_text(i, 'his:subscriberDOB'),
                relationship_to_patient=get_text(i, 'his:relationshipToPatient'),
                effective_date=get_text(i, 'his:effectiveDate') or "",
                termination_date=get_text(i, 'his:terminationDate'),
                copay_amount=float(get_text(i, 'his:copayAmount') or 0),
                deductible_amount=float(get_text(i, 'his:deductibleAmount') or 0) if get_text(i, 'his:deductibleAmount') else None,
                verification_status=get_text(i, 'his:verificationStatus'),
                verified_date=get_text(i, 'his:verifiedDate'),
                pre_auth_required=i.xpath('his:preAuthRequired', namespaces=ns)[0].text == 'true' if i.xpath('his:preAuthRequired', namespaces=ns) else None,
                notes=get_text(i, 'his:notes'),
                active=i.get('active', 'true') == 'true'
            ))

        # 4. Emergency Contacts (Full Mapping)
        def parse_contact_info(ci_node):
            ec_addresses = [Address(
                street_line1=get_text(a, 'his:streetLine1') or "",
                street_line2=get_text(a, 'his:streetLine2'),
                city=get_text(a, 'his:city') or "",
                state_province=get_text(a, 'his:stateProvince') or "",
                postal_code=get_text(a, 'his:postalCode') or "",
                country_code=get_text(a, 'his:countryCode') or "",
                address_type=get_text(a, 'his:addressType'),
                preferred=a.get('preferred') == 'true'
            ) for a in ci_node.xpath('.//his:address', namespaces=ns)]
            
            ec_methods = [ContactMethod(
                method=get_text(cm, 'his:method') or "",
                value=get_text(cm, 'his:value') or "",
                note=get_text(cm, 'his:note'),
                preferred=cm.get('preferred') == 'true',
                active=cm.get('active', 'true') == 'true'
            ) for cm in ci_node.xpath('.//his:contactMethod', namespaces=ns)]
            return ec_addresses, ec_methods

        emergency = []
        for ec in root.xpath('.//his:emergencyContact', namespaces=ns):
            name_n = ec.xpath('his:name', namespaces=ns)[0]
            ci_n = ec.xpath('his:contactInfo', namespaces=ns)[0]
            addr_list, method_list = parse_contact_info(ci_n)
            
            emergency.append(EmergencyContact(
                priority=int(ec.get('priority', 0)),
                name=Name(
                    prefix=get_text(name_n, 'his:prefix'),
                    first_name=get_text(name_n, 'his:firstName') or "",
                    middle_name=get_text(name_n, 'his:middleName'),
                    last_name=get_text(name_n, 'his:lastName') or "",
                    suffix=get_text(name_n, 'his:suffix'),
                    preferred_name=get_text(name_n, 'his:preferredName'),
                    name_use=name_n.get('nameUse', 'LEGAL')
                ),
                relationship=get_text(ec, 'his:relationship') or "",
                addresses=addr_list,
                methods=method_list,
                note=get_text(ec, 'his:note'),
                legal_guardian=ec.get('legalGuardian') == 'true'
            ))

        # 5. Allergies
        allergies = []
        for allergy_node in root.xpath('.//his:allergy', namespaces=ns):
            allergies.append(Allergy(
                allergen=get_text(allergy_node, 'his:allergen') or "",
                allergen_type=get_text(allergy_node, 'his:allergenType') or "",
                severity=get_text(allergy_node, 'his:severity') or "",
                reaction=get_text(allergy_node, 'his:reaction'),
                onset_date=get_text(allergy_node, 'his:onsetDate'),
                verified_by=get_text(allergy_node, 'his:verifiedBy'),
                status=get_text(allergy_node, 'his:status') or "ACTIVE",
                recorded=allergy_node.get('recorded')
            ))

        # 6. Registration Metadata
        reg_node = root.xpath('//his:registration', namespaces=ns)
        
        # Parse external IDs
        external_ids = []
        if reg_node:
            for ext_id_node in reg_node[0].xpath('.//his:externalId', namespaces=ns):
                external_ids.append(ExternalId(
                    id_type=get_text(ext_id_node, 'his:idType') or "",
                    id_value=get_text(ext_id_node, 'his:idValue') or "",
                    issuer=get_text(ext_id_node, 'his:issuer')
                ))
        
        registration_metadata = RegistrationMetadata(
            registration_facility=get_text(reg_node[0], 'his:facility') if reg_node else "Unknown",
            registration_date=datetime.fromisoformat(get_text(reg_node[0], 'his:registrationDate') or datetime.now().isoformat()) if reg_node else datetime.now(),
            registered_by=get_text(reg_node[0], 'his:registeredBy') if reg_node else "",
            last_updated=datetime.fromisoformat(get_text(reg_node[0], 'his:lastUpdated')) if reg_node and get_text(reg_node[0], 'his:lastUpdated') else None,
            last_updated_by=get_text(reg_node[0], 'his:lastUpdatedBy') if reg_node else None,
            source_system=get_text(reg_node[0], 'his:sourceSystem') if reg_node else "HIS",
            external_ids=external_ids
        )

        return PatientReport(
            mrn=root.get('mrn') or "",
            status=get_text(demo_node, 'his:status') or "ACTIVE",
            demographics=demographic, 
            addresses=addresses, 
            methods=methods, 
            insurance=insurance,
            allergies=allergies,
            emergency=emergency,
            registration_metadata=registration_metadata
        )
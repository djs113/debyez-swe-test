from lxml import etree
from src.models.patient import *

def parse_patient_xml(xml_path):
    ns = {'his': 'urn:his:patient:v2'}
    tree = etree.parse(xml_path)
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
            first=get_text(name_node, 'his:firstName') or "",
            middle=get_text(name_node, 'his:middleName'),
            last=get_text(name_node, 'his:lastName') or "",
            suffix=get_text(name_node, 'his:suffix'),
            preferred=get_text(name_node, 'his:preferredName'),
            use=name_node.get('nameUse', 'LEGAL')
        ),
        dob=get_text(demo_node, 'his:dateOfBirth') or "",
        gender=get_text(demo_node, 'his:gender') or "",
        blood_group=get_text(demo_node, 'his:bloodGroup'),
        marital_status=get_text(demo_node, 'his:maritalStatus'),
        mrn=root.get('mrn') or ""
    )

    # 2. Contacts (Main Patient - SCOPED)
    contact_info_node = root.xpath('his:contactInfo', namespaces=ns)[0]
    
    addr_nodes = contact_info_node.xpath('his:addresses/his:address', namespaces=ns)
    
    addresses = [Address(
        line1=get_text(a, 'his:streetLine1') or "",
        city=get_text(a, 'his:city') or "",
        state=get_text(a, 'his:stateProvince') or "",
        postal=get_text(a, 'his:postalCode') or "",
        country=get_text(a, 'his:countryCode') or "",
        type=get_text(a, 'his:addressType'),
        preferred=a.get('preferred') == 'true'
    ) for a in addr_nodes]

    methods = [ContactMethod(
        method=get_text(cm, 'his:method') or "",
        value=get_text(cm, 'his:value') or "",
        note=get_text(cm, 'his:note'),
        preferred=cm.get('preferred') == 'true'
    ) for cm in contact_info_node.xpath('his:contactMethods/his:contactMethod', namespaces=ns)]

    # 3. Insurance
    insurance = [Insurance(
        type=i.get('insuranceType') or "",
        insurer=get_text(i, 'his:insurerName') or "",
        plan=get_text(i, 'his:planName') or "",
        policy=get_text(i, 'his:policyNumber') or "",
        member_id=get_text(i, 'his:memberId') or "",
        effective=get_text(i, 'his:effectiveDate') or "",
        copay=float(get_text(i, 'his:copayAmount') or 0)
    ) for i in root.xpath('.//his:insurancePlan', namespaces=ns)]

    # 4. Emergency Contacts (Full Mapping)
    def parse_contact_info(ci_node):
        """Helper to parse ContactInfo block for any entity."""
        ec_addresses = [Address(
            line1=get_text(a, 'his:streetLine1') or "",
            city=get_text(a, 'his:city') or "",
            state=get_text(a, 'his:stateProvince') or "",
            postal=get_text(a, 'his:postalCode') or "",
            country=get_text(a, 'his:countryCode') or "",
            type=get_text(a, 'his:addressType'),
            preferred=a.get('preferred') == 'true'
        ) for a in ci_node.xpath('.//his:address', namespaces=ns)]
        
        ec_methods = [ContactMethod(
            method=get_text(cm, 'his:method') or "",
            value=get_text(cm, 'his:value') or "",
            note=get_text(cm, 'his:note'),
            preferred=cm.get('preferred') == 'true'
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
                first=get_text(name_n, 'his:firstName') or "",
                last=get_text(name_n, 'his:lastName') or "",
                middle=get_text(name_n, 'his:middleName')
            ),
            relationship=get_text(ec, 'his:relationship') or "",
            addresses=addr_list,
            methods=method_list,
            note=get_text(ec, 'his:note')
        ))

    return PatientReport(demographic=demographic, addresses=addresses, methods=methods, insurance=insurance, emergency=emergency)
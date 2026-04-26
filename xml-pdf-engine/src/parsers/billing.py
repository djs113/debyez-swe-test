from lxml import etree
from src.models.billing import *
from src.parsers.base import BaseParser
from decimal import Decimal
from datetime import datetime, date as dateobj

class BillingParser(BaseParser):
    def parse(self, xml_path):
        ns = {'hbill': 'urn:his:billing:v2'}
        
        # Create a secure parser that disables external entity resolution
        parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()

        def get_text(node, path):
            result = node.xpath(path, namespaces=ns)
            return result[0].text if result else None

        def get_monetary(node, path):
            val = get_text(node, path)
            nodes = node.xpath(path, namespaces=ns)
            curr = nodes[0].get('currency', 'USD') if nodes else 'USD'
            return MonetaryAmount(value=Decimal(val or 0), currency=curr) if val else None

        def parse_date(date_str):
            if not date_str:
                return None
            return dateobj.fromisoformat(date_str)

        def parse_datetime(dt_str):
            if not dt_str:
                return None
            return datetime.fromisoformat(dt_str)

        # 1. Billing Provider - ALL FIELDS
        bp = root.xpath('hbill:billingProvider', namespaces=ns)[0]
        
        # Parse service address if exists
        service_addr_nodes = bp.xpath('hbill:serviceAddress', namespaces=ns)
        service_addr = None
        if service_addr_nodes:
            sa = service_addr_nodes[0]
            service_addr = BillingAddress(
                line1=get_text(sa, 'hbill:line1'),
                line2=get_text(sa, 'hbill:line2'),
                city=get_text(sa, 'hbill:city'),
                state=get_text(sa, 'hbill:state'),
                zip=get_text(sa, 'hbill:zip'),
                country=get_text(sa, 'hbill:country') or 'US'
            )
        
        provider = BillingProvider(
            npi=get_text(bp, 'hbill:npi'),
            ein=get_text(bp, 'hbill:ein'),
            provider_name=get_text(bp, 'hbill:providerName'),
            taxonomy=get_text(bp, 'hbill:taxonomy'),
            specialty=get_text(bp, 'hbill:specialty'),
            group_npi=get_text(bp, 'hbill:groupNPI'),
            group_name=get_text(bp, 'hbill:groupName'),
            billing_address=BillingAddress(
                line1=get_text(bp, 'hbill:billingAddress/hbill:line1'),
                line2=get_text(bp, 'hbill:billingAddress/hbill:line2'),
                city=get_text(bp, 'hbill:billingAddress/hbill:city'),
                state=get_text(bp, 'hbill:billingAddress/hbill:state'),
                zip=get_text(bp, 'hbill:billingAddress/hbill:zip'),
                country=get_text(bp, 'hbill:billingAddress/hbill:country') or 'US'
            ),
            service_address=service_addr,
            credential_type=bp.get('credentialType')
        )

        # 2. Payers - ALL FIELDS
        payers = []
        for p in root.xpath('.//hbill:payer', namespaces=ns):
            # Parse claim submission address if exists
            claim_addr_nodes = p.xpath('hbill:claimSubmissionAddress', namespaces=ns)
            claim_addr = None
            if claim_addr_nodes:
                ca = claim_addr_nodes[0]
                claim_addr = BillingAddress(
                    line1=get_text(ca, 'hbill:line1'),
                    line2=get_text(ca, 'hbill:line2'),
                    city=get_text(ca, 'hbill:city'),
                    state=get_text(ca, 'hbill:state'),
                    zip=get_text(ca, 'hbill:zip'),
                    country=get_text(ca, 'hbill:country') or 'US'
                )
            
            payers.append(InsurancePayer(
                priority=int(p.get('priority')),
                active=p.get('active', 'true').lower() == 'true',
                payer_id=get_text(p, 'hbill:payerId'),
                payer_name=get_text(p, 'hbill:payerName'),
                payer_type=get_text(p, 'hbill:payerType'),
                member_id=get_text(p, 'hbill:memberId'),
                group_number=get_text(p, 'hbill:groupNumber'),
                plan_name=get_text(p, 'hbill:planName'),
                claim_submission_address=claim_addr,
                electronic_payer_id=get_text(p, 'hbill:electronicPayerId')
            ))

        # 3. Diagnosis Pointers - ALL FIELDS
        dp_nodes = root.xpath('.//hbill:diagnosisPointer', namespaces=ns)
        diagnosis_pointers = [DiagnosisPointer(
            pointer=d.get('pointer'),
            principal=d.get('principal', 'false').lower() == 'true',
            icd10_code=get_text(d, 'hbill:icd10Code'),
            description=get_text(d, 'hbill:description')
        ) for d in dp_nodes]

        # 4. Service Lines - ALL FIELDS
        service_lines = []
        for sl in root.xpath('.//hbill:serviceLineItem', namespaces=ns):
            # Parse modifiers if present
            modifiers = []
            for mod in sl.xpath('hbill:modifiers/hbill:modifier', namespaces=ns):
                modifiers.append(Modifier(
                    code=get_text(mod, 'hbill:code'),
                    description=get_text(mod, 'hbill:description')
                ))
            
            service_lines.append(ServiceLineItem(
                line_number=int(sl.get('lineNumber')),
                status=sl.get('status', 'INCLUDED'),
                cpt_code=get_text(sl, 'hbill:cptCode'),
                cpt_description=get_text(sl, 'hbill:cptDescription'),
                modifiers=modifiers,
                service_date=parse_date(get_text(sl, 'hbill:serviceDate')),
                service_date_end=parse_date(get_text(sl, 'hbill:serviceDateEnd')),
                place_of_service=get_text(sl, 'hbill:placeOfService'),
                units=Decimal(get_text(sl, 'hbill:units') or 0),
                charged_amount=get_monetary(sl, 'hbill:chargedAmount'),
                allowed_amount=get_monetary(sl, 'hbill:allowedAmount'),
                paid_amount=get_monetary(sl, 'hbill:paidAmount'),
                diagnosis_pointers=get_text(sl, 'hbill:diagnosisPointers'),
                rendering_provider=get_text(sl, 'hbill:renderingProvider'),
                revenue_code=get_text(sl, 'hbill:revenueCode'),
                denial_reason=get_text(sl, 'hbill:denialReason'),
                notes=get_text(sl, 'hbill:notes')
            ))

        # 5. Adjustments - ALL FIELDS
        adjustments = []
        for adj in root.xpath('.//hbill:adjustment', namespaces=ns):
            adjustments.append(Adjustment(
                adjustment_id=adj.get('adjustmentId'),
                reason=get_text(adj, 'hbill:reason'),
                reason_code=get_text(adj, 'hbill:reasonCode'),
                amount=get_monetary(adj, 'hbill:amount'),
                applied_date=parse_date(get_text(adj, 'hbill:appliedDate')),
                applied_by=get_text(adj, 'hbill:appliedBy'),
                notes=get_text(adj, 'hbill:notes')
            ))

        # 6. Payments - ALL FIELDS
        payments = []
        for pmt in root.xpath('.//hbill:payment', namespaces=ns):
            payments.append(Payment(
                payment_id=pmt.get('paymentId'),
                posted_by=pmt.get('postedBy'),
                posted_at=parse_datetime(pmt.get('postedAt')),
                payment_date=parse_date(get_text(pmt, 'hbill:paymentDate')),
                amount=get_monetary(pmt, 'hbill:amount'),
                payment_method=get_text(pmt, 'hbill:paymentMethod'),
                reference_number=get_text(pmt, 'hbill:referenceNumber'),
                payer_name=get_text(pmt, 'hbill:payerName'),
                check_number=get_text(pmt, 'hbill:checkNumber'),
                era_number=get_text(pmt, 'hbill:eraNumber'),
                notes=get_text(pmt, 'hbill:notes')
            ))

        # 7. Totals - ALL FIELDS
        t = root.xpath('hbill:totals', namespaces=ns)[0]
        totals = ClaimTotals(
            total_charged=get_monetary(t, 'hbill:totalCharged'),
            total_allowed=get_monetary(t, 'hbill:totalAllowed'),
            total_insurance_paid=get_monetary(t, 'hbill:totalInsurancePaid'),
            total_adjustments=get_monetary(t, 'hbill:totalAdjustments'),
            total_patient_responsibility=get_monetary(t, 'hbill:totalPatientResponsibility'),
            total_patient_paid=get_monetary(t, 'hbill:totalPatientPaid'),
            balance_due=get_monetary(t, 'hbill:balanceDue')
        )

        # 8. Appeals - ALL FIELDS
        appeals = []
        for app in root.xpath('.//hbill:appeal', namespaces=ns):
            appeals.append(Appeal(
                appeal_id=app.get('appealId'),
                appeal_status=app.get('appealStatus', 'PENDING'),
                appeal_date=parse_date(get_text(app, 'hbill:appealDate')),
                appeal_reason=get_text(app, 'hbill:appealReason'),
                submitted_by=get_text(app, 'hbill:submittedBy'),
                supporting_docs=get_text(app, 'hbill:supportingDocs'),
                resolution_date=parse_date(get_text(app, 'hbill:resolutionDate')),
                resolution_notes=get_text(app, 'hbill:resolutionNotes')
            ))

        return MedicalClaim(
            claim_id=root.get('claimId'),
            patient_mrn=root.get('patientMRN'),
            encounter_id=root.get('encounterId'),
            status=root.get('status', 'DRAFT'),
            version=int(root.get('version', 1)),
            electronic_claim=root.get('electronicClaim', 'true').lower() == 'true',
            claim_type=get_text(root, 'hbill:claimType'),
            service_start_date=parse_date(get_text(root, 'hbill:serviceStartDate')),
            service_end_date=parse_date(get_text(root, 'hbill:serviceEndDate')),
            submission_date=parse_date(get_text(root, 'hbill:submissionDate')),
            billing_provider=provider,
            payers=payers,
            diagnosis_pointers=diagnosis_pointers,
            service_lines=service_lines,
            adjustments=adjustments,
            payments=payments,
            totals=totals,
            appeals=appeals,
            prior_auth_number=get_text(root, 'hbill:priorAuthNumber'),
            referral_number=get_text(root, 'hbill:referralNumber'),
            internal_notes=get_text(root, 'hbill:internalNotes')
        )
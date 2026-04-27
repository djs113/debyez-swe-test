from lxml import etree
from src.models.billing import *
from src.parsers.base import BaseParser
from decimal import Decimal
from datetime import datetime, date as dateobj
import logging

logger = logging.getLogger(__name__)

class BillingParser(BaseParser):
    def parse(self, xml_path):
        ns = {'hbill': 'urn:his:billing:v2'}

        try:
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

        def get_monetary(node, path):
            """Safely extract monetary amount with currency."""
            val = self.safe_get_text(node, path, ns, field_type='identifier')
            nodes = node.xpath(path, namespaces=ns) if node else []
            curr = nodes[0].get('currency', 'USD') if nodes else 'USD'
            try:
                return MonetaryAmount(value=Decimal(val or 0), currency=curr) if val else None
            except Exception as e:
                logger.warning(f"Error parsing monetary amount: {e}")
                return None

        def parse_date(date_str):
            """Safely parse ISO date string."""
            if not date_str:
                return None
            try:
                return dateobj.fromisoformat(date_str)
            except ValueError as e:
                logger.warning(f"Error parsing date {date_str}: {e}")
                return None

        def parse_datetime(dt_str):
            """Safely parse ISO datetime string."""
            if not dt_str:
                return None
            try:
                return datetime.fromisoformat(dt_str)
            except ValueError as e:
                logger.warning(f"Error parsing datetime {dt_str}: {e}")
                return None

        # Log any unknown elements at root level (defensive robustness)
        expected_root_elements = {
            'claimNumber', 'serviceDate', 'billingProvider', 'servicingProvider',
            'payer', 'patient', 'procedures', 'diagnosisPointers', 'serviceLineItems',
            'adjustments', 'payments', 'appeals', 'totals'
        }
        self.log_unknown_elements(root, expected_root_elements)

        # 1. Billing Provider
        bp = self.safe_get_element(root, 'hbill:billingProvider', ns)
        if not bp:
            logger.warning("Billing provider section not found")
            bp = root

        service_addr = None
        if bp:
            service_addr_node = self.safe_get_element(bp, 'hbill:serviceAddress', ns)
            if service_addr_node:
                try:
                    service_addr = BillingAddress(
                        line1=self.safe_get_text(service_addr_node, 'hbill:line1', ns, field_type='address'),
                        line2=self.safe_get_text(service_addr_node, 'hbill:line2', ns, field_type='address'),
                        city=self.safe_get_text(service_addr_node, 'hbill:city', ns, field_type='address'),
                        state=self.safe_get_text(service_addr_node, 'hbill:state', ns, field_type='code'),
                        zip=self.safe_get_text(service_addr_node, 'hbill:zip', ns, field_type='code'),
                        country=self.safe_get_text(service_addr_node, 'hbill:country', ns, default='US')
                    )
                except Exception as e:
                    logger.warning(f"Error parsing service address: {e}")

        billing_addr_node = self.safe_get_element(bp, 'hbill:billingAddress', ns) if bp else None
        billing_addr = BillingAddress(
            line1=self.safe_get_text(billing_addr_node, 'hbill:line1', ns, field_type='address') if billing_addr_node else "",
            line2=self.safe_get_text(billing_addr_node, 'hbill:line2', ns, field_type='address') if billing_addr_node else None,
            city=self.safe_get_text(billing_addr_node, 'hbill:city', ns, field_type='address') if billing_addr_node else "",
            state=self.safe_get_text(billing_addr_node, 'hbill:state', ns, field_type='code') if billing_addr_node else "",
            zip=self.safe_get_text(billing_addr_node, 'hbill:zip', ns, field_type='code') if billing_addr_node else "",
            country=self.safe_get_text(billing_addr_node, 'hbill:country', ns, default='US') if billing_addr_node else 'US'
        )

        provider = BillingProvider(
            npi=self.safe_get_text(bp, 'hbill:npi', ns, field_type='identifier') if bp else "",
            ein=self.safe_get_text(bp, 'hbill:ein', ns, field_type='code') if bp else "",
            provider_name=self.safe_get_text(bp, 'hbill:providerName', ns, field_type='name') if bp else "",
            taxonomy=self.safe_get_text(bp, 'hbill:taxonomy', ns, field_type='code') if bp else "",
            specialty=self.safe_get_text(bp, 'hbill:specialty', ns) if bp else "",
            group_npi=self.safe_get_text(bp, 'hbill:groupNPI', ns, field_type='identifier') if bp else "",
            group_name=self.safe_get_text(bp, 'hbill:groupName', ns, field_type='name') if bp else "",
            billing_address=billing_addr,
            service_address=service_addr,
            credential_type=self.safe_get_attr(bp, 'credentialType') if bp else ""
        )

        # 2. Payers
        payers = []
        for p in root.xpath('.//hbill:payer', namespaces=ns) or []:
            try:
                claim_addr = None
                claim_addr_node = self.safe_get_element(p, 'hbill:claimSubmissionAddress', ns)
                if claim_addr_node:
                    claim_addr = BillingAddress(
                        line1=self.safe_get_text(claim_addr_node, 'hbill:line1', ns, field_type='address'),
                        line2=self.safe_get_text(claim_addr_node, 'hbill:line2', ns, field_type='address'),
                        city=self.safe_get_text(claim_addr_node, 'hbill:city', ns, field_type='address'),
                        state=self.safe_get_text(claim_addr_node, 'hbill:state', ns, field_type='code'),
                        zip=self.safe_get_text(claim_addr_node, 'hbill:zip', ns, field_type='code'),
                        country=self.safe_get_text(claim_addr_node, 'hbill:country', ns, default='US')
                    )

                payers.append(InsurancePayer(
                    priority=int(self.safe_get_attr(p, 'priority', '0')),
                    active=self.safe_get_attr(p, 'active', 'true').lower() == 'true',
                    payer_id=self.safe_get_text(p, 'hbill:payerId', ns, field_type='identifier'),
                    payer_name=self.safe_get_text(p, 'hbill:payerName', ns, field_type='name'),
                    payer_type=self.safe_get_text(p, 'hbill:payerType', ns),
                    member_id=self.safe_get_text(p, 'hbill:memberId', ns, field_type='identifier'),
                    group_number=self.safe_get_text(p, 'hbill:groupNumber', ns, field_type='identifier'),
                    plan_name=self.safe_get_text(p, 'hbill:planName', ns, field_type='text'),
                    claim_submission_address=claim_addr,
                    electronic_payer_id=self.safe_get_text(p, 'hbill:electronicPayerId', ns, field_type='identifier')
                ))
            except Exception as e:
                logger.warning(f"Error parsing payer: {e}")
                continue

        # 3. Diagnosis Pointers
        diagnosis_pointers = []
        for d in root.xpath('.//hbill:diagnosisPointer', namespaces=ns) or []:
            try:
                diagnosis_pointers.append(DiagnosisPointer(
                    pointer=self.safe_get_attr(d, 'pointer'),
                    principal=self.safe_get_attr(d, 'principal', 'false').lower() == 'true',
                    icd10_code=self.safe_get_text(d, 'hbill:icd10Code', ns, field_type='code'),
                    description=self.safe_get_text(d, 'hbill:description', ns, field_type='description')
                ))
            except Exception as e:
                logger.warning(f"Error parsing diagnosis pointer: {e}")
                continue

        # 4. Service Lines
        service_lines = []
        for sl in root.xpath('.//hbill:serviceLineItem', namespaces=ns) or []:
            try:
                modifiers = []
                for mod in sl.xpath('hbill:modifiers/hbill:modifier', namespaces=ns) or []:
                    try:
                        modifiers.append(Modifier(
                            code=self.safe_get_text(mod, 'hbill:code', ns, field_type='code'),
                            description=self.safe_get_text(mod, 'hbill:description', ns, field_type='description')
                        ))
                    except Exception as e:
                        logger.warning(f"Error parsing modifier: {e}")
                        continue

                units_str = self.safe_get_text(sl, 'hbill:units', ns, default='0')
                try:
                    units = Decimal(units_str) if units_str else Decimal(0)
                except:
                    units = Decimal(0)

                service_lines.append(ServiceLineItem(
                    line_number=int(self.safe_get_attr(sl, 'lineNumber', '0')),
                    status=self.safe_get_attr(sl, 'status', 'INCLUDED'),
                    cpt_code=self.safe_get_text(sl, 'hbill:cptCode', ns, field_type='code'),
                    cpt_description=self.safe_get_text(sl, 'hbill:cptDescription', ns, field_type='description'),
                    modifiers=modifiers,
                    service_date=parse_date(self.safe_get_text(sl, 'hbill:serviceDate', ns)),
                    service_date_end=parse_date(self.safe_get_text(sl, 'hbill:serviceDateEnd', ns)),
                    place_of_service=self.safe_get_text(sl, 'hbill:placeOfService', ns),
                    units=units,
                    charged_amount=get_monetary(sl, 'hbill:chargedAmount'),
                    allowed_amount=get_monetary(sl, 'hbill:allowedAmount'),
                    paid_amount=get_monetary(sl, 'hbill:paidAmount'),
                    diagnosis_pointers=self.safe_get_text(sl, 'hbill:diagnosisPointers', ns),
                    rendering_provider=self.safe_get_text(sl, 'hbill:renderingProvider', ns, field_type='name'),
                    revenue_code=self.safe_get_text(sl, 'hbill:revenueCode', ns, field_type='code'),
                    denial_reason=self.safe_get_text(sl, 'hbill:denialReason', ns, field_type='description'),
                    notes=self.safe_get_text(sl, 'hbill:notes', ns, field_type='description')
                ))
            except Exception as e:
                logger.warning(f"Error parsing service line: {e}")
                continue

        # 5. Adjustments
        adjustments = []
        for adj in root.xpath('.//hbill:adjustment', namespaces=ns) or []:
            try:
                adjustments.append(Adjustment(
                    adjustment_id=self.safe_get_attr(adj, 'adjustmentId'),
                    reason=self.safe_get_text(adj, 'hbill:reason', ns, field_type='description'),
                    reason_code=self.safe_get_text(adj, 'hbill:reasonCode', ns, field_type='code'),
                    amount=get_monetary(adj, 'hbill:amount'),
                    applied_date=parse_date(self.safe_get_text(adj, 'hbill:appliedDate', ns)),
                    applied_by=self.safe_get_text(adj, 'hbill:appliedBy', ns, field_type='name'),
                    notes=self.safe_get_text(adj, 'hbill:notes', ns, field_type='description')
                ))
            except Exception as e:
                logger.warning(f"Error parsing adjustment: {e}")
                continue

        # 6. Payments
        payments = []
        for pmt in root.xpath('.//hbill:payment', namespaces=ns) or []:
            try:
                payments.append(Payment(
                    payment_id=self.safe_get_attr(pmt, 'paymentId'),
                    posted_by=self.safe_get_attr(pmt, 'postedBy'),
                    posted_at=parse_datetime(self.safe_get_attr(pmt, 'postedAt')),
                    payment_date=parse_date(self.safe_get_text(pmt, 'hbill:paymentDate', ns)),
                    amount=get_monetary(pmt, 'hbill:amount'),
                    payment_method=self.safe_get_text(pmt, 'hbill:paymentMethod', ns),
                    reference_number=self.safe_get_text(pmt, 'hbill:referenceNumber', ns, field_type='identifier'),
                    payer_name=self.safe_get_text(pmt, 'hbill:payerName', ns, field_type='name'),
                    check_number=self.safe_get_text(pmt, 'hbill:checkNumber', ns, field_type='identifier'),
                    era_number=self.safe_get_text(pmt, 'hbill:eraNumber', ns, field_type='identifier'),
                    notes=self.safe_get_text(pmt, 'hbill:notes', ns, field_type='description')
                ))
            except Exception as e:
                logger.warning(f"Error parsing payment: {e}")
                continue

        # 7. Totals
        t = self.safe_get_element(root, 'hbill:totals', ns)
        totals = ClaimTotals(
            total_charged=get_monetary(t, 'hbill:totalCharged') if t else None,
            total_allowed=get_monetary(t, 'hbill:totalAllowed') if t else None,
            total_insurance_paid=get_monetary(t, 'hbill:totalInsurancePaid') if t else None,
            total_adjustments=get_monetary(t, 'hbill:totalAdjustments') if t else None,
            total_patient_responsibility=get_monetary(t, 'hbill:totalPatientResponsibility') if t else None,
            total_patient_paid=get_monetary(t, 'hbill:totalPatientPaid') if t else None,
            balance_due=get_monetary(t, 'hbill:balanceDue') if t else None
        )

        # 8. Appeals
        appeals = []
        for app in root.xpath('.//hbill:appeal', namespaces=ns) or []:
            try:
                appeals.append(Appeal(
                    appeal_id=self.safe_get_attr(app, 'appealId'),
                    appeal_status=self.safe_get_attr(app, 'appealStatus', 'PENDING'),
                    appeal_date=parse_date(self.safe_get_text(app, 'hbill:appealDate', ns)),
                    appeal_reason=self.safe_get_text(app, 'hbill:appealReason', ns, field_type='description'),
                    submitted_by=self.safe_get_text(app, 'hbill:submittedBy', ns, field_type='name'),
                    supporting_docs=self.safe_get_text(app, 'hbill:supportingDocs', ns, field_type='description'),
                    resolution_date=parse_date(self.safe_get_text(app, 'hbill:resolutionDate', ns)),
                    resolution_notes=self.safe_get_text(app, 'hbill:resolutionNotes', ns, field_type='description')
                ))
            except Exception as e:
                logger.warning(f"Error parsing appeal: {e}")
                continue

        return MedicalClaim(
            claim_id=self.safe_get_attr(root, 'claimId'),
            patient_mrn=self.safe_get_attr(root, 'patientMRN'),
            encounter_id=self.safe_get_attr(root, 'encounterId'),
            status=self.safe_get_attr(root, 'status', 'DRAFT'),
            version=int(self.safe_get_attr(root, 'version', '1')),
            electronic_claim=self.safe_get_attr(root, 'electronicClaim', 'true').lower() == 'true',
            claim_type=self.safe_get_text(root, 'hbill:claimType', ns),
            service_start_date=parse_date(self.safe_get_text(root, 'hbill:serviceStartDate', ns)),
            service_end_date=parse_date(self.safe_get_text(root, 'hbill:serviceEndDate', ns)),
            submission_date=parse_date(self.safe_get_text(root, 'hbill:submissionDate', ns)),
            billing_provider=provider,
            payers=payers,
            diagnosis_pointers=diagnosis_pointers,
            service_lines=service_lines,
            adjustments=adjustments,
            payments=payments,
            totals=totals,
            appeals=appeals,
            prior_auth_number=self.safe_get_text(root, 'hbill:priorAuthNumber', ns),
            referral_number=self.safe_get_text(root, 'hbill:referralNumber', ns),
            internal_notes=self.safe_get_text(root, 'hbill:internalNotes', ns, field_type='description')
        )
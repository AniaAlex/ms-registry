"""
XML Generation Functions for ETSI TS 119612 Trust Status Lists

This module provides functions to generate ETSI-compliant XML output
in both standard and go-trust compatible formats.
"""

from xml.dom import minidom
from xml.etree import ElementTree as ET

# =============================================================================
# ETSI TS 119612 Namespace definitions
# =============================================================================
NS_TSL = "http://uri.etsi.org/02231/v2#"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ADDTYPES = "http://uri.etsi.org/02231/v2/additionaltypes#"
NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"
NS_EIDAS_SIG = "http://uri.etsi.org/TrstSvc/SvcInfoExt/eSigDir-1999-93-EC-TrustedList/#"
NS_XADES_141 = "http://uri.etsi.org/01903/v1.4.1#"
NS_XML = "http://www.w3.org/XML/1998/namespace"


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_tsl_xml(scheme) -> str:
    """
    Generate ETSI TS 119612 compliant XML from a TSLScheme instance.

    Args:
        scheme: TSLScheme model instance

    Returns:
        Pretty-printed XML string
    """
    # Namespaces
    NS_TSL = "http://uri.etsi.org/02231/v2#"
    NS_XML = "http://www.w3.org/XML/1998/namespace"
    NS_DS = "http://www.w3.org/2000/09/xmldsig#"

    # Register namespaces
    ET.register_namespace("", NS_TSL)
    ET.register_namespace("xml", NS_XML)
    ET.register_namespace("ds", NS_DS)

    # Create root element
    root = ET.Element(f"{{{NS_TSL}}}TrustServiceStatusList")

    # Scheme Information
    scheme_info = ET.SubElement(root, f"{{{NS_TSL}}}SchemeInformation")

    # TSL Version Identifier
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}TSLVersionIdentifier").text = "5"

    # TSL Sequence Number
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}TSLSequenceNumber").text = str(
        scheme.sequence_number
    )

    # TSL Type
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}TSLType").text = scheme.tsl_type

    # Scheme Operator Name
    operator_name_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}SchemeOperatorName")
    for name in scheme.operator_names.all():
        name_elem = ET.SubElement(operator_name_elem, f"{{{NS_TSL}}}Name")
        name_elem.set(f"{{{NS_XML}}}lang", name.language)
        name_elem.text = name.value

    # Scheme Name
    if scheme.scheme_names.exists():
        scheme_name_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}SchemeName")
        for name in scheme.scheme_names.all():
            name_elem = ET.SubElement(scheme_name_elem, f"{{{NS_TSL}}}Name")
            name_elem.set(f"{{{NS_XML}}}lang", name.language)
            name_elem.text = name.value

    # Scheme Information URI
    if scheme.information_uris.exists():
        uri_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}SchemeInformationURI")
        for uri in scheme.information_uris.all():
            u = ET.SubElement(uri_elem, f"{{{NS_TSL}}}URI")
            u.set(f"{{{NS_XML}}}lang", uri.language)
            u.text = uri.uri

    # Status Determination Approach
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}StatusDeterminationApproach").text = (
        scheme.status_determination_approach
    )

    # Scheme Type/Community Rules
    if scheme.community_rules.exists():
        rules_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}SchemeTypeCommunityRules")
        for rule in scheme.community_rules.all():
            u = ET.SubElement(rules_elem, f"{{{NS_TSL}}}URI")
            u.set(f"{{{NS_XML}}}lang", rule.language)
            u.text = rule.uri

    # Scheme Territory
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}SchemeTerritory").text = scheme.territory

    # Policy or Legal Notice
    if scheme.legal_notices.exists():
        notice_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}PolicyOrLegalNotice")
        for notice in scheme.legal_notices.all():
            n = ET.SubElement(notice_elem, f"{{{NS_TSL}}}TSLLegalNotice")
            n.set(f"{{{NS_XML}}}lang", notice.language)
            n.text = notice.notice

    # Historical Information Period
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}HistoricalInformationPeriod").text = str(
        scheme.historical_information_period
    )

    # Pointers to Other TSL (for LOTL)
    if scheme.pointers.exists():
        pointers_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}PointersToOtherTSL")
        for pointer in scheme.pointers.all():
            ptr_elem = ET.SubElement(pointers_elem, f"{{{NS_TSL}}}OtherTSLPointer")

            # Service Digital Identities (certificates for signature verification)
            if pointer.certificates.exists():
                sdi_elem = ET.SubElement(
                    ptr_elem, f"{{{NS_TSL}}}ServiceDigitalIdentities"
                )
                sdi_inner = ET.SubElement(
                    sdi_elem, f"{{{NS_TSL}}}ServiceDigitalIdentity"
                )
                for cert in pointer.certificates.all():
                    di_elem = ET.SubElement(sdi_inner, f"{{{NS_TSL}}}DigitalId")
                    x509_elem = ET.SubElement(di_elem, f"{{{NS_TSL}}}X509Certificate")
                    x509_elem.text = cert.certificate_data

            ET.SubElement(ptr_elem, f"{{{NS_TSL}}}TSLLocation").text = (
                pointer.tsl_location
            )

            # Additional information
            add_info = ET.SubElement(ptr_elem, f"{{{NS_TSL}}}AdditionalInformation")
            ET.SubElement(add_info, f"{{{NS_TSL}}}TSLType").text = pointer.tsl_type

            # Operator names for pointer
            if pointer.operator_names.exists():
                op_name = ET.SubElement(add_info, f"{{{NS_TSL}}}SchemeOperatorName")
                for name in pointer.operator_names.all():
                    n = ET.SubElement(op_name, f"{{{NS_TSL}}}Name")
                    n.set(f"{{{NS_XML}}}lang", name.language)
                    n.text = name.value

            ET.SubElement(add_info, f"{{{NS_TSL}}}SchemeTerritory").text = (
                pointer.scheme_territory
            )
            ET.SubElement(add_info, f"{{{NS_TSL}}}MimeType").text = pointer.mime_type

    # List Issue Date Time
    ET.SubElement(scheme_info, f"{{{NS_TSL}}}ListIssueDateTime").text = (
        scheme.issue_date.isoformat()
    )

    # Next Update
    if scheme.next_update:
        next_update = ET.SubElement(scheme_info, f"{{{NS_TSL}}}NextUpdate")
        ET.SubElement(next_update, f"{{{NS_TSL}}}dateTime").text = (
            scheme.next_update.isoformat()
        )

    # Distribution Points
    dist_points = scheme.get_distribution_points_list()
    if dist_points:
        dp_elem = ET.SubElement(scheme_info, f"{{{NS_TSL}}}DistributionPoints")
        for dp in dist_points:
            ET.SubElement(dp_elem, f"{{{NS_TSL}}}URI").text = dp

    # Trust Service Provider List
    tsp_list = ET.SubElement(root, f"{{{NS_TSL}}}TrustServiceProviderList")

    for provider in scheme.providers.filter(is_active=True):
        tsp_elem = ET.SubElement(tsp_list, f"{{{NS_TSL}}}TrustServiceProvider")

        # TSP Information
        tsp_info = ET.SubElement(tsp_elem, f"{{{NS_TSL}}}TSPInformation")

        # TSP Name
        tsp_name = ET.SubElement(tsp_info, f"{{{NS_TSL}}}TSPName")
        for name in provider.names.all():
            n = ET.SubElement(tsp_name, f"{{{NS_TSL}}}Name")
            n.set(f"{{{NS_XML}}}lang", name.language)
            n.text = name.value

        # TSP Trade Name
        if provider.trade_names.exists():
            trade_name = ET.SubElement(tsp_info, f"{{{NS_TSL}}}TSPTradeName")
            for name in provider.trade_names.all():
                n = ET.SubElement(trade_name, f"{{{NS_TSL}}}Name")
                n.set(f"{{{NS_XML}}}lang", name.language)
                n.text = name.value

        # TSP Address
        tsp_address = ET.SubElement(tsp_info, f"{{{NS_TSL}}}TSPAddress")

        # Postal Address
        if provider.street_address:
            postal_addresses = ET.SubElement(
                tsp_address, f"{{{NS_TSL}}}PostalAddresses"
            )
            postal = ET.SubElement(postal_addresses, f"{{{NS_TSL}}}PostalAddress")
            postal.set(f"{{{NS_XML}}}lang", "en")

            if provider.street_address:
                ET.SubElement(postal, f"{{{NS_TSL}}}StreetAddress").text = (
                    provider.street_address
                )
            if provider.locality:
                ET.SubElement(postal, f"{{{NS_TSL}}}Locality").text = provider.locality
            if provider.state_or_province:
                ET.SubElement(postal, f"{{{NS_TSL}}}StateOrProvince").text = (
                    provider.state_or_province
                )
            if provider.postal_code:
                ET.SubElement(postal, f"{{{NS_TSL}}}PostalCode").text = (
                    provider.postal_code
                )
            if provider.country_name:
                ET.SubElement(postal, f"{{{NS_TSL}}}CountryName").text = (
                    provider.country_name
                )

        # Electronic Address
        if provider.electronic_addresses.exists():
            electronic = ET.SubElement(tsp_address, f"{{{NS_TSL}}}ElectronicAddress")
            for addr in provider.electronic_addresses.all():
                u = ET.SubElement(electronic, f"{{{NS_TSL}}}URI")
                u.set(f"{{{NS_XML}}}lang", addr.language)
                u.text = addr.uri

        # TSP Information URI
        if provider.information_uris.exists():
            info_uri = ET.SubElement(tsp_info, f"{{{NS_TSL}}}TSPInformationURI")
            for uri in provider.information_uris.all():
                u = ET.SubElement(info_uri, f"{{{NS_TSL}}}URI")
                u.set(f"{{{NS_XML}}}lang", uri.language)
                u.text = uri.uri

        # TSP Services
        tsp_services = ET.SubElement(tsp_elem, f"{{{NS_TSL}}}TSPServices")

        for service in provider.services.filter(is_active=True):
            svc_elem = ET.SubElement(tsp_services, f"{{{NS_TSL}}}TSPService")
            svc_info = ET.SubElement(svc_elem, f"{{{NS_TSL}}}ServiceInformation")

            # Service Type Identifier
            ET.SubElement(svc_info, f"{{{NS_TSL}}}ServiceTypeIdentifier").text = (
                service.service_type
            )

            # Service Name
            svc_name = ET.SubElement(svc_info, f"{{{NS_TSL}}}ServiceName")
            for name in service.names.all():
                n = ET.SubElement(svc_name, f"{{{NS_TSL}}}Name")
                n.set(f"{{{NS_XML}}}lang", name.language)
                n.text = name.value

            # Service Digital Identity (Certificates)
            if service.certificates.exists():
                sdi = ET.SubElement(svc_info, f"{{{NS_TSL}}}ServiceDigitalIdentity")
                for cert in service.certificates.all():
                    di = ET.SubElement(sdi, f"{{{NS_TSL}}}DigitalId")
                    x509 = ET.SubElement(di, f"{{{NS_TSL}}}X509Certificate")
                    x509.text = cert.get_base64_der()

            # Service Status
            ET.SubElement(svc_info, f"{{{NS_TSL}}}ServiceStatus").text = service.status

            # Status Starting Time
            ET.SubElement(svc_info, f"{{{NS_TSL}}}StatusStartingTime").text = (
                service.status_starting_time.isoformat()
            )

            # Service Supply Points
            if service.supply_points.exists():
                ssp = ET.SubElement(svc_info, f"{{{NS_TSL}}}ServiceSupplyPoints")
                for sp in service.supply_points.all():
                    ET.SubElement(ssp, f"{{{NS_TSL}}}ServiceSupplyPoint").text = sp.uri

            # Service Definition URI
            if service.definition_uris.exists():
                sdu = ET.SubElement(svc_info, f"{{{NS_TSL}}}TSPServiceDefinitionURI")
                for uri in service.definition_uris.all():
                    u = ET.SubElement(sdu, f"{{{NS_TSL}}}URI")
                    u.set(f"{{{NS_XML}}}lang", uri.language)
                    u.text = uri.uri

            # Service History
            if service.history.exists():
                history_elem = ET.SubElement(svc_elem, f"{{{NS_TSL}}}ServiceHistory")
                for hist in service.history.all():
                    hist_instance = ET.SubElement(
                        history_elem, f"{{{NS_TSL}}}ServiceHistoryInstance"
                    )

                    ET.SubElement(
                        hist_instance, f"{{{NS_TSL}}}ServiceTypeIdentifier"
                    ).text = hist.service_type

                    hist_name = ET.SubElement(hist_instance, f"{{{NS_TSL}}}ServiceName")
                    for name in hist.names.all():
                        n = ET.SubElement(hist_name, f"{{{NS_TSL}}}Name")
                        n.set(f"{{{NS_XML}}}lang", name.language)
                        n.text = name.value

                    ET.SubElement(hist_instance, f"{{{NS_TSL}}}ServiceStatus").text = (
                        hist.status
                    )
                    ET.SubElement(
                        hist_instance, f"{{{NS_TSL}}}StatusStartingTime"
                    ).text = hist.status_starting_time.isoformat()

    # Convert to string with pretty printing
    xml_string = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(xml_string)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + dom.toprettyxml(indent="  ")[dom.toprettyxml().find("\n") + 1 :]
    )


def generate_tsl_xml_gotrust_format(scheme) -> str:
    """
    Generate ETSI TS 119612 XML in the same format as go-trust.

    This function produces XML with tsl: namespace prefix, matching the output
    format of go-trust's PublishTSL step (pkg/pipeline/step_publish.go).

    Args:
        scheme: TSLScheme model instance

    Returns:
        XML string with tsl: namespace prefix (go-trust compatible)
    """
    NS_TSL = "http://uri.etsi.org/02231/v2#"

    # Build XML manually for go-trust format with tsl: prefix
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(f'<tsl:TrustServiceStatusList xmlns:tsl="{NS_TSL}">')

    # Scheme Information
    lines.append("  <tsl:SchemeInformation>")
    lines.append("    <tsl:TSLVersionIdentifier>5</tsl:TSLVersionIdentifier>")
    lines.append(
        f"    <tsl:TSLSequenceNumber>{scheme.sequence_number}</tsl:TSLSequenceNumber>"
    )
    lines.append(f"    <tsl:TSLType>{scheme.tsl_type}</tsl:TSLType>")

    # Scheme Operator Name
    lines.append("    <tsl:SchemeOperatorName>")
    for name in scheme.operator_names.all():
        lines.append(
            f'      <tsl:Name xml:lang="{name.language}">'
            f"{_escape_xml(name.value)}</tsl:Name>"
        )
    lines.append("    </tsl:SchemeOperatorName>")

    # Scheme Name (optional)
    if scheme.scheme_names.exists():
        lines.append("    <tsl:SchemeName>")
        for name in scheme.scheme_names.all():
            lines.append(
                f'      <tsl:Name xml:lang="{name.language}">'
                f"{_escape_xml(name.value)}</tsl:Name>"
            )
        lines.append("    </tsl:SchemeName>")

    # Scheme Information URI (optional)
    if scheme.information_uris.exists():
        lines.append("    <tsl:SchemeInformationURI>")
        for uri in scheme.information_uris.all():
            lines.append(
                f'      <tsl:URI xml:lang="{uri.language}">'
                f"{_escape_xml(uri.uri)}</tsl:URI>"
            )
        lines.append("    </tsl:SchemeInformationURI>")

    # Status Determination Approach
    lines.append(
        f"    <tsl:StatusDeterminationApproach>"
        f"{scheme.status_determination_approach}</tsl:StatusDeterminationApproach>"
    )

    # Scheme Type/Community Rules (optional)
    if scheme.community_rules.exists():
        lines.append("    <tsl:SchemeTypeCommunityRules>")
        for rule in scheme.community_rules.all():
            lines.append(
                f'      <tsl:URI xml:lang="{rule.language}">'
                f"{_escape_xml(rule.uri)}</tsl:URI>"
            )
        lines.append("    </tsl:SchemeTypeCommunityRules>")

    # Scheme Territory
    lines.append(f"    <tsl:SchemeTerritory>{scheme.territory}</tsl:SchemeTerritory>")

    # Policy or Legal Notice (optional)
    if scheme.legal_notices.exists():
        lines.append("    <tsl:PolicyOrLegalNotice>")
        for notice in scheme.legal_notices.all():
            lines.append(
                f'      <tsl:TSLLegalNotice xml:lang="{notice.language}">'
                f"{_escape_xml(notice.notice)}</tsl:TSLLegalNotice>"
            )
        lines.append("    </tsl:PolicyOrLegalNotice>")

    # Historical Information Period
    lines.append(
        f"    <tsl:HistoricalInformationPeriod>"
        f"{scheme.historical_information_period}</tsl:HistoricalInformationPeriod>"
    )

    # Pointers to Other TSL (for LOTL)
    if scheme.pointers.exists():
        lines.append("    <tsl:PointersToOtherTSL>")
        for pointer in scheme.pointers.all():
            lines.append("      <tsl:OtherTSLPointer>")

            # Service Digital Identities
            if pointer.certificates.exists():
                lines.append("        <tsl:ServiceDigitalIdentities>")
                lines.append("          <tsl:ServiceDigitalIdentity>")
                for cert in pointer.certificates.all():
                    lines.append("            <tsl:DigitalId>")
                    lines.append(
                        f"              <tsl:X509Certificate>"
                        f"{cert.certificate_data}</tsl:X509Certificate>"
                    )
                    lines.append("            </tsl:DigitalId>")
                lines.append("          </tsl:ServiceDigitalIdentity>")
                lines.append("        </tsl:ServiceDigitalIdentities>")

            lines.append(
                f"        <tsl:TSLLocation>"
                f"{_escape_xml(pointer.tsl_location)}</tsl:TSLLocation>"
            )

            lines.append("        <tsl:AdditionalInformation>")
            lines.append(f"          <tsl:TSLType>{pointer.tsl_type}</tsl:TSLType>")
            if pointer.operator_names.exists():
                lines.append("          <tsl:SchemeOperatorName>")
                for name in pointer.operator_names.all():
                    lines.append(
                        f'            <tsl:Name xml:lang="{name.language}">'
                        f"{_escape_xml(name.value)}</tsl:Name>"
                    )
                lines.append("          </tsl:SchemeOperatorName>")
            lines.append(
                f"          <tsl:SchemeTerritory>"
                f"{pointer.scheme_territory}</tsl:SchemeTerritory>"
            )
            lines.append(f"          <tsl:MimeType>{pointer.mime_type}</tsl:MimeType>")
            lines.append("        </tsl:AdditionalInformation>")

            lines.append("      </tsl:OtherTSLPointer>")
        lines.append("    </tsl:PointersToOtherTSL>")

    # List Issue Date Time
    issue_date_str = scheme.issue_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"    <tsl:ListIssueDateTime>{issue_date_str}</tsl:ListIssueDateTime>")

    # Next Update (optional)
    if scheme.next_update:
        lines.append("    <tsl:NextUpdate>")
        next_update_str = scheme.next_update.strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"      <tsl:dateTime>{next_update_str}</tsl:dateTime>")
        lines.append("    </tsl:NextUpdate>")

    # Distribution Points (optional)
    dist_points = scheme.get_distribution_points_list()
    if dist_points:
        lines.append("    <tsl:DistributionPoints>")
        for dp in dist_points:
            lines.append(f"      <tsl:URI>{_escape_xml(dp)}</tsl:URI>")
        lines.append("    </tsl:DistributionPoints>")

    lines.append("  </tsl:SchemeInformation>")

    # Trust Service Provider List
    lines.append("  <tsl:TrustServiceProviderList>")

    for provider in scheme.providers.filter(is_active=True):
        lines.append("    <tsl:TrustServiceProvider>")
        lines.append("      <tsl:TSPInformation>")

        # TSP Name
        lines.append("        <tsl:TSPName>")
        for name in provider.names.all():
            lines.append(
                f'          <tsl:Name xml:lang="{name.language}">'
                f"{_escape_xml(name.value)}</tsl:Name>"
            )
        lines.append("        </tsl:TSPName>")

        # TSP Trade Name (optional)
        if provider.trade_names.exists():
            lines.append("        <tsl:TSPTradeName>")
            for name in provider.trade_names.all():
                lines.append(
                    f'          <tsl:Name xml:lang="{name.language}">'
                    f"{_escape_xml(name.value)}</tsl:Name>"
                )
            lines.append("        </tsl:TSPTradeName>")

        # TSP Address
        if provider.street_address or provider.electronic_addresses.exists():
            lines.append("        <tsl:TSPAddress>")

            # Postal Address
            if provider.street_address:
                lines.append("          <tsl:PostalAddresses>")
                lines.append('            <tsl:PostalAddress xml:lang="en">')
                if provider.street_address:
                    lines.append(
                        f"              <tsl:StreetAddress>"
                        f"{_escape_xml(provider.street_address)}</tsl:StreetAddress>"
                    )
                if provider.locality:
                    lines.append(
                        f"              <tsl:Locality>"
                        f"{_escape_xml(provider.locality)}</tsl:Locality>"
                    )
                if provider.state_or_province:
                    lines.append(
                        f"              <tsl:StateOrProvince>"
                        f"{_escape_xml(provider.state_or_province)}"
                        f"</tsl:StateOrProvince>"
                    )
                if provider.postal_code:
                    lines.append(
                        f"              <tsl:PostalCode>"
                        f"{_escape_xml(provider.postal_code)}</tsl:PostalCode>"
                    )
                if provider.country_name:
                    lines.append(
                        f"              <tsl:CountryName>"
                        f"{_escape_xml(provider.country_name)}</tsl:CountryName>"
                    )
                lines.append("            </tsl:PostalAddress>")
                lines.append("          </tsl:PostalAddresses>")

            # Electronic Address
            if provider.electronic_addresses.exists():
                lines.append("          <tsl:ElectronicAddress>")
                for addr in provider.electronic_addresses.all():
                    lines.append(
                        f'            <tsl:URI xml:lang="{addr.language}">'
                        f"{_escape_xml(addr.uri)}</tsl:URI>"
                    )
                lines.append("          </tsl:ElectronicAddress>")

            lines.append("        </tsl:TSPAddress>")

        # TSP Information URI (optional)
        if provider.information_uris.exists():
            lines.append("        <tsl:TSPInformationURI>")
            for uri in provider.information_uris.all():
                lines.append(
                    f'          <tsl:URI xml:lang="{uri.language}">'
                    f"{_escape_xml(uri.uri)}</tsl:URI>"
                )
            lines.append("        </tsl:TSPInformationURI>")

        lines.append("      </tsl:TSPInformation>")

        # TSP Services
        lines.append("      <tsl:TSPServices>")

        for service in provider.services.filter(is_active=True):
            lines.append("        <tsl:TSPService>")
            lines.append("          <tsl:ServiceInformation>")

            # Service Type Identifier
            lines.append(
                f"            <tsl:ServiceTypeIdentifier>"
                f"{service.service_type}</tsl:ServiceTypeIdentifier>"
            )

            # Service Name
            lines.append("            <tsl:ServiceName>")
            for name in service.names.all():
                lines.append(
                    f'              <tsl:Name xml:lang="{name.language}">'
                    f"{_escape_xml(name.value)}</tsl:Name>"
                )
            lines.append("            </tsl:ServiceName>")

            # Service Status
            lines.append(
                f"            <tsl:ServiceStatus>{service.status}</tsl:ServiceStatus>"
            )

            # Status Starting Time
            status_time = service.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            lines.append(
                f"            <tsl:StatusStartingTime>{status_time}"
                f"</tsl:StatusStartingTime>"
            )

            # Service Digital Identity (Certificates)
            if service.certificates.exists():
                lines.append("            <tsl:ServiceDigitalIdentity>")
                for cert in service.certificates.all():
                    lines.append("              <tsl:DigitalId>")
                    lines.append(
                        f"                <tsl:X509Certificate>"
                        f"{cert.get_base64_der()}</tsl:X509Certificate>"
                    )
                    lines.append("              </tsl:DigitalId>")
                lines.append("            </tsl:ServiceDigitalIdentity>")

            # Service Supply Points (optional)
            if service.supply_points.exists():
                lines.append("            <tsl:ServiceSupplyPoints>")
                for sp in service.supply_points.all():
                    lines.append(
                        f"              <tsl:ServiceSupplyPoint>"
                        f"{_escape_xml(sp.uri)}</tsl:ServiceSupplyPoint>"
                    )
                lines.append("            </tsl:ServiceSupplyPoints>")

            # Service Definition URI (optional)
            if service.definition_uris.exists():
                lines.append("            <tsl:TSPServiceDefinitionURI>")
                for uri in service.definition_uris.all():
                    lines.append(
                        f'              <tsl:URI xml:lang="{uri.language}">'
                        f"{_escape_xml(uri.uri)}</tsl:URI>"
                    )
                lines.append("            </tsl:TSPServiceDefinitionURI>")

            lines.append("          </tsl:ServiceInformation>")

            # Service History (optional)
            if service.history.exists():
                lines.append("          <tsl:ServiceHistory>")
                for hist in service.history.all():
                    lines.append("            <tsl:ServiceHistoryInstance>")
                    lines.append(
                        f"              <tsl:ServiceTypeIdentifier>"
                        f"{hist.service_type}</tsl:ServiceTypeIdentifier>"
                    )
                    lines.append("              <tsl:ServiceName>")
                    for name in hist.names.all():
                        lines.append(
                            f'                <tsl:Name xml:lang="{name.language}">'
                            f"{_escape_xml(name.value)}</tsl:Name>"
                        )
                    lines.append("              </tsl:ServiceName>")
                    lines.append(
                        f"              <tsl:ServiceStatus>{hist.status}"
                        f"</tsl:ServiceStatus>"
                    )
                    hist_time = hist.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    lines.append(
                        f"              <tsl:StatusStartingTime>{hist_time}"
                        f"</tsl:StatusStartingTime>"
                    )
                    lines.append("            </tsl:ServiceHistoryInstance>")
                lines.append("          </tsl:ServiceHistory>")

            lines.append("        </tsl:TSPService>")

        lines.append("      </tsl:TSPServices>")
        lines.append("    </tsl:TrustServiceProvider>")

    lines.append("  </tsl:TrustServiceProviderList>")
    lines.append("</tsl:TrustServiceStatusList>")

    return "\n".join(lines)


def export_tsl_to_file(scheme, filepath: str, use_gotrust_format: bool = True) -> str:
    """
    Export a TSL scheme to an XML file.

    This mirrors go-trust's PublishTSL step functionality.

    Args:
        scheme: TSLScheme model instance
        filepath: Output file path
        use_gotrust_format: If True, use go-trust compatible format (tsl: prefix)

    Returns:
        The filepath where the XML was written
    """
    if use_gotrust_format:
        xml_content = generate_tsl_xml_gotrust_format(scheme)
    else:
        xml_content = generate_tsl_xml(scheme)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return filepath


def export_tsl_with_filename(
    scheme, output_dir: str, use_gotrust_format: bool = True
) -> str:
    """
    Export a TSL scheme to a file with auto-generated filename.

    The filename is generated based on territory and sequence number,
    similar to go-trust's default naming convention.

    Args:
        scheme: TSLScheme model instance
        output_dir: Output directory path
        use_gotrust_format: If True, use go-trust compatible format

    Returns:
        The filepath where the XML was written
    """
    import os

    # Generate filename similar to go-trust
    filename = f"{scheme.territory}-TSL-{scheme.sequence_number}.xml"
    filepath = os.path.join(output_dir, filename)

    return export_tsl_to_file(scheme, filepath, use_gotrust_format)


def export_multiple_tsls(
    schemes, output_dir: str, use_gotrust_format: bool = True
) -> list:
    """
    Export multiple TSL schemes to XML files.

    Args:
        schemes: QuerySet or list of TSLScheme instances
        output_dir: Output directory path
        use_gotrust_format: If True, use go-trust compatible format

    Returns:
        List of filepaths where XMLs were written
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    filepaths = []
    for scheme in schemes:
        filepath = export_tsl_with_filename(scheme, output_dir, use_gotrust_format)
        filepaths.append(filepath)

    return filepaths


def generate_tsl_xml_etsi_format(scheme) -> str:
    """
    Generate ETSI TS 119612 compliant XML in the exact format used by EU Trust Lists.

    This function produces XML with all required ETSI namespaces, matching the format
    of official EU member state Trust Status Lists (like Sweden's PTS TSL).

    Args:
        scheme: TSLScheme model instance

    Returns:
        Complete ETSI TS 119612 compliant XML string
    """
    lines = []

    # XML declaration
    lines.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')

    # Root element with all ETSI namespaces
    lines.append(
        "<TrustServiceStatusList "
        f'xmlns="{NS_TSL}" '
        f'xmlns:ns2="{NS_DS}" '
        f'xmlns:ns3="{NS_ADDTYPES}" '
        f'xmlns:ns4="{NS_XADES}" '
        f'xmlns:ns5="{NS_EIDAS_SIG}" '
        f'xmlns:ns6="{NS_XADES_141}" '
        'Id="id_for_enveloped_signing_of_the_entire_list" '
        'TSLTag="http://uri.etsi.org/19612/TSLTag">'
    )

    # SchemeInformation section
    lines.append("    <SchemeInformation>")

    # TSL Version Identifier (always 5 for current ETSI spec)
    lines.append("        <TSLVersionIdentifier>5</TSLVersionIdentifier>")

    # TSL Sequence Number
    lines.append(
        f"        <TSLSequenceNumber>{scheme.sequence_number}</TSLSequenceNumber>"
    )

    # TSL Type
    lines.append(f"        <TSLType>{_escape_xml(scheme.tsl_type)}</TSLType>")

    # Scheme Operator Name
    lines.append("        <SchemeOperatorName>")
    for name in scheme.operator_names.all():
        lines.append(
            f'            <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
        )
    lines.append("        </SchemeOperatorName>")

    # Scheme Operator Address
    lines.append("        <SchemeOperatorAddress>")

    # Postal Addresses - Get from first provider or use scheme territory defaults
    lines.append("            <PostalAddresses>")
    lines.append('                <PostalAddress xml:lang="en">')

    # Try to get address from the scheme's first provider, or use defaults
    first_provider = scheme.providers.first()
    if first_provider and first_provider.street_address:
        lines.append(
            f"                    <StreetAddress>{_escape_xml(first_provider.street_address)}</StreetAddress>"
        )
        if first_provider.locality:
            lines.append(
                f"                    <Locality>{_escape_xml(first_provider.locality)}</Locality>"
            )
        if first_provider.postal_code:
            lines.append(
                f"                    <PostalCode>{_escape_xml(first_provider.postal_code)}</PostalCode>"
            )
        lines.append(
            f"                    <CountryName>{scheme.territory}</CountryName>"
        )
    else:
        lines.append(f"                    <StreetAddress></StreetAddress>")
        lines.append(f"                    <Locality></Locality>")
        lines.append(f"                    <PostalCode></PostalCode>")
        lines.append(
            f"                    <CountryName>{scheme.territory}</CountryName>"
        )

    lines.append("                </PostalAddress>")
    lines.append("            </PostalAddresses>")

    # Electronic Address
    lines.append("            <ElectronicAddress>")
    for uri in scheme.information_uris.all():
        lines.append(
            f'                <URI xml:lang="{uri.language}">{_escape_xml(uri.uri)}</URI>'
        )
    lines.append("            </ElectronicAddress>")
    lines.append("        </SchemeOperatorAddress>")

    # Scheme Name
    if scheme.scheme_names.exists():
        lines.append("        <SchemeName>")
        for name in scheme.scheme_names.all():
            lines.append(
                f'            <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
            )
        lines.append("        </SchemeName>")

    # Scheme Information URI
    if scheme.information_uris.exists():
        lines.append("        <SchemeInformationURI>")
        for uri in scheme.information_uris.all():
            lines.append(
                f'            <URI xml:lang="{uri.language}">{_escape_xml(uri.uri)}</URI>'
            )
        lines.append("        </SchemeInformationURI>")

    # Status Determination Approach
    lines.append(
        f"        <StatusDeterminationApproach>{_escape_xml(scheme.status_determination_approach)}</StatusDeterminationApproach>"
    )

    # Scheme Type Community Rules
    if scheme.community_rules.exists():
        lines.append("        <SchemeTypeCommunityRules>")
        for rule in scheme.community_rules.all():
            lines.append(
                f'            <URI xml:lang="{rule.language}">{_escape_xml(rule.uri)}</URI>'
            )
        lines.append("        </SchemeTypeCommunityRules>")

    # Scheme Territory
    lines.append(f"        <SchemeTerritory>{scheme.territory}</SchemeTerritory>")

    # Policy or Legal Notice
    if scheme.legal_notices.exists():
        lines.append("        <PolicyOrLegalNotice>")
        for notice in scheme.legal_notices.all():
            lines.append(
                f'            <TSLLegalNotice xml:lang="{notice.language}">{_escape_xml(notice.notice)}</TSLLegalNotice>'
            )
        lines.append("        </PolicyOrLegalNotice>")

    # Historical Information Period
    lines.append(
        f"        <HistoricalInformationPeriod>{scheme.historical_information_period}</HistoricalInformationPeriod>"
    )

    # Pointers to Other TSL (for LOTL)
    if scheme.pointers.exists():
        lines.append("        <PointersToOtherTSL>")
        for pointer in scheme.pointers.all():
            lines.append("            <OtherTSLPointer>")

            # Service Digital Identities (certificates for signature verification)
            if pointer.certificates.exists():
                lines.append("                <ServiceDigitalIdentities>")
                for cert in pointer.certificates.all():
                    lines.append("                    <ServiceDigitalIdentity>")
                    lines.append("                        <DigitalId>")
                    lines.append(
                        f"                            <X509Certificate>{cert.certificate_data}</X509Certificate>"
                    )
                    lines.append("                        </DigitalId>")
                    lines.append("                    </ServiceDigitalIdentity>")
                lines.append("                </ServiceDigitalIdentities>")

            lines.append(
                f"                <TSLLocation>{_escape_xml(pointer.tsl_location)}</TSLLocation>"
            )

            # Additional Information
            lines.append("                <AdditionalInformation>")
            lines.append("                    <OtherInformation>")
            lines.append(
                f"                        <TSLType>{pointer.tsl_type}</TSLType>"
            )
            lines.append("                    </OtherInformation>")
            lines.append("                    <OtherInformation>")
            lines.append(
                f"                        <SchemeTerritory>{pointer.scheme_territory}</SchemeTerritory>"
            )
            lines.append("                    </OtherInformation>")
            lines.append("                    <OtherInformation>")
            lines.append(
                f"                        <ns3:MimeType>{pointer.mime_type}</ns3:MimeType>"
            )
            lines.append("                    </OtherInformation>")
            if pointer.operator_names.exists():
                lines.append("                    <OtherInformation>")
                lines.append("                        <SchemeOperatorName>")
                for name in pointer.operator_names.all():
                    lines.append(
                        f'                            <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
                    )
                lines.append("                        </SchemeOperatorName>")
                lines.append("                    </OtherInformation>")
            lines.append("                </AdditionalInformation>")

            lines.append("            </OtherTSLPointer>")
        lines.append("        </PointersToOtherTSL>")

    # List Issue Date Time
    issue_date_str = scheme.issue_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"        <ListIssueDateTime>{issue_date_str}</ListIssueDateTime>")

    # Next Update
    if scheme.next_update:
        lines.append("        <NextUpdate>")
        next_update_str = scheme.next_update.strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"            <dateTime>{next_update_str}</dateTime>")
        lines.append("        </NextUpdate>")

    # Distribution Points
    dist_points = scheme.get_distribution_points_list()
    if dist_points:
        lines.append("        <DistributionPoints>")
        for dp in dist_points:
            lines.append(f"            <URI>{_escape_xml(dp)}</URI>")
        lines.append("        </DistributionPoints>")

    lines.append("    </SchemeInformation>")

    # Trust Service Provider List
    lines.append("    <TrustServiceProviderList>")

    for provider in scheme.providers.filter(is_active=True):
        lines.append("        <TrustServiceProvider>")

        # TSP Information
        lines.append("            <TSPInformation>")

        # TSP Name
        lines.append("                <TSPName>")
        for name in provider.names.all():
            lines.append(
                f'                    <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
            )
        lines.append("                </TSPName>")

        # TSP Trade Name
        if provider.trade_names.exists():
            lines.append("                <TSPTradeName>")
            for name in provider.trade_names.all():
                lines.append(
                    f'                    <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
                )
            lines.append("                </TSPTradeName>")

        # TSP Address
        lines.append("                <TSPAddress>")

        # Postal Addresses
        if provider.street_address:
            lines.append("                    <PostalAddresses>")
            lines.append('                        <PostalAddress xml:lang="en">')
            lines.append(
                f"                            <StreetAddress>{_escape_xml(provider.street_address)}</StreetAddress>"
            )
            if provider.locality:
                lines.append(
                    f"                            <Locality>{_escape_xml(provider.locality)}</Locality>"
                )
            if provider.state_or_province:
                lines.append(
                    f"                            <StateOrProvince>{_escape_xml(provider.state_or_province)}</StateOrProvince>"
                )
            if provider.postal_code:
                lines.append(
                    f"                            <PostalCode>{_escape_xml(provider.postal_code)}</PostalCode>"
                )
            lines.append(
                f"                            <CountryName>{_escape_xml(provider.country_name)}</CountryName>"
            )
            lines.append("                        </PostalAddress>")
            lines.append("                    </PostalAddresses>")

        # Electronic Address
        if provider.electronic_addresses.exists():
            lines.append("                    <ElectronicAddress>")
            for addr in provider.electronic_addresses.all():
                lines.append(
                    f'                        <URI xml:lang="{addr.language}">{_escape_xml(addr.uri)}</URI>'
                )
            lines.append("                    </ElectronicAddress>")

        lines.append("                </TSPAddress>")

        # TSP Information URI
        if provider.information_uris.exists():
            lines.append("                <TSPInformationURI>")
            for uri in provider.information_uris.all():
                lines.append(
                    f'                    <URI xml:lang="{uri.language}">{_escape_xml(uri.uri)}</URI>'
                )
            lines.append("                </TSPInformationURI>")

        lines.append("            </TSPInformation>")

        # TSP Services
        lines.append("            <TSPServices>")

        for service in provider.services.filter(is_active=True):
            lines.append("                <TSPService>")
            lines.append("                    <ServiceInformation>")

            # Service Type Identifier
            lines.append(
                f"                        <ServiceTypeIdentifier>{service.service_type}</ServiceTypeIdentifier>"
            )

            # Service Name
            lines.append("                        <ServiceName>")
            for name in service.names.all():
                lines.append(
                    f'                            <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
                )
            lines.append("                        </ServiceName>")

            # Service Digital Identity (Certificates)
            if service.certificates.exists():
                lines.append("                        <ServiceDigitalIdentity>")
                for cert in service.certificates.all():
                    # Output X509Certificate
                    lines.append("                            <DigitalId>")
                    lines.append(
                        f"                                <X509Certificate>{cert.get_base64_der()}</X509Certificate>"
                    )
                    lines.append("                            </DigitalId>")
                    # Output X509SubjectName if available
                    if cert.x509_subject_name:
                        lines.append("                            <DigitalId>")
                        lines.append(
                            f"                                <X509SubjectName>{_escape_xml(cert.x509_subject_name)}</X509SubjectName>"
                        )
                        lines.append("                            </DigitalId>")
                    # Output X509SKI if available
                    if cert.x509_ski:
                        lines.append("                            <DigitalId>")
                        lines.append(
                            f"                                <X509SKI>{cert.x509_ski}</X509SKI>"
                        )
                        lines.append("                            </DigitalId>")
                lines.append("                        </ServiceDigitalIdentity>")

            # Service Status
            lines.append(
                f"                        <ServiceStatus>{service.status}</ServiceStatus>"
            )

            # Status Starting Time
            status_time = service.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            lines.append(
                f"                        <StatusStartingTime>{status_time}</StatusStartingTime>"
            )

            # Service Information Extensions (if any qualifications or additional info exist)
            has_extensions = (
                hasattr(service, "qualifications") and service.qualifications.exists()
            ) or (
                hasattr(service, "additional_service_info")
                and service.additional_service_info.exists()
            )

            if (
                has_extensions
                or service.supply_points.exists()
                or service.definition_uris.exists()
            ):
                lines.append("                        <ServiceInformationExtensions>")

                # Qualifications extension
                if (
                    hasattr(service, "qualifications")
                    and service.qualifications.exists()
                ):
                    lines.append(
                        '                            <Extension Critical="true">'
                    )
                    lines.append("                                <ns5:Qualifications>")
                    for qual in service.qualifications.all():
                        lines.append(
                            "                                    <ns5:QualificationElement>"
                        )
                        lines.append(
                            "                                        <ns5:Qualifiers>"
                        )
                        lines.append(
                            f'                                            <ns5:Qualifier uri="{_escape_xml(qual.qualifier_uri)}"/>'
                        )
                        lines.append(
                            "                                        </ns5:Qualifiers>"
                        )
                        lines.append(
                            f'                                        <ns5:CriteriaList assert="{qual.criteria_assert}">'
                        )
                        # Add key usage bits if specified
                        if qual.key_usage:
                            lines.append(
                                "                                            <ns5:KeyUsage>"
                            )
                            for ku_name, ku_value in [
                                ("digitalSignature", qual.key_usage_digital_signature),
                                ("nonRepudiation", qual.key_usage_non_repudiation),
                                ("keyEncipherment", qual.key_usage_key_encipherment),
                                ("dataEncipherment", qual.key_usage_data_encipherment),
                                ("keyAgreement", qual.key_usage_key_agreement),
                                ("keyCertSign", qual.key_usage_key_cert_sign),
                                ("crlSign", qual.key_usage_crl_sign),
                                ("encipherOnly", qual.key_usage_encipher_only),
                                ("decipherOnly", qual.key_usage_decipher_only),
                            ]:
                                lines.append(
                                    f'                                                <ns5:KeyUsageBit name="{ku_name}">{str(ku_value).lower()}</ns5:KeyUsageBit>'
                                )
                            lines.append(
                                "                                            </ns5:KeyUsage>"
                            )
                        lines.append(
                            "                                        </ns5:CriteriaList>"
                        )
                        lines.append(
                            "                                    </ns5:QualificationElement>"
                        )
                    lines.append(
                        "                                </ns5:Qualifications>"
                    )
                    lines.append("                            </Extension>")

                # Additional Service Information extension
                if (
                    hasattr(service, "additional_service_info")
                    and service.additional_service_info.exists()
                ):
                    for info in service.additional_service_info.all():
                        critical = "true" if info.critical else "false"
                        lines.append(
                            f'                            <Extension Critical="{critical}">'
                        )
                        lines.append(
                            "                                <AdditionalServiceInformation>"
                        )
                        lines.append(
                            f'                                    <URI xml:lang="{info.language}">{_escape_xml(info.uri)}</URI>'
                        )
                        lines.append(
                            "                                </AdditionalServiceInformation>"
                        )
                        lines.append("                            </Extension>")

                lines.append("                        </ServiceInformationExtensions>")

            lines.append("                    </ServiceInformation>")

            # Service History
            if service.history.exists():
                lines.append("                    <ServiceHistory>")
                for hist in service.history.all().order_by("-status_starting_time"):
                    lines.append("                        <ServiceHistoryInstance>")
                    lines.append(
                        f"                            <ServiceTypeIdentifier>{hist.service_type}</ServiceTypeIdentifier>"
                    )
                    lines.append("                            <ServiceName>")
                    for name in hist.names.all():
                        lines.append(
                            f'                                <Name xml:lang="{name.language}">{_escape_xml(name.value)}</Name>'
                        )
                    lines.append("                            </ServiceName>")

                    # History Digital Identity (X509SubjectName and X509SKI)
                    if hasattr(hist, "digital_ids") and hist.digital_ids.exists():
                        lines.append(
                            "                            <ServiceDigitalIdentity>"
                        )
                        for digital_id in hist.digital_ids.all():
                            lines.append("                                <DigitalId>")
                            if digital_id.x509_subject_name:
                                lines.append(
                                    f"                                    <X509SubjectName>{_escape_xml(digital_id.x509_subject_name)}</X509SubjectName>"
                                )
                            lines.append("                                </DigitalId>")
                            if digital_id.x509_ski:
                                lines.append(
                                    "                                <DigitalId>"
                                )
                                lines.append(
                                    f"                                    <X509SKI>{digital_id.x509_ski}</X509SKI>"
                                )
                                lines.append(
                                    "                                </DigitalId>"
                                )
                        lines.append(
                            "                            </ServiceDigitalIdentity>"
                        )

                    lines.append(
                        f"                            <ServiceStatus>{hist.status}</ServiceStatus>"
                    )
                    hist_time = hist.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    lines.append(
                        f"                            <StatusStartingTime>{hist_time}</StatusStartingTime>"
                    )

                    # History Service Information Extensions
                    has_hist_extensions = (
                        hasattr(hist, "qualifications") and hist.qualifications.exists()
                    ) or (
                        hasattr(hist, "additional_info")
                        and hist.additional_info.exists()
                    )

                    if has_hist_extensions:
                        lines.append(
                            "                            <ServiceInformationExtensions>"
                        )

                        # History Qualifications
                        if (
                            hasattr(hist, "qualifications")
                            and hist.qualifications.exists()
                        ):
                            lines.append(
                                '                                <Extension Critical="true">'
                            )
                            lines.append(
                                "                                    <ns5:Qualifications>"
                            )
                            for qual in hist.qualifications.all():
                                lines.append(
                                    "                                        <ns5:QualificationElement>"
                                )
                                lines.append(
                                    "                                            <ns5:Qualifiers>"
                                )
                                lines.append(
                                    f'                                                <ns5:Qualifier uri="{_escape_xml(qual.qualifier_uri)}"/>'
                                )
                                lines.append(
                                    "                                            </ns5:Qualifiers>"
                                )
                                lines.append(
                                    f'                                            <ns5:CriteriaList assert="{qual.criteria_assert}">'
                                )
                                if qual.key_usage:
                                    lines.append(
                                        "                                                <ns5:KeyUsage>"
                                    )
                                    for ku_name, ku_value in [
                                        (
                                            "digitalSignature",
                                            qual.key_usage_digital_signature,
                                        ),
                                        (
                                            "nonRepudiation",
                                            qual.key_usage_non_repudiation,
                                        ),
                                        (
                                            "keyEncipherment",
                                            qual.key_usage_key_encipherment,
                                        ),
                                        (
                                            "dataEncipherment",
                                            qual.key_usage_data_encipherment,
                                        ),
                                        ("keyAgreement", qual.key_usage_key_agreement),
                                        ("keyCertSign", qual.key_usage_key_cert_sign),
                                        ("crlSign", qual.key_usage_crl_sign),
                                        ("encipherOnly", qual.key_usage_encipher_only),
                                        ("decipherOnly", qual.key_usage_decipher_only),
                                    ]:
                                        lines.append(
                                            f'                                                    <ns5:KeyUsageBit name="{ku_name}">{str(ku_value).lower()}</ns5:KeyUsageBit>'
                                        )
                                    lines.append(
                                        "                                                </ns5:KeyUsage>"
                                    )
                                lines.append(
                                    "                                            </ns5:CriteriaList>"
                                )
                                lines.append(
                                    "                                        </ns5:QualificationElement>"
                                )
                            lines.append(
                                "                                    </ns5:Qualifications>"
                            )
                            lines.append("                                </Extension>")

                        # History Additional Service Information
                        if (
                            hasattr(hist, "additional_info")
                            and hist.additional_info.exists()
                        ):
                            for info in hist.additional_info.all():
                                critical = "true" if info.critical else "false"
                                lines.append(
                                    f'                                <Extension Critical="{critical}">'
                                )
                                lines.append(
                                    "                                    <AdditionalServiceInformation>"
                                )
                                lines.append(
                                    f'                                        <URI xml:lang="{info.language}">{_escape_xml(info.uri)}</URI>'
                                )
                                lines.append(
                                    "                                    </AdditionalServiceInformation>"
                                )
                                lines.append(
                                    "                                </Extension>"
                                )

                        lines.append(
                            "                            </ServiceInformationExtensions>"
                        )

                    lines.append("                        </ServiceHistoryInstance>")
                lines.append("                    </ServiceHistory>")

            lines.append("                </TSPService>")

        lines.append("            </TSPServices>")
        lines.append("        </TrustServiceProvider>")

    lines.append("    </TrustServiceProviderList>")
    lines.append("</TrustServiceStatusList>")

    return "\n".join(lines)

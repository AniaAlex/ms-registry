"""
XML Generation Functions for ETSI TS 119612 Trust Status Lists

This module generates ETSI TS 119612 compliant "EUgeneric" TSL XML -
unprefixed default namespace, matching real member-state trusted lists.
"""

# =============================================================================
# ETSI TS 119612 Namespace definitions
# =============================================================================
NS_TSL = "http://uri.etsi.org/02231/v2#"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ADDTYPES = "http://uri.etsi.org/02231/v2/additionaltypes#"
NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"
NS_EIDAS_SIG = "http://uri.etsi.org/TrstSvc/SvcInfoExt/eSigDir-1999-93-EC-TrustedList/#"
NS_XADES_141 = "http://uri.etsi.org/01903/v1.4.1#"


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


def export_tsl_to_file(scheme, filepath: str) -> str:
    """
    Export a TSL scheme to an XML file.

    Args:
        scheme: TSLScheme model instance
        filepath: Output file path

    Returns:
        The filepath where the XML was written
    """
    xml_content = generate_tsl_xml_etsi_format(scheme)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return filepath


def export_tsl_with_filename(scheme, output_dir: str) -> str:
    """
    Export a TSL scheme to a file with an auto-generated filename based on
    territory and sequence number.

    Args:
        scheme: TSLScheme model instance
        output_dir: Output directory path

    Returns:
        The filepath where the XML was written
    """
    import os

    filename = f"{scheme.territory}-TSL-{scheme.sequence_number}.xml"
    filepath = os.path.join(output_dir, filename)

    return export_tsl_to_file(scheme, filepath)


def export_multiple_tsls(schemes, output_dir: str) -> list:
    """
    Export multiple TSL schemes to XML files.

    Args:
        schemes: QuerySet or list of TSLScheme instances
        output_dir: Output directory path

    Returns:
        List of filepaths where XMLs were written
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    filepaths = []
    for scheme in schemes:
        filepath = export_tsl_with_filename(scheme, output_dir)
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
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')

    # Root element with all ETSI namespaces
    lines.append(
        "<TrustServiceStatusList "
        f'xmlns="{NS_TSL}" '
        f'xmlns:ns2="{NS_DS}" '
        f'xmlns:ns3="{NS_ADDTYPES}" '
        f'xmlns:ns4="{NS_XADES}" '
        f'xmlns:ns5="{NS_EIDAS_SIG}" '
        f'xmlns:ns6="{NS_XADES_141}" '
        f'Id="{scheme.tsl_id}" '
        'TSLTag="http://uri.etsi.org/19612/TSLTag">'
    )

    # SchemeInformation section
    lines.append("    <SchemeInformation>")

    # TSL Version Identifier
    lines.append(
        f"        <TSLVersionIdentifier>{scheme.version}</TSLVersionIdentifier>"
    )

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
            f'            <Name xml:lang="{name.language}">'
            f"{_escape_xml(name.value)}</Name>"
        )
    lines.append("        </SchemeOperatorName>")

    # Scheme Name
    if scheme.scheme_names.exists():
        lines.append("        <SchemeName>")
        for name in scheme.scheme_names.all():
            lines.append(
                f'            <Name xml:lang="{name.language}">'
                f"{_escape_xml(name.value)}</Name>"
            )
        lines.append("        </SchemeName>")

    # Scheme Information URI
    if scheme.information_uris.exists():
        lines.append("        <SchemeInformationURI>")
        for uri in scheme.information_uris.all():
            lines.append(
                f'            <URI xml:lang="{uri.language}">'
                f"{_escape_xml(uri.uri)}</URI>"
            )
        lines.append("        </SchemeInformationURI>")

    # Status Determination Approach
    lines.append(
        f"        <StatusDeterminationApproach>"
        f"{_escape_xml(scheme.status_determination_approach)}"
        f"</StatusDeterminationApproach>"
    )

    # Scheme Type Community Rules
    if scheme.community_rules.exists():
        lines.append("        <SchemeTypeCommunityRules>")
        for rule in scheme.community_rules.all():
            lines.append(
                f'            <URI xml:lang="{rule.language}">'
                f"{_escape_xml(rule.uri)}</URI>"
            )
        lines.append("        </SchemeTypeCommunityRules>")

    # Scheme Territory
    lines.append(f"        <SchemeTerritory>{scheme.territory}</SchemeTerritory>")

    # Policy or Legal Notice
    if scheme.legal_notices.exists():
        lines.append("        <PolicyOrLegalNotice>")
        for notice in scheme.legal_notices.all():
            lines.append(
                f'            <TSLLegalNotice xml:lang="{notice.language}">'
                f"{_escape_xml(notice.notice)}</TSLLegalNotice>"
            )
        lines.append("        </PolicyOrLegalNotice>")

    # Historical Information Period
    lines.append(
        f"        <HistoricalInformationPeriod>"
        f"{scheme.historical_information_period}"
        f"</HistoricalInformationPeriod>"
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
                        f"                            <X509Certificate>"
                        f"{cert.certificate_data}</X509Certificate>"
                    )
                    lines.append("                        </DigitalId>")
                    lines.append("                    </ServiceDigitalIdentity>")
                lines.append("                </ServiceDigitalIdentities>")

            lines.append(
                f"                <TSLLocation>"
                f"{_escape_xml(pointer.tsl_location)}</TSLLocation>"
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
                f"                        <SchemeTerritory>"
                f"{pointer.scheme_territory}</SchemeTerritory>"
            )
            lines.append("                    </OtherInformation>")
            lines.append("                    <OtherInformation>")
            lines.append(
                f"                        <ns3:MimeType>"
                f"{pointer.mime_type}</ns3:MimeType>"
            )
            lines.append("                    </OtherInformation>")
            if pointer.operator_names.exists():
                lines.append("                    <OtherInformation>")
                lines.append("                        <SchemeOperatorName>")
                for name in pointer.operator_names.all():
                    lines.append(
                        f'                            <Name xml:lang="{name.language}">'
                        f"{_escape_xml(name.value)}</Name>"
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
                f'                    <Name xml:lang="{name.language}">'
                f"{_escape_xml(name.value)}</Name>"
            )
        lines.append("                </TSPName>")

        # TSP Trade Name
        if provider.trade_names.exists():
            lines.append("                <TSPTradeName>")
            for name in provider.trade_names.all():
                lines.append(
                    f'                    <Name xml:lang="{name.language}">'
                    f"{_escape_xml(name.value)}</Name>"
                )
            lines.append("                </TSPTradeName>")

        # TSP Address
        lines.append("                <TSPAddress>")

        # Postal Addresses
        if provider.street_address:
            lines.append("                    <PostalAddresses>")
            lines.append('                        <PostalAddress xml:lang="en">')
            lines.append(
                f"                            <StreetAddress>"
                f"{_escape_xml(provider.street_address)}</StreetAddress>"
            )
            if provider.locality:
                lines.append(
                    f"                            <Locality>"
                    f"{_escape_xml(provider.locality)}</Locality>"
                )
            if provider.state_or_province:
                lines.append(
                    f"                            <StateOrProvince>"
                    f"{_escape_xml(provider.state_or_province)}</StateOrProvince>"
                )
            if provider.postal_code:
                lines.append(
                    f"                            <PostalCode>"
                    f"{_escape_xml(provider.postal_code)}</PostalCode>"
                )
            lines.append(
                f"                            <CountryName>"
                f"{_escape_xml(provider.country_name)}</CountryName>"
            )
            lines.append("                        </PostalAddress>")
            lines.append("                    </PostalAddresses>")

        # Electronic Address
        if provider.electronic_addresses.exists():
            lines.append("                    <ElectronicAddress>")
            for addr in provider.electronic_addresses.all():
                lines.append(
                    f'                        <URI xml:lang="{addr.language}">'
                    f"{_escape_xml(addr.uri)}</URI>"
                )
            lines.append("                    </ElectronicAddress>")

        lines.append("                </TSPAddress>")

        # TSP Information URI
        if provider.information_uris.exists():
            lines.append("                <TSPInformationURI>")
            for uri in provider.information_uris.all():
                lines.append(
                    f'                    <URI xml:lang="{uri.language}">'
                    f"{_escape_xml(uri.uri)}</URI>"
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
                f"                        <ServiceTypeIdentifier>"
                f"{service.service_type}</ServiceTypeIdentifier>"
            )

            # Service Name
            lines.append("                        <ServiceName>")
            for name in service.names.all():
                lines.append(
                    f'                            <Name xml:lang="{name.language}">'
                    f"{_escape_xml(name.value)}</Name>"
                )
            lines.append("                        </ServiceName>")

            # Service Digital Identity (Certificates)
            if service.certificates.exists():
                lines.append("                        <ServiceDigitalIdentity>")
                for cert in service.certificates.all():
                    lines.append("                            <DigitalId>")
                    lines.append(
                        f"                                <X509Certificate>"
                        f"{cert.get_base64_der()}</X509Certificate>"
                    )
                    lines.append(
                        f"                                <X509SubjectName>"
                        f"{_escape_xml(cert.x509_subject_name) if cert.x509_subject_name else ''}"  # noqa: E501
                        f"</X509SubjectName>"
                    )
                    lines.append(
                        f"                                <X509SKI>"
                        f"{cert.x509_ski if cert.x509_ski else ''}"
                        f"</X509SKI>"
                    )
                    lines.append("                            </DigitalId>")
                lines.append("                        </ServiceDigitalIdentity>")

            # Service Status
            lines.append(
                f"                        <ServiceStatus>"
                f"{service.status}</ServiceStatus>"
            )

            # Status Starting Time
            status_time = service.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            lines.append(
                f"                        <StatusStartingTime>"
                f"{status_time}</StatusStartingTime>"
            )

            # Service Information Extensions
            # (if any qualifications or additional info exist)
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
                            "                                    "
                            "<ns5:QualificationElement>"
                        )
                        lines.append(
                            "                                        "
                            "<ns5:Qualifiers>"
                        )
                        lines.append(
                            f"                                            "
                            f'<ns5:Qualifier uri="{_escape_xml(qual.qualifier_uri)}"/>'
                        )
                        lines.append(
                            "                                        "
                            "</ns5:Qualifiers>"
                        )
                        lines.append(
                            f"                                        "
                            f'<ns5:CriteriaList assert="{qual.criteria_assert}">'
                        )
                        # Add key usage bits if specified
                        if qual.key_usage:
                            lines.append(
                                "                                            "
                                "<ns5:KeyUsage>"
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
                                    f"                                                "
                                    f'<ns5:KeyUsageBit name="{ku_name}">'
                                    f"{str(ku_value).lower()}</ns5:KeyUsageBit>"
                                )
                            lines.append(
                                "                                            "
                                "</ns5:KeyUsage>"
                            )
                        lines.append(
                            "                                        "
                            "</ns5:CriteriaList>"
                        )
                        lines.append(
                            "                                    "
                            "</ns5:QualificationElement>"
                        )
                    lines.append(
                        "                                " "</ns5:Qualifications>"
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
                            f"                            "
                            f'<Extension Critical="{critical}">'
                        )
                        lines.append(
                            "                                "
                            "<AdditionalServiceInformation>"
                        )
                        lines.append(
                            f"                                    "
                            f'<URI xml:lang="{info.language}">'
                            f"{_escape_xml(info.uri)}</URI>"
                        )
                        lines.append(
                            "                                "
                            "</AdditionalServiceInformation>"
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
                        f"                            <ServiceTypeIdentifier>"
                        f"{hist.service_type}</ServiceTypeIdentifier>"
                    )
                    lines.append("                            <ServiceName>")
                    for name in hist.names.all():
                        lines.append(
                            f"                                "
                            f'<Name xml:lang="{name.language}">'
                            f"{_escape_xml(name.value)}</Name>"
                        )
                    lines.append("                            </ServiceName>")

                    # History Digital Identity (X509SubjectName and X509SKI)
                    if hasattr(hist, "digital_ids") and hist.digital_ids.exists():
                        lines.append(
                            "                            " "<ServiceDigitalIdentity>"
                        )
                        for digital_id in hist.digital_ids.all():
                            lines.append("                                <DigitalId>")
                            if digital_id.x509_subject_name:
                                lines.append(
                                    f"                                    "
                                    f"<X509SubjectName>"
                                    f"{_escape_xml(digital_id.x509_subject_name)}"
                                    f"</X509SubjectName>"
                                )
                            lines.append("                                </DigitalId>")
                            if digital_id.x509_ski:
                                lines.append(
                                    "                                <DigitalId>"
                                )
                                lines.append(
                                    f"                                    <X509SKI>"
                                    f"{digital_id.x509_ski}</X509SKI>"
                                )
                                lines.append(
                                    "                                </DigitalId>"
                                )
                        lines.append(
                            "                            " "</ServiceDigitalIdentity>"
                        )

                    lines.append(
                        f"                            <ServiceStatus>"
                        f"{hist.status}</ServiceStatus>"
                    )
                    hist_time = hist.status_starting_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    lines.append(
                        f"                            <StatusStartingTime>"
                        f"{hist_time}</StatusStartingTime>"
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
                            "                            "
                            "<ServiceInformationExtensions>"
                        )

                        # History Qualifications
                        if (
                            hasattr(hist, "qualifications")
                            and hist.qualifications.exists()
                        ):
                            lines.append(
                                "                                "
                                '<Extension Critical="true">'
                            )
                            lines.append(
                                "                                    "
                                "<ns5:Qualifications>"
                            )
                            for qual in hist.qualifications.all():
                                lines.append(
                                    "                                        "
                                    "<ns5:QualificationElement>"
                                )
                                lines.append(
                                    "                                            "
                                    "<ns5:Qualifiers>"
                                )
                                lines.append(
                                    f"                                                "
                                    f"<ns5:Qualifier uri="
                                    f'"{_escape_xml(qual.qualifier_uri)}"/>'
                                )
                                lines.append(
                                    "                                            "
                                    "</ns5:Qualifiers>"
                                )
                                lines.append(
                                    f"                                            "
                                    f"<ns5:CriteriaList assert="
                                    f'"{qual.criteria_assert}">'
                                )
                                if qual.key_usage:
                                    lines.append(
                                        "                                        "
                                        "        <ns5:KeyUsage>"
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
                                        (
                                            "keyAgreement",
                                            qual.key_usage_key_agreement,
                                        ),
                                        (
                                            "keyCertSign",
                                            qual.key_usage_key_cert_sign,
                                        ),
                                        (
                                            "crlSign",
                                            qual.key_usage_crl_sign,
                                        ),
                                        (
                                            "encipherOnly",
                                            qual.key_usage_encipher_only,
                                        ),
                                        (
                                            "decipherOnly",
                                            qual.key_usage_decipher_only,
                                        ),
                                    ]:
                                        lines.append(
                                            f"                                        "
                                            f"            <ns5:KeyUsageBit "
                                            f'name="{ku_name}">'
                                            f"{str(ku_value).lower()}"
                                            f"</ns5:KeyUsageBit>"
                                        )
                                    lines.append(
                                        "                                        "
                                        "        </ns5:KeyUsage>"
                                    )
                                lines.append(
                                    "                                            "
                                    "</ns5:CriteriaList>"
                                )
                                lines.append(
                                    "                                        "
                                    "</ns5:QualificationElement>"
                                )
                            lines.append(
                                "                                    "
                                "</ns5:Qualifications>"
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
                                    f"                                "
                                    f'<Extension Critical="{critical}">'
                                )
                                lines.append(
                                    "                                    "
                                    "<AdditionalServiceInformation>"
                                )
                                lines.append(
                                    f"                                        "
                                    f'<URI xml:lang="{info.language}">'
                                    f"{_escape_xml(info.uri)}</URI>"
                                )
                                lines.append(
                                    "                                    "
                                    "</AdditionalServiceInformation>"
                                )
                                lines.append(
                                    "                                " "</Extension>"
                                )

                        lines.append(
                            "                            "
                            "</ServiceInformationExtensions>"
                        )

                    lines.append("                        </ServiceHistoryInstance>")
                lines.append("                    </ServiceHistory>")

            lines.append("                </TSPService>")

        lines.append("            </TSPServices>")
        lines.append("        </TrustServiceProvider>")

    lines.append("    </TrustServiceProviderList>")
    lines.append("</TrustServiceStatusList>")

    return "\n".join(lines)

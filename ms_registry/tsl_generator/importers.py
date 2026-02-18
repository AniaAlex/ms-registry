"""
TSL Importers for ETSI TS 119612 Trust Status Lists

This module provides functions to import TSL data from various sources:
- YAML/PEM files (go-trust example-tsl format)
- XML files (ETSI TS 119612 format)
"""

import base64
import os
from datetime import datetime
from xml.etree import ElementTree as ET

import yaml

from .models import (
    SERVICE_STATUS_CHOICES,
    SERVICE_TYPE_CHOICES,
    TSL_TYPE_CHOICES,
    ServiceCertificate,
    ServiceHistoryInstance,
    ServiceHistoryName,
    ServiceName,
    ServiceSupplyPoint,
    TrustService,
    TrustServiceProvider,
    TSLPolicyOrLegalNotice,
    TSLScheme,
    TSLSchemeCommunityRule,
    TSLSchemeInformationURI,
    TSLSchemeName,
    TSLSchemeOperatorName,
    TSPElectronicAddress,
    TSPInformationURI,
    TSPName,
    TSPTradeName,
)


def import_scheme_from_yaml(yaml_path: str) -> TSLScheme:
    """
    Import a TSL scheme from a YAML file.

    Args:
        yaml_path: Path to scheme.yaml file

    Returns:
        Created TSLScheme instance
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scheme = TSLScheme.objects.create(
        name=data.get("name", os.path.basename(os.path.dirname(yaml_path))),
        tsl_type=data.get("tslType", TSL_TYPE_CHOICES[1][0]),
        sequence_number=data.get("sequenceNumber", 1),
        territory=data.get("territory", "SE"),
        historical_information_period=data.get("historicalInformationPeriod", 65535),
        status_determination_approach=data.get(
            "statusDeterminationApproach",
            "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/StatusDetn/EUappropriate",
        ),
    )

    # Import operator names
    for lang, name in data.get("operatorName", {}).items():
        TSLSchemeOperatorName.objects.create(scheme=scheme, language=lang, value=name)

    # Import scheme names
    for lang, name in data.get("schemeName", {}).items():
        TSLSchemeName.objects.create(scheme=scheme, language=lang, value=name)

    # Import information URIs
    for lang, uri in data.get("informationURI", {}).items():
        TSLSchemeInformationURI.objects.create(scheme=scheme, language=lang, uri=uri)

    # Import community rules
    for lang, uri in data.get("communityRules", {}).items():
        TSLSchemeCommunityRule.objects.create(scheme=scheme, language=lang, uri=uri)

    # Import legal notices
    for lang, notice in data.get("legalNotice", {}).items():
        TSLPolicyOrLegalNotice.objects.create(
            scheme=scheme, language=lang, notice=notice
        )

    return scheme


def import_provider_from_yaml(
    yaml_path: str, scheme: TSLScheme
) -> TrustServiceProvider:
    """
    Import a Trust Service Provider from a YAML file.

    Args:
        yaml_path: Path to provider.yaml file
        scheme: Parent TSLScheme instance

    Returns:
        Created TrustServiceProvider instance
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    provider = TrustServiceProvider.objects.create(
        scheme=scheme,
        street_address=data.get("postalAddress", {}).get("streetAddress", ""),
        locality=data.get("postalAddress", {}).get("locality", ""),
        state_or_province=data.get("postalAddress", {}).get("stateOrProvince", ""),
        postal_code=data.get("postalAddress", {}).get("postalCode", ""),
        country_name=data.get("postalAddress", {}).get("countryName", "SE"),
    )

    # Import names
    for lang, name in data.get("name", {}).items():
        TSPName.objects.create(provider=provider, language=lang, value=name)

    # Import trade names
    for lang, name in data.get("tradeName", {}).items():
        TSPTradeName.objects.create(provider=provider, language=lang, value=name)

    # Import electronic addresses
    for addr in data.get("electronicAddress", []):
        if isinstance(addr, str):
            TSPElectronicAddress.objects.create(provider=provider, uri=addr)
        elif isinstance(addr, dict):
            for lang, uri in addr.items():
                TSPElectronicAddress.objects.create(
                    provider=provider, uri=uri, language=lang
                )

    # Import information URIs
    for lang, uri in data.get("informationURI", {}).items():
        TSPInformationURI.objects.create(provider=provider, language=lang, uri=uri)

    return provider


def import_service_from_yaml(
    yaml_path: str, pem_path: str, provider: TrustServiceProvider
) -> TrustService:
    """
    Import a Trust Service from YAML and PEM files.

    Args:
        yaml_path: Path to service.yaml file
        pem_path: Path to certificate.pem file
        provider: Parent TrustServiceProvider instance

    Returns:
        Created TrustService instance
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    service = TrustService.objects.create(
        provider=provider,
        service_type=data.get("serviceType", SERVICE_TYPE_CHOICES[0][0]),
        status=data.get("status", SERVICE_STATUS_CHOICES[0][0]),
    )

    # Import names
    for lang, name in data.get("serviceName", {}).items():
        ServiceName.objects.create(service=service, language=lang, value=name)

    # Import supply points
    for uri in data.get("supplyPoints", []):
        ServiceSupplyPoint.objects.create(service=service, uri=uri)

    # Import certificate
    if os.path.exists(pem_path):
        with open(pem_path, "r", encoding="utf-8") as f:
            pem_content = f.read()
        ServiceCertificate.objects.create(service=service, certificate_pem=pem_content)

    return service


def import_tsl_directory(directory_path: str) -> TSLScheme:
    """
    Import a complete TSL from a go-trust example-tsl directory structure.

    Expected structure:
        directory_path/
        ├── scheme.yaml
        └── providers/
            └── provider1/
                ├── provider.yaml
                ├── cert1.pem
                └── cert1.yaml

    Args:
        directory_path: Path to TSL directory

    Returns:
        Created TSLScheme instance
    """
    # Import scheme
    scheme_path = os.path.join(directory_path, "scheme.yaml")
    if not os.path.exists(scheme_path):
        raise FileNotFoundError(f"scheme.yaml not found in {directory_path}")

    scheme = import_scheme_from_yaml(scheme_path)

    # Import providers
    providers_dir = os.path.join(directory_path, "providers")
    if os.path.exists(providers_dir):
        for provider_name in os.listdir(providers_dir):
            provider_dir = os.path.join(providers_dir, provider_name)
            if os.path.isdir(provider_dir):
                provider_yaml = os.path.join(provider_dir, "provider.yaml")
                if os.path.exists(provider_yaml):
                    provider = import_provider_from_yaml(provider_yaml, scheme)

                    # Find and import services (*.yaml files that aren't provider.yaml)
                    for filename in os.listdir(provider_dir):
                        if filename.endswith(".yaml") and filename != "provider.yaml":
                            service_yaml = os.path.join(provider_dir, filename)
                            # Look for corresponding .pem file
                            pem_filename = filename.replace(".yaml", ".pem")
                            pem_path = os.path.join(provider_dir, pem_filename)
                            import_service_from_yaml(service_yaml, pem_path, provider)

    return scheme


# =============================================================================
# XML Import Functions for ETSI TS 119612 TSL
# =============================================================================

# XML Namespaces used in ETSI TS 119612 TSL documents
TSL_NAMESPACES = {
    "tsl": "http://uri.etsi.org/02231/v2#",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
    "addtypes": "http://uri.etsi.org/02231/v2/additionaltypes#",
    "ecc": "http://uri.etsi.org/TrstSvc/SvcInfoExt/eSigDir-1999-93-EC-TrustedList/#",
}


def _find_text(element, path: str, namespaces: dict = None) -> str:
    """Find text content of an element, handling namespaces."""
    if namespaces is None:
        namespaces = TSL_NAMESPACES

    # Try with namespace prefix first
    el = element.find(path, namespaces)
    if el is not None and el.text:
        return el.text.strip()

    # Try without namespace (for default namespace elements)
    # Remove namespace prefix from path for fallback
    simple_path = path.split(":")[-1] if ":" in path else path
    for child in element:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag_name == simple_path and child.text:
            return child.text.strip()

    return ""


def _find_all_text(element, path: str, namespaces: dict = None) -> list:
    """Find all matching elements and return their text content."""
    if namespaces is None:
        namespaces = TSL_NAMESPACES

    results = []

    # Try with namespace
    elements = element.findall(path, namespaces)
    for el in elements:
        if el.text:
            results.append(el.text.strip())

    # If no results, try iterating children
    if not results:
        simple_path = path.split(":")[-1] if ":" in path else path
        for child in element:
            tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag_name == simple_path and child.text:
                results.append(child.text.strip())

    return results


def _get_lang_attr(element) -> str:
    """Extract xml:lang attribute from an element."""
    # Try various common attribute patterns
    lang = element.get("{http://www.w3.org/XML/1998/namespace}lang")
    if lang:
        return lang
    lang = element.get("lang")
    if lang:
        return lang
    return "en"  # Default to English


def _parse_datetime(dt_string: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    if not dt_string:
        return None

    # Remove trailing Z and handle various formats
    dt_string = dt_string.strip()

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue

    return None


def import_tsl_from_xml(xml_content: str, scheme_name: str = None) -> TSLScheme:
    """
    Import a TSL from ETSI TS 119612 XML content.

    This function parses the XML and creates all corresponding Django model instances,
    including extracting X.509 certificates from ServiceDigitalIdentity elements.

    Args:
        xml_content: XML string content
        scheme_name: Optional custom name for the scheme

    Returns:
        Created TSLScheme instance
    """
    root = ET.fromstring(xml_content)
    ns = TSL_NAMESPACES

    # Find SchemeInformation element
    scheme_info = root.find("tsl:SchemeInformation", ns)
    if scheme_info is None:
        # Try without namespace prefix
        for child in root:
            if "SchemeInformation" in child.tag:
                scheme_info = child
                break

    if scheme_info is None:
        raise ValueError("No SchemeInformation element found in XML")

    # Extract basic scheme information
    tsl_type = _find_text(scheme_info, "tsl:TSLType", ns)
    if not tsl_type:
        tsl_type = _find_text(scheme_info, "TSLType", ns)

    sequence_number_text = _find_text(scheme_info, "tsl:TSLSequenceNumber", ns)
    if not sequence_number_text:
        sequence_number_text = _find_text(scheme_info, "TSLSequenceNumber", ns)
    sequence_number = int(sequence_number_text) if sequence_number_text else 1

    territory = _find_text(scheme_info, "tsl:SchemeTerritory", ns)
    if not territory:
        territory = _find_text(scheme_info, "SchemeTerritory", ns)
    territory = territory or "XX"

    hist_period_text = _find_text(scheme_info, "tsl:HistoricalInformationPeriod", ns)
    if not hist_period_text:
        hist_period_text = _find_text(scheme_info, "HistoricalInformationPeriod", ns)
    hist_period = int(hist_period_text) if hist_period_text else 65535

    status_det = _find_text(scheme_info, "tsl:StatusDeterminationApproach", ns)
    if not status_det:
        status_det = _find_text(scheme_info, "StatusDeterminationApproach", ns)
    status_det = (
        status_det
        or "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/StatusDetn/EUappropriate"
    )

    # Parse dates
    issue_date_str = _find_text(scheme_info, "tsl:ListIssueDateTime", ns)
    if not issue_date_str:
        issue_date_str = _find_text(scheme_info, "ListIssueDateTime", ns)
    issue_date = _parse_datetime(issue_date_str)

    next_update_el = scheme_info.find("tsl:NextUpdate", ns)
    if next_update_el is None:
        for child in scheme_info:
            if "NextUpdate" in child.tag:
                next_update_el = child
                break

    next_update = None
    if next_update_el is not None:
        next_update_str = _find_text(next_update_el, "tsl:dateTime", ns)
        if not next_update_str:
            next_update_str = _find_text(next_update_el, "dateTime", ns)
        if not next_update_str and next_update_el.text:
            next_update_str = next_update_el.text.strip()
        next_update = _parse_datetime(next_update_str)

    # Distribution points
    dist_points = []
    dp_el = scheme_info.find("tsl:DistributionPoints", ns)
    if dp_el is None:
        for child in scheme_info:
            if "DistributionPoints" in child.tag:
                dp_el = child
                break

    if dp_el is not None:
        for uri_el in dp_el:
            if uri_el.text:
                dist_points.append(uri_el.text.strip())

    # Generate scheme name if not provided
    if not scheme_name:
        scheme_name = f"{territory} Trust List (Seq #{sequence_number})"

    # Create TSLScheme
    scheme = TSLScheme.objects.create(
        name=scheme_name,
        tsl_type=tsl_type or TSL_TYPE_CHOICES[1][0],
        sequence_number=sequence_number,
        territory=territory,
        issue_date=issue_date or datetime.now(),
        next_update=next_update,
        distribution_points="\n".join(dist_points),
        historical_information_period=hist_period,
        status_determination_approach=status_det,
    )

    # Import multi-language names
    _import_multilang_names(
        scheme_info,
        "tsl:SchemeOperatorName",
        "tsl:Name",
        ns,
        lambda lang, val: TSLSchemeOperatorName.objects.create(
            scheme=scheme, language=lang, value=val
        ),
    )

    _import_multilang_names(
        scheme_info,
        "tsl:SchemeName",
        "tsl:Name",
        ns,
        lambda lang, val: TSLSchemeName.objects.create(
            scheme=scheme, language=lang, value=val
        ),
    )

    # Import URIs
    _import_multilang_uris(
        scheme_info,
        "tsl:SchemeInformationURI",
        "tsl:URI",
        ns,
        lambda lang, uri: TSLSchemeInformationURI.objects.create(
            scheme=scheme, language=lang, uri=uri
        ),
    )

    _import_multilang_uris(
        scheme_info,
        "tsl:SchemeTypeCommunityRules",
        "tsl:URI",
        ns,
        lambda lang, uri: TSLSchemeCommunityRule.objects.create(
            scheme=scheme, language=lang, uri=uri
        ),
    )

    # Import legal notices
    policy_el = scheme_info.find("tsl:PolicyOrLegalNotice", ns)
    if policy_el is None:
        for child in scheme_info:
            if "PolicyOrLegalNotice" in child.tag:
                policy_el = child
                break

    if policy_el is not None:
        for notice_el in policy_el:
            if "TSLLegalNotice" in notice_el.tag and notice_el.text:
                lang = _get_lang_attr(notice_el)
                TSLPolicyOrLegalNotice.objects.create(
                    scheme=scheme, language=lang, notice=notice_el.text.strip()
                )

    # Import Trust Service Providers
    tsp_list = root.find("tsl:TrustServiceProviderList", ns)
    if tsp_list is None:
        for child in root:
            if "TrustServiceProviderList" in child.tag:
                tsp_list = child
                break

    if tsp_list is not None:
        for tsp_el in tsp_list:
            if "TrustServiceProvider" in tsp_el.tag:
                _import_tsp(tsp_el, scheme, ns)

    return scheme


def _import_multilang_names(
    parent_el, container_path: str, name_path: str, ns: dict, create_func
):
    """Import multi-language name elements."""
    container = parent_el.find(container_path, ns)
    if container is None:
        simple_path = container_path.split(":")[-1]
        for child in parent_el:
            if simple_path in child.tag:
                container = child
                break

    if container is not None:
        for name_el in container:
            if "Name" in name_el.tag and name_el.text:
                lang = _get_lang_attr(name_el)
                create_func(lang, name_el.text.strip())


def _import_multilang_uris(
    parent_el, container_path: str, uri_path: str, ns: dict, create_func
):
    """Import multi-language URI elements."""
    container = parent_el.find(container_path, ns)
    if container is None:
        simple_path = container_path.split(":")[-1]
        for child in parent_el:
            if simple_path in child.tag:
                container = child
                break

    if container is not None:
        for uri_el in container:
            if "URI" in uri_el.tag and uri_el.text:
                lang = _get_lang_attr(uri_el)
                create_func(lang, uri_el.text.strip())


def _import_tsp(tsp_el, scheme: TSLScheme, ns: dict) -> TrustServiceProvider:
    """Import a TrustServiceProvider from XML element."""
    tsp_info = tsp_el.find("tsl:TSPInformation", ns)
    if tsp_info is None:
        for child in tsp_el:
            if "TSPInformation" in child.tag:
                tsp_info = child
                break

    if tsp_info is None:
        return None

    # Extract postal address
    street = ""
    locality = ""
    state = ""
    postal_code = ""
    country = "XX"

    addr_el = tsp_info.find("tsl:TSPAddress", ns)
    if addr_el is None:
        for child in tsp_info:
            if "TSPAddress" in child.tag:
                addr_el = child
                break

    if addr_el is not None:
        postal_addrs = addr_el.find("tsl:PostalAddresses", ns)
        if postal_addrs is None:
            for child in addr_el:
                if "PostalAddresses" in child.tag:
                    postal_addrs = child
                    break

        if postal_addrs is not None:
            postal = None
            for child in postal_addrs:
                if "PostalAddress" in child.tag:
                    postal = child
                    break

            if postal is not None:
                street = _find_text(postal, "tsl:StreetAddress", ns) or _find_text(
                    postal, "StreetAddress", ns
                )
                locality = _find_text(postal, "tsl:Locality", ns) or _find_text(
                    postal, "Locality", ns
                )
                state = _find_text(postal, "tsl:StateOrProvince", ns) or _find_text(
                    postal, "StateOrProvince", ns
                )
                postal_code = _find_text(postal, "tsl:PostalCode", ns) or _find_text(
                    postal, "PostalCode", ns
                )
                country = (
                    _find_text(postal, "tsl:CountryName", ns)
                    or _find_text(postal, "CountryName", ns)
                    or "XX"
                )

    # Create provider
    provider = TrustServiceProvider.objects.create(
        scheme=scheme,
        street_address=street,
        locality=locality,
        state_or_province=state,
        postal_code=postal_code,
        country_name=country[:2],  # Ensure 2-char limit
    )

    # Import TSP names
    _import_multilang_names(
        tsp_info,
        "tsl:TSPName",
        "tsl:Name",
        ns,
        lambda lang, val: TSPName.objects.create(
            provider=provider, language=lang, value=val
        ),
    )

    # Import trade names
    _import_multilang_names(
        tsp_info,
        "tsl:TSPTradeName",
        "tsl:Name",
        ns,
        lambda lang, val: TSPTradeName.objects.create(
            provider=provider, language=lang, value=val
        ),
    )

    # Import electronic addresses
    if addr_el is not None:
        elec_addr = addr_el.find("tsl:ElectronicAddress", ns)
        if elec_addr is None:
            for child in addr_el:
                if "ElectronicAddress" in child.tag:
                    elec_addr = child
                    break

        if elec_addr is not None:
            for uri_el in elec_addr:
                if "URI" in uri_el.tag and uri_el.text:
                    lang = _get_lang_attr(uri_el)
                    TSPElectronicAddress.objects.create(
                        provider=provider, uri=uri_el.text.strip(), language=lang
                    )

    # Import information URIs
    _import_multilang_uris(
        tsp_info,
        "tsl:TSPInformationURI",
        "tsl:URI",
        ns,
        lambda lang, uri: TSPInformationURI.objects.create(
            provider=provider, language=lang, uri=uri
        ),
    )

    # Import services
    tsp_services = tsp_el.find("tsl:TSPServices", ns)
    if tsp_services is None:
        for child in tsp_el:
            if "TSPServices" in child.tag:
                tsp_services = child
                break

    if tsp_services is not None:
        for svc_el in tsp_services:
            if "TSPService" in svc_el.tag:
                _import_service(svc_el, provider, ns)

    return provider


def _import_service(svc_el, provider: TrustServiceProvider, ns: dict) -> TrustService:
    """Import a TrustService from XML element."""
    svc_info = svc_el.find("tsl:ServiceInformation", ns)
    if svc_info is None:
        for child in svc_el:
            if "ServiceInformation" in child.tag:
                svc_info = child
                break

    if svc_info is None:
        return None

    # Extract service type
    svc_type = _find_text(svc_info, "tsl:ServiceTypeIdentifier", ns)
    if not svc_type:
        svc_type = _find_text(svc_info, "ServiceTypeIdentifier", ns)
    svc_type = svc_type or SERVICE_TYPE_CHOICES[0][0]

    # Extract status
    status = _find_text(svc_info, "tsl:ServiceStatus", ns)
    if not status:
        status = _find_text(svc_info, "ServiceStatus", ns)
    status = status or SERVICE_STATUS_CHOICES[0][0]

    # Extract status starting time
    status_time_str = _find_text(svc_info, "tsl:StatusStartingTime", ns)
    if not status_time_str:
        status_time_str = _find_text(svc_info, "StatusStartingTime", ns)
    status_time = _parse_datetime(status_time_str)

    # Create service
    service = TrustService.objects.create(
        provider=provider,
        service_type=svc_type,
        status=status,
        status_starting_time=status_time or datetime.now(),
    )

    # Import service names
    _import_multilang_names(
        svc_info,
        "tsl:ServiceName",
        "tsl:Name",
        ns,
        lambda lang, val: ServiceName.objects.create(
            service=service, language=lang, value=val
        ),
    )

    # Import supply points
    ssp_el = svc_info.find("tsl:ServiceSupplyPoints", ns)
    if ssp_el is None:
        for child in svc_info:
            if "ServiceSupplyPoints" in child.tag:
                ssp_el = child
                break

    if ssp_el is not None:
        for sp_el in ssp_el:
            if sp_el.text:
                ServiceSupplyPoint.objects.create(
                    service=service, uri=sp_el.text.strip()
                )

    # Import X.509 certificates from ServiceDigitalIdentity
    _import_service_certificates(svc_info, service, ns)

    # Import service history
    _import_service_history(svc_el, service, ns)

    return service


def _import_service_certificates(svc_info, service: TrustService, ns: dict):
    """
    Import X.509 certificates from ServiceDigitalIdentity element.

    This extracts certificate data from the XML and stores it in the
    ServiceCertificate model, optionally extracting metadata like
    subject CN, issuer CN, serial number, and validity dates.
    """
    sdi_el = svc_info.find("tsl:ServiceDigitalIdentity", ns)
    if sdi_el is None:
        for child in svc_info:
            if "ServiceDigitalIdentity" in child.tag:
                sdi_el = child
                break

    if sdi_el is None:
        return

    # Find all DigitalId elements
    for digital_id in sdi_el:
        if "DigitalId" not in digital_id.tag:
            continue

        # Look for X509Certificate element
        x509_el = digital_id.find("tsl:X509Certificate", ns)
        if x509_el is None:
            for child in digital_id:
                if "X509Certificate" in child.tag:
                    x509_el = child
                    break

        if x509_el is not None and x509_el.text:
            cert_data = x509_el.text.strip()
            _extract_x509_certificate(cert_data, service)


def _extract_x509_certificate(cert_b64: str, service: TrustService):
    """
    Extract and store an X.509 certificate.

    Converts base64-encoded DER to PEM format and optionally extracts
    certificate metadata using the cryptography library if available.
    """
    # Clean up base64 data (remove whitespace)
    cert_b64_clean = "".join(cert_b64.split())

    # Convert to PEM format
    pem_lines = ["-----BEGIN CERTIFICATE-----"]
    # Split into 64-character lines
    for i in range(0, len(cert_b64_clean), 64):
        pem_lines.append(cert_b64_clean[i : i + 64])
    pem_lines.append("-----END CERTIFICATE-----")
    pem_content = "\n".join(pem_lines)

    # Try to extract certificate metadata using cryptography library
    subject_cn = ""
    issuer_cn = ""
    serial_number = ""
    not_before = None
    not_after = None

    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        # Decode base64 to DER
        der_data = base64.b64decode(cert_b64_clean)
        cert = x509.load_der_x509_certificate(der_data, default_backend())

        # Extract subject CN
        try:
            subject_cn_attrs = cert.subject.get_attributes_for_oid(
                x509.oid.NameOID.COMMON_NAME
            )
            if subject_cn_attrs:
                subject_cn = subject_cn_attrs[0].value
        except Exception:
            pass

        # Extract issuer CN
        try:
            issuer_cn_attrs = cert.issuer.get_attributes_for_oid(
                x509.oid.NameOID.COMMON_NAME
            )
            if issuer_cn_attrs:
                issuer_cn = issuer_cn_attrs[0].value
        except Exception:
            pass

        # Extract serial number
        serial_number = format(cert.serial_number, "x").upper()

        # Extract validity dates
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc

    except ImportError:
        # cryptography library not available, skip metadata extraction
        pass
    except Exception:
        # Failed to parse certificate, still store the raw data
        pass

    # Create ServiceCertificate record
    ServiceCertificate.objects.create(
        service=service,
        certificate_pem=pem_content,
        subject_cn=subject_cn[:500] if subject_cn else "",
        issuer_cn=issuer_cn[:500] if issuer_cn else "",
        serial_number=serial_number[:100] if serial_number else "",
        not_before=not_before,
        not_after=not_after,
    )


def _import_service_history(svc_el, service: TrustService, ns: dict):
    """Import service history instances from XML."""
    history_el = svc_el.find("tsl:ServiceHistory", ns)
    if history_el is None:
        for child in svc_el:
            if "ServiceHistory" in child.tag:
                history_el = child
                break

    if history_el is None:
        return

    for hist_inst in history_el:
        if "ServiceHistoryInstance" not in hist_inst.tag:
            continue

        # Extract history data
        hist_type = _find_text(hist_inst, "tsl:ServiceTypeIdentifier", ns)
        if not hist_type:
            hist_type = _find_text(hist_inst, "ServiceTypeIdentifier", ns)
        hist_type = hist_type or service.service_type

        hist_status = _find_text(hist_inst, "tsl:ServiceStatus", ns)
        if not hist_status:
            hist_status = _find_text(hist_inst, "ServiceStatus", ns)
        hist_status = hist_status or SERVICE_STATUS_CHOICES[0][0]

        hist_time_str = _find_text(hist_inst, "tsl:StatusStartingTime", ns)
        if not hist_time_str:
            hist_time_str = _find_text(hist_inst, "StatusStartingTime", ns)
        hist_time = _parse_datetime(hist_time_str)

        if not hist_time:
            continue  # Skip if no valid timestamp

        # Create history instance
        history = ServiceHistoryInstance.objects.create(
            service=service,
            service_type=hist_type,
            status=hist_status,
            status_starting_time=hist_time,
        )

        # Import history names
        _import_multilang_names(
            hist_inst,
            "tsl:ServiceName",
            "tsl:Name",
            ns,
            lambda lang, val: ServiceHistoryName.objects.create(
                history=history, language=lang, value=val
            ),
        )


def import_tsl_from_xml_file(filepath: str, scheme_name: str = None) -> TSLScheme:
    """
    Import a TSL from an ETSI TS 119612 XML file.

    Args:
        filepath: Path to the XML file
        scheme_name: Optional custom name for the scheme

    Returns:
        Created TSLScheme instance
    """
    with open(filepath, "r", encoding="utf-8") as f:
        xml_content = f.read()

    return import_tsl_from_xml(xml_content, scheme_name)

# TODO: to be removed

"""Generate a test LOTL (List of Trusted Lists) — unsigned, for development/testing.

Based on the structure defined in:
  https://github.com/webuild-consortium/wp4-trust-group/tools/lotl/

Produces:
  output/list_of_trusted_lists.json
  output/list_of_trusted_lists.xml
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from lxml import etree

    HAS_LXML = True
except ImportError:
    HAS_LXML = False

# ---------------------------------------------------------------------------
# Config (mirrors tools/lotl/settings.py)
# ---------------------------------------------------------------------------

TL_TYPE_TO_LOTE_URI = {
    "wrpac-provider": ("http://uri.etsi.org/19602/LoTEType/EUWRPACProvidersList"),
    "wrprc-provider": ("http://uri.etsi.org/19602/LoTEType/EUWRPRCProvidersList"),
    "pub-eaa-provider": ("http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"),
    "pid-provider": ("http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"),
    "qeaa-provider": ("http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"),
    "eaa-provider": ("http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"),
    "wallet-provider": ("http://uri.etsi.org/19602/LoTEType/EUWalletProvidersList"),
    "ebwoid-provider": (
        "http://uri.etsi.org/19602/LoTEType/EURegistrarsAndRegistersList"
    ),
}

LOTE_TAG = "http://uri.etsi.org/19602/LoTETag"

SCHEME_OPERATOR_NAME = "WE BUILD WP4 Trust Group"
SCHEME_NAME = "WP4 List of Trusted Lists"
SCHEME_INFO_URI = "https://webuild-consortium.github.io/wp4-trust-group/"

OUTPUT_DIR = Path("output")

# ---------------------------------------------------------------------------
# Data model (mirrors tools/lotl/tl_entry.py)
# ---------------------------------------------------------------------------


@dataclass
class TLEntry:
    tl_type: str
    participant_id: str
    tl_url: str
    tl_url_xml: Optional[str] = None
    tl_url_json: Optional[str] = None
    trust_anchor: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_tl_url_json(self) -> str:
        return self.tl_url_json or self.tl_url

    def get_tl_url_xml(self) -> str:
        return self.tl_url_xml or self.tl_url


# ---------------------------------------------------------------------------
# Test data: one or more participants per TL type
# ---------------------------------------------------------------------------

TEST_ENTRIES: list[TLEntry] = [
    TLEntry(
        tl_type="pid-provider",
        participant_id="italy",
        tl_url="https://trust.example.it/pid_providers.json",
        tl_url_xml="https://trust.example.it/pid_providers.xml",
        tl_url_json="https://trust.example.it/pid_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestITALY==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "Italian PID Authority", "country": "IT"},
    ),
    TLEntry(
        tl_type="pid-provider",
        participant_id="germany",
        tl_url="https://trust.example.de/pid_providers.json",
        tl_url_xml="https://trust.example.de/pid_providers.xml",
        tl_url_json="https://trust.example.de/pid_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestGERMANY==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "German PID Authority", "country": "DE"},
    ),
    TLEntry(
        tl_type="wallet-provider",
        participant_id="italy",
        tl_url="https://trust.example.it/wallet_providers.json",
        tl_url_json="https://trust.example.it/wallet_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestWALLETIT==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "Italian Wallet Authority", "country": "IT"},
    ),
    TLEntry(
        tl_type="wallet-provider",
        participant_id="france",
        tl_url="https://trust.example.fr/wallet_providers.json",
        tl_url_json="https://trust.example.fr/wallet_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestWALLETFR==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "French Wallet Authority", "country": "FR"},
    ),
    TLEntry(
        tl_type="wrpac-provider",
        participant_id="eu-central",
        tl_url="https://trust.example.eu/wrpac_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestWRPAC==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "EU WRPAC Authority", "country": "EU"},
    ),
    TLEntry(
        tl_type="wrprc-provider",
        participant_id="eu-central",
        tl_url="https://trust.example.eu/wrprc_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestWRPRC==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "EU WRPRC Authority", "country": "EU"},
    ),
    TLEntry(
        tl_type="pub-eaa-provider",
        participant_id="spain",
        tl_url="https://trust.example.es/pub_eaa_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestPUBEAAES==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "Spanish Pub-EAA Authority", "country": "ES"},
    ),
    TLEntry(
        tl_type="ebwoid-provider",
        participant_id="eu-central",
        tl_url="https://trust.example.eu/ebwoid_providers.json",
        trust_anchor=(
            "-----BEGIN CERTIFICATE-----\nMIIBtestEBWOID==\n-----END CERTIFICATE-----"
        ),
        metadata={"operator_name": "EU EBWOID Registry", "country": "EU"},
    ),
]


# ---------------------------------------------------------------------------
# JSON generator (mirrors tools/lotl/json_generator.py)
# ---------------------------------------------------------------------------


def generate_lotl_json(
    entries: list[TLEntry], sequence_number: int = 1
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    issue_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    next_month = now.month + 6
    next_year = now.year + (next_month - 1) // 12
    next_month = ((next_month - 1) % 12) + 1
    next_update = now.replace(year=next_year, month=next_month).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    distribution_points: list[dict[str, Any]] = []
    for entry in entries:
        dist: dict[str, Any] = {
            "tlType": entry.tl_type,
            "participantId": entry.participant_id,
            "tlUrl": entry.tl_url,
            "tlUrlJson": entry.get_tl_url_json(),
            "tlUrlXml": entry.get_tl_url_xml(),
        }
        if entry.metadata:
            dist["metadata"] = entry.metadata
        distribution_points.append(dist)

    scheme_info: dict[str, Any] = {
        "loteVersionIdentifier": 1,
        "loteSequenceNumber": sequence_number,
        "loteType": "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
        "schemeOperatorName": [{"lang": "en", "value": SCHEME_OPERATOR_NAME}],
        "schemeOperatorAddress": {
            "postalAddresses": [],
            "electronicAddress": [{"lang": "en", "uri": SCHEME_INFO_URI}],
        },
        "schemeName": [{"lang": "en", "value": SCHEME_NAME}],
        "schemeInformationURI": [{"lang": "en", "uri": SCHEME_INFO_URI}],
        "statusDeterminationApproach": (
            "http://uri.etsi.org/TrstSvc/TrustedList/StatusDetn/EUappropriate"
        ),
        "schemeTypeCommunityRules": [],
        "schemeTerritory": "EU",
        "listIssueDateTime": issue_dt,
        "nextUpdate": next_update,
        "distributionPoints": distribution_points,
    }

    return {"loteTag": LOTE_TAG, "schemeInformation": scheme_info}


# ---------------------------------------------------------------------------
# XML generator (mirrors tools/lotl/xml_generator.py, ETSI TS 119 612 v2.4.1)
# ---------------------------------------------------------------------------


def generate_lotl_xml(entries: list[TLEntry], sequence_number: int = 1) -> bytes:
    if not HAS_LXML:
        raise RuntimeError("lxml is required for XML generation: pip install lxml")

    NS = "http://uri.etsi.org/19612/v2.4.1#"
    XSD_NS = "http://www.w3.org/2001/XMLSchema-instance"
    XML_NS = "http://www.w3.org/XML/1998/namespace"

    nsmap = {None: NS, "xsd": XSD_NS}

    now = datetime.now(timezone.utc)
    issue_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    next_month = now.month + 6
    next_year = now.year + (next_month - 1) // 12
    next_month = ((next_month - 1) % 12) + 1
    next_update = now.replace(year=next_year, month=next_month).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    def elem(parent, tag, text=None):
        el = etree.SubElement(parent, f"{{{NS}}}{tag}")
        if text is not None:
            el.text = str(text)
        return el

    def lang_elem(parent, tag, text, lang="en"):
        el = etree.SubElement(parent, f"{{{NS}}}{tag}")
        name = etree.SubElement(el, f"{{{NS}}}Name")
        name.set(f"{{{XML_NS}}}lang", lang)
        name.text = text
        return el

    root = etree.Element(f"{{{NS}}}TrustServiceStatusList", nsmap=nsmap)

    si = etree.SubElement(root, f"{{{NS}}}SchemeInformation")
    elem(si, "TSLVersionIdentifier", "6")
    elem(si, "TSLSequenceNumber", str(sequence_number))
    elem(si, "TSLType", "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric")

    lang_elem(si, "SchemeOperatorName", SCHEME_OPERATOR_NAME)

    addr = elem(si, "SchemeOperatorAddress")
    elem(addr, "PostalAddresses")
    electronic = elem(addr, "ElectronicAddress")
    uri_el = elem(electronic, "URI")
    uri_el.set(f"{{{XML_NS}}}lang", "en")
    uri_el.text = SCHEME_INFO_URI

    lang_elem(si, "SchemeName", SCHEME_NAME)

    si_uri = elem(si, "SchemeInformationURI")
    uri2 = elem(si_uri, "URI")
    uri2.set(f"{{{XML_NS}}}lang", "en")
    uri2.text = SCHEME_INFO_URI

    elem(
        si,
        "StatusDeterminationApproach",
        "http://uri.etsi.org/TrstSvc/TrustedList/StatusDetn/EUappropriate",
    )
    elem(si, "SchemeTerritory", "EU")
    elem(si, "ListIssueDateTime", issue_dt)

    nu = elem(si, "NextUpdate")
    elem(nu, "dateTime", next_update)

    dp = elem(si, "DistributionPoints")
    for entry in entries:
        dp_uri = elem(dp, "URI")
        dp_uri.text = entry.tl_url

    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    entries = TEST_ENTRIES
    sequence = 1

    # --- JSON ---
    lotl_json = generate_lotl_json(entries, sequence_number=sequence)
    json_path = OUTPUT_DIR / "list_of_trusted_lists.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(lotl_json, f, indent=2)
    print(f"[JSON] Written to {json_path}")
    dp_count = len(lotl_json["schemeInformation"]["distributionPoints"])
    print(f"       {dp_count} distribution points")

    # --- XML ---
    if HAS_LXML:
        xml_bytes = generate_lotl_xml(entries, sequence_number=sequence)
        xml_path = OUTPUT_DIR / "list_of_trusted_lists.xml"
        with open(xml_path, "wb") as f:
            f.write(xml_bytes)
        print(f"[XML]  Written to {xml_path}")
    else:
        print("[XML]  Skipped — install lxml: pip install lxml")

    # --- Summary ---
    print()
    print("Entries by type:")
    by_type: dict[str, list[str]] = {}
    for e in entries:
        by_type.setdefault(e.tl_type, []).append(e.participant_id)
    for tl_type, participants in sorted(by_type.items()):
        print(f"  {tl_type}: {', '.join(participants)}")


if __name__ == "__main__":
    main()

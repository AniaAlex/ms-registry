# SIROS Registry Integration with Member State Registry

**Date:** 16 February 2026  
**Version:** 1.0

## Overview

This document describes how the [SIROS VCTM Registry](https://github.com/sirosfoundation/registry.siros.org) can be integrated with this Member State Registry to provide a complete EUDI Wallet trust infrastructure.

## Architecture Comparison

### Member State Registry (This Project)

**Purpose:** Authority and trust management

| Component | Function |
|-----------|----------|
| Legal Entities | Organizations participating in the ecosystem |
| Registered Entities | PID Providers, Attestation Providers, Relying Parties |
| Supervisory Authorities | Data Protection Authorities (DPAs) |
| Entitlements | What each entity is authorized to do |
| TSL Generator | ETSI TS 119612 Trust Status Lists |

**Answers:** *"WHO is trusted to participate?"*

### SIROS Registry

**Purpose:** Credential type metadata

| Component | Function |
|-----------|----------|
| VCTMs | Verifiable Credential Type Metadata |
| Schemas | Credential attribute definitions |
| Display Properties | How credentials should be rendered |
| Stable URLs | Consistent references to credential types |

**Answers:** *"WHAT do credentials contain and look like?"*

## Trust Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    EU Commission LOTL                            │
│         (List of Trusted Lists - Points to MS TSLs)             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Member State TSL (This Registry)                    │
│                                                                  │
│  • Lists authorized PID Providers                               │
│  • Lists authorized Attestation Providers (QEAA, PuB-EAA)       │
│  • Lists registered Relying Parties                             │
│  • Links to SIROS for credential type definitions               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SIROS VCTM Registry                            │
│                                                                  │
│  • Credential type schemas                                      │
│  • Display metadata                                             │
│  • Validation rules                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. TSL Service Definition URIs

The TSL generator can reference SIROS VCTMs in service definitions:

```xml
<TSPService>
    <ServiceInformation>
        <ServiceTypeIdentifier>
            http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/QEAA_Provider
        </ServiceTypeIdentifier>
        <ServiceName>
            <Name xml:lang="en">Swedish Tax Agency - Identity Credential Service</Name>
        </ServiceName>
        <!-- Link to SIROS for credential metadata -->
        <TSPServiceDefinitionURI>
            <URI xml:lang="en">https://registry.siros.org/skatteverket/identity-credential.json</URI>
        </TSPServiceDefinitionURI>
    </ServiceInformation>
</TSPService>
```

### 2. Entity Entitlements with Credential Type References

Store SIROS VCTM URLs in entity entitlements:

```python
# Model extension for credential type reference
class EntityEntitlement(BaseModel):
    registered_entity = models.ForeignKey(RegisteredEntity, ...)
    entitlement_type = models.CharField(choices=EntitlementType.choices)
    entitlement_uri = models.URLField(...)
    
    # SIROS integration
    credential_type_vctm_url = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="SIROS VCTM URL for this credential type"
    )
```

### 3. Credential Type Registry Table

New model to cache/reference SIROS credential types:

```python
class CredentialTypeReference(BaseModel):
    """Reference to SIROS VCTM credential type"""
    
    vctm_url = models.URLField(
        max_length=2048,
        unique=True,
        help_text="SIROS registry URL (e.g., https://registry.siros.org/org/credential.json)"
    )
    credential_type_name = models.CharField(max_length=500)
    organization = models.CharField(max_length=200)
    
    # Cached metadata from SIROS
    vct_value = models.CharField(
        max_length=500,
        help_text="Verifiable Credential Type identifier"
    )
    display_name = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    
    # Sync tracking
    last_synced = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
```

### 4. API Endpoint for VCTM Sync

```python
# views.py
class SyncSIROSVCTMView(APIView):
    """Sync credential type metadata from SIROS registry"""
    
    def post(self, request):
        vctm_url = request.data.get('vctm_url')
        
        # Fetch VCTM from SIROS
        response = requests.get(vctm_url)
        vctm_data = response.json()
        
        # Create/update local reference
        ref, created = CredentialTypeReference.objects.update_or_create(
            vctm_url=vctm_url,
            defaults={
                'credential_type_name': vctm_data.get('name'),
                'vct_value': vctm_data.get('vct'),
                'display_name': vctm_data.get('display', {}).get('name'),
                'description': vctm_data.get('description', ''),
            }
        )
        return Response({'status': 'synced', 'id': str(ref.id)})
```

## Data Flow Examples

### Example 1: Registering a PID Provider

1. **Member State Registry:**
   - Register Skatteverket as Legal Entity
   - Create RegisteredEntity with role `PID_PROVIDER`
   - Add entitlement: `http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/PID_Issuer`
   - Link to SIROS VCTM: `https://registry.siros.org/skatteverket/pid.json`

2. **SIROS Registry:**
   - Hosts the PID VCTM with schema definition
   - Provides display properties for wallet rendering

3. **TSL Output:**
   ```xml
   <TrustServiceProvider>
       <TSPName>Skatteverket</TSPName>
       <TSPServices>
           <TSPService>
               <ServiceTypeIdentifier>
                   http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/PID_Issuer
               </ServiceTypeIdentifier>
               <TSPServiceDefinitionURI>
                   <URI>https://registry.siros.org/skatteverket/pid.json</URI>
               </TSPServiceDefinitionURI>
           </TSPService>
       </TSPServices>
   </TrustServiceProvider>
   ```

### Example 2: Wallet Verification Flow

```
1. Wallet receives credential from issuer
2. Wallet extracts issuer identifier
3. Wallet queries MS TSL → finds issuer in trusted list ✓
4. Wallet gets SIROS VCTM URL from TSL
5. Wallet fetches VCTM → gets display properties
6. Wallet renders credential with correct branding
```

## Implementation Roadmap

### Phase 1: Basic Integration
- [ ] Add `credential_type_vctm_url` field to `EntityEntitlement` model
- [ ] Update TSL generator to include `TSPServiceDefinitionURI` with SIROS URLs
- [ ] Add VCTM URL field to admin interface

### Phase 2: Credential Type Registry
- [ ] Create `CredentialTypeReference` model
- [ ] Build SIROS sync management command
- [ ] Add credential type selection in entity registration

### Phase 3: Validation & Display
- [ ] Validate VCTM URLs resolve correctly
- [ ] Cache VCTM metadata locally
- [ ] Display credential type info in registry UI

### Phase 4: Bidirectional Integration
- [ ] Publish MS registry data in SIROS-compatible format
- [ ] Generate `.well-known/vctm-registry.json` for MS credentials
- [ ] Enable SIROS to aggregate MS-specific VCTMs

## API Endpoints (Proposed)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/credential-types/` | GET | List known credential types from SIROS |
| `/api/credential-types/sync/` | POST | Sync VCTM from SIROS URL |
| `/api/credential-types/{id}/` | GET | Get cached credential type details |
| `/api/entities/{id}/credential-types/` | GET | List credential types for entity |

## Security Considerations

1. **VCTM URL Validation**
   - Only allow URLs from trusted SIROS domains
   - Validate HTTPS
   - Check for valid JSON response

2. **Caching Strategy**
   - Cache VCTMs locally to reduce external dependencies
   - Set reasonable TTL (e.g., 24 hours)
   - Handle SIROS downtime gracefully

3. **Trust Boundaries**
   - MS Registry = authoritative for entity trust status
   - SIROS = reference for credential format/display only
   - Never trust SIROS for authorization decisions

## References

- [SIROS VCTM Registry](https://github.com/sirosfoundation/registry.siros.org)
- [SIROS mtcvctm GitHub Action](https://github.com/sirosfoundation/mtcvctm)
- [ETSI TS 119 612](https://www.etsi.org/deliver/etsi_ts/119600_119699/119612/) - Trust Status Lists
- [SD-JWT VC Specification](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- [EUDI Wallet Architecture Reference Framework](https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework)

## Conclusion

The Member State Registry and SIROS serve complementary roles:

- **Member State Registry** provides the **trust anchor** (who is authorized)
- **SIROS** provides **interoperability metadata** (what credentials look like)

Integration enables wallets to:
1. Verify issuer trust via MS TSL
2. Fetch credential display properties via SIROS
3. Render credentials consistently across the EU

Both systems are necessary for a complete EUDI Wallet ecosystem.

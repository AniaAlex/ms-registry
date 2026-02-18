# Combined Trust + MS Registry Setup

This setup runs **both** go-trust and ms-registry in the same docker-compose file.

## Benefits
- Single network namespace (services can communicate)
- Managed together with one Puppet class
- Share infrastructure (always-https)
- Simpler deployment

## Setup

### 1. Update your existing `vc::trust` manifest

Replace `/path/to/puppet/modules/vc/manifests/trust.pp` with the contents of:
```
manifests/trust_combined.pp
```

### 2. Update the docker-compose template

Replace `/path/to/puppet/modules/vc/templates/trust/docker-compose.yml.erb` with:
```
templates/docker-compose-combined.yml.erb
```

### 3. Add Hiera data

Add to your Hiera (encrypt with eyaml):

```yaml
# MS Registry secrets (REQUIRED - encrypt with eyaml)
ms_registry::secret_key: >
  ENC[PKCS7,MIICzTCCAskCAQ...]

ms_registry::db_password: >
  ENC[PKCS7,MIIEYAYJKoZI...]

# MS Registry config (optional)
ms_registry::env: PRODUCTION
ms_registry::debug: 'False'
ms_registry::redis_url: redis://redis:6379/0

# Docker image tags (optional)
vc::trust::trust_tag: latest
vc::trust::ms_registry_tag: latest
```

### 4. Apply Puppet

```bash
puppet agent -t
```

## Result

All services running in `/opt/trust/docker-compose.yml`:

```
Services:
├── always-https    (port 80)
├── go-trust        (port 443)
├── ms-registry     (port 8000, 3030)
├── db              (PostgreSQL for ms-registry)
└── redis           (Redis for ms-registry)
```

## Firewall Ports

- **80**: HTTP (always-https)
- **443**: HTTPS (go-trust)
- **8000**: HTTP API (ms-registry)
- **3030**: uWSGI socket (ms-registry)

## Alternative: Keep Separate

If you prefer to keep them in separate docker-compose files:
1. Use the original separate manifests (`ms_registry.pp`)
2. Services will be in different directories:
   - `/opt/trust/` - go-trust
   - `/opt/ms-registry/` - ms-registry

# Puppet Manifest for MS Registry

This directory contains Puppet manifests and templates for deploying MS Registry using your existing Sunet infrastructure pattern.

## Files

- `manifests/ms_registry.pp` - Puppet class for MS Registry
- `templates/docker-compose.yml.erb` - Docker Compose template
- `hiera-example.yaml` - Example Hiera data with eyaml encryption

## Installation

### 1. Copy files to your Puppet repository

```bash
# Copy manifest
cp manifests/ms_registry.pp /path/to/puppet/modules/vc/manifests/

# Copy template
cp templates/docker-compose.yml.erb /path/to/puppet/modules/vc/templates/ms_registry/
```

### 2. Add secrets to Hiera

Encrypt your secrets with eyaml:

```bash
# Generate Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Encrypt the secret key
eyaml encrypt -s 'your-django-secret-key-here'

# Encrypt database password
eyaml encrypt -s 'your-db-password-here'
```

Add to your Hiera data (e.g., `common.yaml` or `production.yaml`):

```yaml
ms_registry::secret_key: >
  ENC[PKCS7,MIICzTCCAskCAQ...]

ms_registry::db_password: >
  ENC[PKCS7,MIIEYAYJKoZI...]

ms_registry::env: PRODUCTION
ms_registry::debug: 'False'
ms_registry::redis_url: redis://redis:6379/0
```

### 3. Apply the manifest

Add to your node definition:

```puppet
node 'ms-registry.example.com' {
  include vc::ms_registry
}
```

Or with custom parameters:

```puppet
node 'ms-registry.example.com' {
  class { 'vc::ms_registry':
    ms_registry_tag => 'v1.0.0',
    interface       => 'ens3',
  }
}
```

### 4. Run Puppet

```bash
puppet agent -t
```

## What it does

The manifest will:
1. Configure firewall (nftables/UFW) for ports 8000 and 3030
2. Create `/opt/ms-registry/docker-compose.yml` from template
3. Inject decrypted secrets from Hiera into environment variables
4. Start the MS Registry service with docker-compose

## Ports

- **8000**: HTTP API and web interface
- **3030**: uWSGI socket

## Docker Image

The manifest expects the image at:
```
docker.sunet.se/docker-ms-registry:latest
```

Make sure to build and push the image to your registry first.

## Customization

### Change ports

Edit `manifests/ms_registry.pp` and update the port numbers in the firewall rules and docker-compose template.

### Change deployment directory

Default is `/opt/ms-registry/`. To change, update the `compose_dir` parameter in the `sunet::docker_compose` resource.

### Add SSL certificates

Similar to the trust service, you can mount SSL certificates:

```erb
volumes:
  - /etc/dehydrated/private/ms-registry.example.com.pem:/tls_cert.pem:ro
  - /etc/dehydrated/private/ms-registry.example.com.key:/tls_key.pem:ro
```

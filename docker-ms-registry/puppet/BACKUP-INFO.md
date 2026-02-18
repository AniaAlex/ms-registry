# Backup Files

This directory contains backups of the original vc::trust configuration before adding ms-registry integration.

## Backup Files:

- **trust_original.pp.bak** - Original Puppet manifest for vc::trust (go-trust only)
- **docker-compose-original.yml.erb.bak** - Original docker-compose template (go-trust only)

## Current Files (with ms-registry):

- **trust_combined.pp** - Combined manifest with both go-trust and ms-registry
- **docker-compose-combined.yml.erb** - Combined docker-compose with all services

## To Revert to Original:

If you need to go back to just go-trust:

1. Use `trust_original.pp.bak` as the manifest
2. Use `docker-compose-original.yml.erb.bak` as the template
3. Remove ms-registry specific Hiera data

## Created: 2026-02-18

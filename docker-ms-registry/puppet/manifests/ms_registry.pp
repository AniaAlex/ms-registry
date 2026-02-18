class vc::ms_registry (
  String $ms_registry_tag = 'latest',
  String $interface = 'ens3',
  String $secret_key = lookup('ms_registry::secret_key'),
  String $db_password = lookup('ms_registry::db_password'),
  String $env = lookup('ms_registry::env', String, 'first', 'PRODUCTION'),
  String $debug = lookup('ms_registry::debug', String, 'first', 'False'),
  String $redis_url = lookup('ms_registry::redis_url', String, 'first', 'redis://redis:6379/0'),
){
  if $::facts['sunet_nftables_enabled'] == 'yes' {
    sunet::nftables::docker_expose { 'ms_registry_http' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 8000,
    }

    sunet::nftables::docker_expose { 'ms_registry_socket' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 3030,
    }
  } else {
    sunet::misc::ufw_allow { 'allow-ms-registry-http':
      from => 'any',
      port => '8000'
    }
    sunet::misc::ufw_allow { 'allow-ms-registry-socket':
      from => 'any',
      port => '3030'
    }
  }

  sunet::docker_compose {'ms-registry':
    content          => template('vc/ms_registry/docker-compose.yml.erb'),
    service_name     => 'ms-registry',
    compose_dir      => '/opt',
    compose_filename => 'docker-compose.yml',
    description      => 'MS Registry Service',
  }

}

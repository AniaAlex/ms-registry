class vc::trust (
  String $trust_tag = 'latest',
  String $ms_registry_tag = 'latest',
  String $interface = 'ens3',
  String $secret_key = lookup('ms_registry::secret_key'),
  String $db_password = lookup('ms_registry::db_password'),
  String $env = lookup('ms_registry::env', String, 'first', 'PRODUCTION'),
  String $debug = lookup('ms_registry::debug', String, 'first', 'False'),
  String $redis_url = lookup('ms_registry::redis_url', String, 'first', 'redis://redis:6379/0'),
){
  if $::facts['sunet_nftables_enabled'] == 'yes' {
    sunet::nftables::docker_expose { 'allow_http' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 80,
    }

    sunet::nftables::docker_expose { 'trust' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 443,
    }

    sunet::nftables::docker_expose { 'ms_registry_http' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 8000,
    }

    sunet::nftables::docker_expose { 'ms_registry_https' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 8443,
    }

    sunet::nftables::docker_expose { 'ms_registry_socket' :
      iif           => $interface,
      allow_clients => 'any',
      port          => 3030,
    }
  } else {
    sunet::misc::ufw_allow { 'allow-http':
      from => 'any',
      port => '80'
    }
    sunet::misc::ufw_allow { 'allow-https':
      from => 'any',
      port => '443'
    }
    sunet::misc::ufw_allow { 'allow-ms-registry-http':
      from => 'any',
      port => '8000'
    }
    sunet::misc::ufw_allow { 'allow-ms-registry-https':
      from => 'any',
      port => '8443'
    }
    sunet::misc::ufw_allow { 'allow-ms-registry-socket':
      from => 'any',
      port => '3030'
    }
  }

  sunet::docker_compose {'trust':
    content          => template('vc/trust/docker-compose.yml.erb'),
    service_name     => 'trust',
    compose_dir      => '/opt',
    compose_filename => 'docker-compose.yml',
    description      => 'Trust engine and MS Registry',
  }

}

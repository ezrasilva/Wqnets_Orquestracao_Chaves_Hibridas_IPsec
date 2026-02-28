#!/usr/bin/env python3
"""Generate self-signed TLS certs for agents and orchestrator only."""

import os
import sys
from datetime import datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


AGENTS = {
    "alice": "192.168.100.10",
    "bob": "192.168.100.11",
    "carol": "192.168.100.12",
    "dave": "192.168.100.13",
}


def generate_self_signed_cert(common_name, dns_names, ip_addresses):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SP"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Sao Paulo"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SDKM-PoC"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(name) for name in dns_names]
                + [x509.IPAddress(addr) for addr in ip_addresses]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256(), default_backend())
    )

    return key, cert


def main():
    cert_dir = Path("/scripts/certs")
    cert_dir.mkdir(exist_ok=True, mode=0o755)

    print("=" * 60)
    print("  GERADOR TLS (AGENTES + ORCHESTRATOR)")
    print("=" * 60)

    for name, ip in AGENTS.items():
        ip_addr = IPv4Address(ip)
        dns_names = [name, f"{name}.local"]
        key, cert = generate_self_signed_cert(name, dns_names, [ip_addr])

        key_path = cert_dir / f"{name}_key.pem"
        cert_path = cert_dir / f"{name}_cert.pem"

        with open(key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        os.chmod(key_path, 0o600)

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"  ✓ {name}: {cert_path} / {key_path}")

    # Certificado genérico para fallback (agent_cert.pem / agent_key.pem)
    fallback_ips = [IPv4Address(ip) for ip in AGENTS.values()]
    fallback_dns = ["agent", "agent.local"] + list(AGENTS.keys())
    key, cert = generate_self_signed_cert("agent", fallback_dns, fallback_ips)

    key_path = cert_dir / "agent_key.pem"
    cert_path = cert_dir / "agent_cert.pem"

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    os.chmod(key_path, 0o600)

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"  ✓ agent: {cert_path} / {key_path}")

    print("=" * 60)
    print("  ✓ Certificados TLS gerados com sucesso!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

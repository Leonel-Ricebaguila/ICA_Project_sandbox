#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for HTTPS development
Creates: server.key, server.crt, server-fullchain.crt
"""

import os
import sys
import ipaddress
from datetime import datetime, timedelta

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("[ERROR] cryptography package not found")
    print("Install it with: pip install cryptography")
    sys.exit(1)


def generate_self_signed_cert(
    output_dir="certs/server",
    common_name="localhost",
    country="MX",
    state="Yucatan",
    locality="Merida",
    organization="UPY Center",
    validity_days=365
):
    """Generate self-signed SSL certificate for development"""
    
    print(f"\n[*] Generating SSL certificates for {common_name}...")
    print(f"[*] Output directory: {output_dir}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate private key
    print("\n[1/3] Generating RSA private key (2048 bits)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Save private key
    key_file = os.path.join(output_dir, "server.key")
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"    [OK] Private key saved: {key_file}")
    
    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
        x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Generate certificate
    print("\n[2/3] Generating X.509 certificate...")
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=validity_days)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv6Address("::1")),
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).sign(private_key, hashes.SHA256())
    
    # Save certificate
    cert_file = os.path.join(output_dir, "server.crt")
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"    [OK] Certificate saved: {cert_file}")
    
    # Create fullchain (same as cert for self-signed)
    fullchain_file = os.path.join(output_dir, "server-fullchain.crt")
    with open(fullchain_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"    [OK] Fullchain saved: {fullchain_file}")
    
    # Display certificate info
    print("\n[*] Certificate Information:")
    print(f"    Subject: {common_name}")
    print(f"    Valid from: {cert.not_valid_before}")
    print(f"    Valid until: {cert.not_valid_after}")
    print(f"    Serial: {cert.serial_number}")
    print(f"    SANs: localhost, 127.0.0.1, ::1")
    
    print("\n[SUCCESS] SSL certificates generated successfully!")
    print("\n[WARNING] This is a self-signed certificate for DEVELOPMENT only.")
    print("          Browsers will show a security warning. For production, use:")
    print("          - Let's Encrypt (certbot)")
    print("          - Commercial CA certificate")
    print("          - Internal PKI")
    
    return key_file, cert_file, fullchain_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate self-signed SSL certificates")
    parser.add_argument("--cn", default="localhost", help="Common Name (default: localhost)")
    parser.add_argument("--days", type=int, default=365, help="Validity in days (default: 365)")
    parser.add_argument("--out", default="certs/server", help="Output directory (default: certs/server)")
    
    args = parser.parse_args()
    
    try:
        generate_self_signed_cert(
            output_dir=args.out,
            common_name=args.cn,
            validity_days=args.days
        )
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


import ipaddress
from typing import List

def ip_allowed(remote_addr: str, cidrs: List[str]) -> bool:
    """
    Devuelve True si la IP remota cae dentro de alguno de los rangos CIDR permitidos.
    Acepta IPv4/IPv6. Si remote_addr es None o inválida, devuelve False.
    """
    if not remote_addr:
        return False
    try:
        ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False

    for cidr in cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            if ip in net:
                return True
        except ValueError:
            # CIDR mal escrito: lo ignoramos
            continue
    return False

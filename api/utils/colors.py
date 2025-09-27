"""Módulo utilitário para impressão colorida no terminal."""

import json
from typing import Any, Dict

class Colors:
    """Classe para armazenar códigos de cores ANSI para o terminal."""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_node_info(title: str, details: Dict[str, Any]):
    """Imprime uma caixa de informações formatada e colorida para cada nó do grafo."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}--- NÓ: {title} ---{Colors.ENDC}")
    for key, value in details.items():
        value_str = json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)
        
        if "Erro" in key or "NÃO" in str(value):
            print(f"{Colors.YELLOW}{key}:{Colors.ENDC} {Colors.RED}{value_str}{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}{key}:{Colors.ENDC} {Colors.GREEN}{value_str}{Colors.ENDC}")

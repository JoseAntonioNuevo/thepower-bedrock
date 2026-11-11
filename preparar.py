"""Inserta nuestro archivo Python en CloudFormation; no se conecta a AWS."""

import hashlib
import json
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parent
    codigo = (raiz / "lambda_function.py").read_text()
    plantilla = json.loads((raiz / "plantilla.json").read_text())
    # CloudFormation empaqueta este código como index.py para Lambda.
    # Así evitamos un bucket S3, un ZIP y Docker en esta demo pequeña.
    plantilla["Resources"]["Funcion"]["Properties"]["Code"]["ZipFile"] = codigo
    plantilla["Parameters"]["AppVersion"]["Default"] = hashlib.sha256(codigo.encode()).hexdigest()[
        :12
    ]
    carpeta = raiz / ".demo-aws"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / "plantilla.json"
    destino.write_text(json.dumps(plantilla, ensure_ascii=False, indent=2) + "\n")
    print(f"Preparada: {destino}")


if __name__ == "__main__":
    main()

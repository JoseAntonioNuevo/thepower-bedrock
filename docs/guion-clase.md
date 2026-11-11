# S17 · Guion corto

Parte de esta carpeta, con Python, dependencias y tu perfil preparados.
Los bloques son Bash (macOS, Linux o Git Bash en Windows).

## 1. Identidad y cuota

Selecciona tu proyecto de aula y comprueba que Bedrock admite inferencias.

```bash
export AWS_PROFILE=tu-perfil
export AWS_REGION=eu-north-1
export S17_ACCOUNT=123456789012
export S17_STACK=s17-clasificador-tu-nombre
aws login --profile "$AWS_PROFILE" --region "$AWS_REGION"
python cliente.py preflight
```

Si falla el preflight, detente y revisa la cuota; no hay clasificación real posible con cuota cero.

## 2. Crear

Inserta el código y crea Lambda, HTTP API con IAM, rol y logs.

```bash
python preparar.py
aws cloudformation deploy \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  --stack-name "$S17_STACK" --template-file .demo-aws/plantilla.json \
  --capabilities CAPABILITY_IAM --tags Project=thepower-s17 Purpose=classroom-demo
python cliente.py estado
```

## 3. Medir

Envía como máximo seis clasificaciones; relee los REPORT sin repetir las inferencias.

```bash
python cliente.py medir --execute
python cliente.py logs
```

## 4. Probar errores

Comprueba salud 200, rechazo sin firma 403 y entrada vacía 422, sin consumir el modelo.

```bash
python cliente.py probar --health --execute
python cliente.py probar --sin-firma --execute
python cliente.py probar --texto "" --execute
```

## 5. Estimar

Calcula 1.000 solicitudes con supuestos; no envía 1.000 peticiones.

```bash
python coste.py
```

## 6. Retirar

Elimina exclusivamente tu stack y comprueba su desaparición en CloudFormation, Lambda y API Gateway.

```bash
aws cloudformation delete-stack \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" --stack-name "$S17_STACK"
aws cloudformation wait stack-delete-complete \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" --stack-name "$S17_STACK"
aws cloudformation describe-stacks \
  --profile "$AWS_PROFILE" --region "$AWS_REGION" --stack-name "$S17_STACK"
```

La última lectura debe indicar que el stack no existe.

# Ejecutar desde src
# Imagen base de Lambda con Python 3.11
FROM public.ecr.aws/lambda/python:3.13

# Instalar dependencias
COPY lambdas/parse_file/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY lambdas/parse_file/lambda_function.py ${LAMBDA_TASK_ROOT}
COPY common ${LAMBDA_TASK_ROOT}/common

# Comando por defecto (archivo.py:funcion)
CMD ["lambda_function.handler"]

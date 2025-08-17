# Ejecutar desde src
# Imagen base de Lambda con Python 3.11
FROM public.ecr.aws/lambda/python:3.13

# Instalar dependencias
COPY lambdas/issue_maker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY lambdas/issue_maker/lambda_function.py ${LAMBDA_TASK_ROOT}
COPY common ${LAMBDA_TASK_ROOT}/common

# Comando por defecto (archivo.py:funcion)
CMD ["lambda_function.handler"]
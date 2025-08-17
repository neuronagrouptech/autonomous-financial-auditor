import json
import logging
from common.services.github_client import fetch_finance_files
from common.core.clients import get_s3_client
from common.core.config import GITHUB_BRANCH, GITHUB_REPO, GITHUB_TOKEN, S3_BUCKET_NAME

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Lambda activada desde GitHub Actions")
    logger.info(f"Event recibido: {json.dumps(event, indent=2)}")

    try:
        pl, bs = fetch_finance_files(GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN)
        logger.info("Succesffully retrieved files from github")

        logger.info("Attemping to save files to S3")

        s3 = get_s3_client()


        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='input/quarter_p&l.txt',
            Body=pl.encode('utf-8'),
            ContentType="text/plain"
        )
        logger.info("Saved quarter_p&l.txt")

        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key='input/balance_sheet.txt',
            Body=bs.encode('utf-8'),
            ContentType="text/plain"
        ) 
        logger.info("Saved balance_sheet.txt")     

        # Respuesta simple
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Lambda Success',
                'timestamp': context.aws_request_id
            })
        }
        logger.info("Respuesta enviada correctamente")

    except Exception as e:
        logger.info("Error en ejecución")

        response = {
            'statusCode': 501,
            'body': json.dumps({
                'message': 'Lambda internal fail: {e}',
                'timestamp': context.aws_request_id
            })
        }
    
    
    return response
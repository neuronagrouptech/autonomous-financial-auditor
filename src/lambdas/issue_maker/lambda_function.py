import json
import logging
from common.services.github_client import create_github_issue
from common.core.config import GITHUB_REPO, GITHUB_TOKEN
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Lambda activada desde GitHub Actions")
    logger.info(f"Event recibido: {json.dumps(event, indent=2)}")

    logger.info(f"Parsing content")
    content = event.get("content", {})


    if content.get('status') != 'ok' :
        try:
            logger.info(f"Creating issue")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = f"Issue generated - {now}"
            create_github_issue(GITHUB_REPO, GITHUB_TOKEN, title, str(content))

            logger.info("Issue created")

            response = {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Lambda Success',
                    'timestamp': context.aws_request_id
                })
            }
            return response

        except Exception as e:
            logger.info("Error en ejecución")

            response = {
                'statusCode': 501,
                'body': json.dumps({
                    'message': f'Lambda internal fail: {e}',
                    'timestamp': context.aws_request_id
                })
            }

            return response
    
        
    else:
        logger.info('No issue found in document. No issue was raised')

        response = {
                'statusCode': 201,
                'body': 'No issue created',
                'timestamp': context.aws_request_id
            }        
        return response
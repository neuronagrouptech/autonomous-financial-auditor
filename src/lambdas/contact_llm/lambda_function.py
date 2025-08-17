import json
import logging
import uuid
from common.core.clients import get_s3_client, get_bedrock_agent
from common.core.config import S3_BUCKET_NAME, AGENT_ALIAS_ID

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):

    try:
        logger.info('Getting s3 client: Attempting')
        s3 = get_s3_client()
        logger.info('Getting s3 client: Success')

        logger.info('Retrieving S3 files: Attempting')
        pl_object = s3.get_object(Bucket=S3_BUCKET_NAME, Key='input/quarter_p&l.txt')
        logger.info('Retrieving S3 files: PL - Success')
        bs_object = s3.get_object(Bucket=S3_BUCKET_NAME, Key='input/balance_sheet.txt')
        logger.info('Retrieving S3 files: BS - Success')

        logger.info('Decoding files: Start')
        pl = pl_object['Body'].read().decode('utf-8')
        bs = bs_object['Body'].read().decode('utf-8')
        logger.info('Decoding files: Success')

        logger.info('Contacting Agent: Start')
        client = get_bedrock_agent()
        session_id = str(uuid.uuid4())

        response = client.invoke_agent(
            agentId="XYKIHMJLKO",
            agentAliasId=AGENT_ALIAS_ID,  # Bedrock Agent Alias
            sessionId=session_id,
            inputText=f'''
            Validate this financial document and respond with JSON only. Begin response with {{ and end with }}. No other text.

            === BALANCE SHEET ===
            {bs}

            === PROFIT & LOSS STATEMENT ===
            {pl}
            '''
        )
        logger.info('Contacting Agent: Success')

        logger.info('Saving report: Start')
        output = ""
        for event in response["completion"]:
            if "chunk" in event:
                output += event["chunk"]["bytes"].decode("utf-8")

        logger.info('Saving report: Start')
        s3.put_object(
                Bucket=S3_BUCKET_NAME,
                Key='output/report.txt',
                Body=output.encode('utf-8'),
                ContentType="text/plain"
            )
        logger.info('Saving report: Success')


        try:
            output_dict = json.loads(output)
        except json.JSONDecodeError as e:
            logger.info("Error al parsear JSON:", e)
            output_dict = {"raw_output": output}

        return {
            'statusCode': 200,
            'message': 'Lambda Success',
            'content': output_dict,
            'timestamp': context.aws_request_id
        }

    except Exception as e:
        logger.info(f"Error: Exception clause. detail:{e}")

        response = {
            'statusCode': 501,
            'body': json.dumps({
                'message': 'Lambda internal fail: {e}',
                'timestamp': context.aws_request_id
            })
        }

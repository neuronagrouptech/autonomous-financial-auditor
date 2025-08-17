import boto3
from botocore.config import Config
import os
from common.core.config import AWS_REGION

# codigo para manejo de clientes de aws.

def get_boto3_session():
    """Logica para discernir el entorno y cargar el perfil"""
    env = os.getenv("ENV", "local")
    print(f'log: Environment: {env}')
    if env == "local":
        from common.core.config import LOCAL_PROFILE_NAME
        print(f'log: profile name : {LOCAL_PROFILE_NAME}')
        return boto3.Session(profile_name=LOCAL_PROFILE_NAME)
    return boto3.Session()

def get_dynamodb_client():
    session = get_boto3_session()
    return session.client("dynamodb", region_name=AWS_REGION)

def get_bedrock_client():
    session = get_boto3_session()
    return session.client("bedrock-runtime", region_name=AWS_REGION)

def get_bedrock_agent():
    config = Config(
        read_timeout=180,       
        connect_timeout=10,
        retries={
            'max_attempts': 3,   # Retry automático
            'mode': 'adaptive'
        }
    )
    session = get_boto3_session()
    return session.client("bedrock-agent-runtime", region_name=AWS_REGION, config=config) 

def get_s3_client():
    session = get_boto3_session()
    return session.client("s3", region_name=AWS_REGION)


def get_langchain_bedrock_client(model_id, max_tokens: int = 250, temperature: float = 0.6, top_p: float =0.6):
    """Sets up langchain bedrock client"""
    from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
    
    client = get_bedrock_client()
    
    #client config
    chat = ChatBedrockConverse(
        client=client,
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
        )
    return chat







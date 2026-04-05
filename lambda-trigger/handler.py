"""
Lambda Trigger Function
Validates EventBridge events and starts Step Function execution
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS Clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

# Environment variables
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
EXECUTION_TABLE_NAME = os.environ['EXECUTION_TABLE_NAME']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for EventBridge trigger
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response with execution details
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract event details
        event_id = event.get('id')
        detail_type = event.get('detail-type')
        detail = event.get('detail', {})
        order_id = detail.get('orderId')
        
        if not order_id:
            logger.error("Missing orderId in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing orderId'})
            }
        
        # Check for duplicate processing (idempotency)
        if is_duplicate(order_id, event_id):
            logger.info(f"Duplicate event detected for order {order_id}, skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Duplicate event, skipped'})
            }
        
        # Validate event schema
        validation_result = validate_event(detail)
        if not validation_result['valid']:
            logger.error(f"Invalid event: {validation_result['errors']}")
            return {
                'statusCode': 400,
                'body': json.dumps({'errors': validation_result['errors']})
            }
        
        # Start Step Function execution
        execution_arn = start_step_function(event, order_id)
        
        # Record execution
        record_execution(order_id, event_id, execution_arn)
        
        logger.info(f"Successfully started execution: {execution_arn}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Execution started',
                'executionArn': execution_arn,
                'orderId': order_id
            })
        }
        
    except Exception as e:
        logger.exception(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def validate_event(detail: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate event schema and required fields
    
    Args:
        detail: Event detail object
        
    Returns:
        Validation result with errors if any
    """
    errors = []
    required_fields = ['orderId', 'customerId', 'totalAmount']
    
    for field in required_fields:
        if field not in detail:
            errors.append(f"Missing required field: {field}")
    
    # Validate data types
    if 'totalAmount' in detail:
        try:
            amount = float(detail['totalAmount'])
            if amount <= 0:
                errors.append("totalAmount must be greater than 0")
        except (ValueError, TypeError):
            errors.append("totalAmount must be a valid number")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def is_duplicate(order_id: str, event_id: str) -> bool:
    """
    Check if this event has already been processed
    
    Args:
        order_id: Order ID
        event_id: Event ID
        
    Returns:
        True if duplicate, False otherwise
    """
    try:
        table = dynamodb.Table(EXECUTION_TABLE_NAME)
        response = table.get_item(
            Key={
                'orderId': order_id,
                'eventId': event_id
            }
        )
        return 'Item' in response
    except Exception as e:
        logger.warning(f"Error checking for duplicate: {str(e)}")
        return False


def start_step_function(event: Dict[str, Any], order_id: str) -> str:
    """
    Start Step Function execution
    
    Args:
        event: Full EventBridge event
        order_id: Order ID
        
    Returns:
        Execution ARN
    """
    execution_name = f"{order_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    response = stepfunctions.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps(event)
    )
    
    return response['executionArn']


def record_execution(order_id: str, event_id: str, execution_arn: str) -> None:
    """
    Record execution in DynamoDB for idempotency
    
    Args:
        order_id: Order ID
        event_id: Event ID
        execution_arn: Step Function execution ARN
    """
    try:
        table = dynamodb.Table(EXECUTION_TABLE_NAME)
        table.put_item(
            Item={
                'orderId': order_id,
                'eventId': event_id,
                'executionArn': execution_arn,
                'timestamp': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + 86400 * 7  # 7 days TTL
            }
        )
    except Exception as e:
        logger.error(f"Error recording execution: {str(e)}")
        # Don't fail the execution if we can't record

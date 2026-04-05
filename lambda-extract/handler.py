"""
Lambda Extract Function
Extracts order data from multiple sources (DynamoDB, external APIs)
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List
import logging
from decimal import Decimal

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS Clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
ORDERS_TABLE_NAME = os.environ['ORDERS_TABLE_NAME']
CUSTOMERS_TABLE_NAME = os.environ['CUSTOMERS_TABLE_NAME']

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Extract Lambda
    
    Args:
        event: Contains orderId, customerId, orderDetails
        context: Lambda context
        
    Returns:
        Extracted data from all sources
    """
    logger.info(f"Extract function started: {json.dumps(event, cls=DecimalEncoder)}")
    
    try:
        order_id = event.get('orderId')
        customer_id = event.get('customerId')
        order_details = event.get('orderDetails', {})
        
        if not order_id or not customer_id:
            raise ValueError("Missing orderId or customerId")
        
        # Extract customer data
        customer_data = get_customer_data(customer_id)
        
        # Extract order history
        order_history = get_order_history(customer_id)
        
        # Extract product details from order items
        product_data = extract_product_data(order_details.get('items', []))
        
        # Perform fraud check (simulated)
        fraud_score = perform_fraud_check(customer_id, order_details)
        
        # Build extracted data response
        extracted_data = {
            'orderId': order_id,
            'customerId': customer_id,
            'extractedAt': datetime.utcnow().isoformat(),
            'customer': customer_data,
            'orderHistory': order_history,
            'products': product_data,
            'fraudCheck': {
                'score': fraud_score,
                'status': 'APPROVED' if fraud_score < 0.5 else 'REVIEW_REQUIRED'
            },
            'rawOrderDetails': order_details
        }
        
        logger.info(f"Extraction completed for order {order_id}")
        
        return {
            'statusCode': 200,
            'body': extracted_data
        }
        
    except Exception as e:
        logger.exception(f"Error in extract function: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'orderId': event.get('orderId', 'unknown')
            }
        }


def get_customer_data(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve customer information from DynamoDB
    
    Args:
        customer_id: Customer ID
        
    Returns:
        Customer data
    """
    try:
        table = dynamodb.Table(CUSTOMERS_TABLE_NAME)
        response = table.get_item(Key={'customerId': customer_id})
        
        if 'Item' in response:
            customer = response['Item']
            return {
                'customerId': customer.get('customerId'),
                'name': customer.get('name', 'Unknown'),
                'email': customer.get('email', ''),
                'phone': customer.get('phone', ''),
                'tier': customer.get('tier', 'Standard'),
                'lifetimeValue': float(customer.get('lifetimeValue', 0)),
                'registrationDate': customer.get('registrationDate', ''),
                'address': customer.get('address', {})
            }
        else:
            logger.warning(f"Customer {customer_id} not found, using defaults")
            return {
                'customerId': customer_id,
                'name': 'Unknown',
                'email': '',
                'tier': 'Standard',
                'lifetimeValue': 0.0
            }
    except Exception as e:
        logger.error(f"Error fetching customer data: {str(e)}")
        return {
            'customerId': customer_id,
            'name': 'Unknown',
            'error': str(e)
        }


def get_order_history(customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get customer's order history
    
    Args:
        customer_id: Customer ID
        limit: Maximum number of orders to return
        
    Returns:
        List of previous orders
    """
    try:
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        response = table.query(
            IndexName='CustomerIdIndex',
            KeyConditionExpression='customerId = :cid',
            ExpressionAttributeValues={':cid': customer_id},
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        orders = []
        for item in response.get('Items', []):
            orders.append({
                'orderId': item.get('orderId'),
                'orderDate': item.get('orderDate'),
                'totalAmount': float(item.get('totalAmount', 0)),
                'status': item.get('status', 'unknown')
            })
        
        return orders
    except Exception as e:
        logger.error(f"Error fetching order history: {str(e)}")
        return []


def extract_product_data(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract and enrich product data
    
    Args:
        items: List of order items
        
    Returns:
        Enriched product data
    """
    products = []
    
    for item in items:
        product = {
            'productId': item.get('productId'),
            'quantity': item.get('quantity', 1),
            'unitPrice': item.get('unitPrice', 0),
            'name': item.get('name', 'Unknown Product'),
            'category': item.get('category', 'General'),
            'inStock': True,  # Would check inventory in real implementation
            'supplier': item.get('supplier', 'Default'),
            'weight': item.get('weight', 0),
            'dimensions': item.get('dimensions', {})
        }
        products.append(product)
    
    return products


def perform_fraud_check(customer_id: str, order_details: Dict[str, Any]) -> float:
    """
    Perform fraud risk assessment
    
    Args:
        customer_id: Customer ID
        order_details: Order details
        
    Returns:
        Fraud risk score (0.0 - 1.0)
    """
    # Simplified fraud scoring logic
    score = 0.0
    
    total_amount = order_details.get('totalAmount', 0)
    
    # High value orders increase risk
    if total_amount > 1000:
        score += 0.2
    if total_amount > 5000:
        score += 0.3
    
    # International orders (could check shipping address)
    shipping = order_details.get('shippingAddress', {})
    if shipping.get('country', 'US') != 'US':
        score += 0.15
    
    # New customer (would check registration date)
    # Simplified: customer_id format check
    if customer_id.startswith('NEW-'):
        score += 0.25
    
    return min(score, 1.0)

"""
Lambda Transform Function
Transforms and enriches extracted data for analytics
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List
import logging
from decimal import Decimal

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Tax rates by state (simplified)
TAX_RATES = {
    'NY': 0.08875,
    'CA': 0.0725,
    'TX': 0.0625,
    'FL': 0.06,
    'IL': 0.0625,
    'PA': 0.06,
    'OH': 0.0575,
    'default': 0.07
}

# Customer tier discount rates
TIER_DISCOUNTS = {
    'Platinum': 0.15,
    'Gold': 0.10,
    'Silver': 0.05,
    'Standard': 0.00
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Transform Lambda
    
    Args:
        event: Contains orderId and extractedData
        context: Lambda context
        
    Returns:
        Transformed and enriched data
    """
    logger.info(f"Transform function started for order: {event.get('orderId')}")
    
    try:
        order_id = event.get('orderId')
        extracted_data = event.get('extractedData', {})
        
        if not order_id:
            raise ValueError("Missing orderId")
        
        # Transform customer data
        customer_transformed = transform_customer_data(extracted_data.get('customer', {}))
        
        # Calculate order financials
        order_summary = calculate_order_summary(
            extracted_data.get('rawOrderDetails', {}),
            customer_transformed
        )
        
        # Enrich with analytics metadata
        analytics_data = build_analytics_data(
            extracted_data,
            order_summary,
            customer_transformed
        )
        
        # Calculate customer metrics
        customer_metrics = calculate_customer_metrics(
            customer_transformed,
            extracted_data.get('orderHistory', []),
            order_summary
        )
        
        # Build transformed data response
        transformed_data = {
            'orderId': order_id,
            'transformedAt': datetime.utcnow().isoformat(),
            'customer': customer_transformed,
            'orderSummary': order_summary,
            'customerMetrics': customer_metrics,
            'analytics': analytics_data,
            'products': transform_products(extracted_data.get('products', [])),
            'fraudCheck': extracted_data.get('fraudCheck', {}),
            'dataQuality': assess_data_quality(extracted_data)
        }
        
        logger.info(f"Transformation completed for order {order_id}")
        
        return {
            'statusCode': 200,
            'body': transformed_data
        }
        
    except Exception as e:
        logger.exception(f"Error in transform function: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'orderId': event.get('orderId', 'unknown')
            }
        }


def transform_customer_data(customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleanse and standardize customer data
    
    Args:
        customer: Raw customer data
        
    Returns:
        Transformed customer data
    """
    return {
        'customerId': customer.get('customerId'),
        'name': customer.get('name', '').strip().title(),
        'email': customer.get('email', '').lower().strip(),
        'phone': normalize_phone(customer.get('phone', '')),
        'tier': customer.get('tier', 'Standard'),
        'lifetimeValue': float(customer.get('lifetimeValue', 0)),
        'segment': categorize_customer(customer),
        'address': {
            'street': customer.get('address', {}).get('street', '').strip(),
            'city': customer.get('address', {}).get('city', '').strip().title(),
            'state': customer.get('address', {}).get('state', '').upper(),
            'zipCode': customer.get('address', {}).get('zipCode', '').strip()
        }
    }


def normalize_phone(phone: str) -> str:
    """Normalize phone number format"""
    # Remove all non-numeric characters
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone


def categorize_customer(customer: Dict[str, Any]) -> str:
    """Categorize customer based on attributes"""
    ltv = customer.get('lifetimeValue', 0)
    
    if ltv >= 10000:
        return 'HighValue'
    elif ltv >= 5000:
        return 'MediumValue'
    elif ltv >= 1000:
        return 'Standard'
    else:
        return 'New'


def calculate_order_summary(order_details: Dict[str, Any], customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive order financials
    
    Args:
        order_details: Raw order details
        customer: Transformed customer data
        
    Returns:
        Order summary with all calculations
    """
    # Calculate subtotal
    subtotal = float(order_details.get('totalAmount', 0))
    
    # Apply tier discount
    tier = customer.get('tier', 'Standard')
    discount_rate = TIER_DISCOUNTS.get(tier, 0)
    discount = subtotal * discount_rate
    
    # Calculate tax
    state = customer.get('address', {}).get('state', 'default')
    tax_rate = TAX_RATES.get(state, TAX_RATES['default'])
    tax = (subtotal - discount) * tax_rate
    
    # Calculate shipping
    shipping = calculate_shipping(order_details, customer)
    
    # Calculate total
    total = subtotal - discount + tax + shipping
    
    return {
        'subtotal': round(subtotal, 2),
        'discount': round(discount, 2),
        'discountRate': discount_rate,
        'tax': round(tax, 2),
        'taxRate': tax_rate,
        'shipping': round(shipping, 2),
        'total': round(total, 2),
        'currency': order_details.get('currency', 'USD'),
        'itemCount': len(order_details.get('items', []))
    }


def calculate_shipping(order_details: Dict[str, Any], customer: Dict[str, Any]) -> float:
    """Calculate shipping cost"""
    # Simplified shipping calculation
    base_shipping = 10.0
    
    # Free shipping for high-tier customers
    if customer.get('tier') in ['Platinum', 'Gold']:
        return 0.0
    
    # Weight-based shipping (simplified)
    items = order_details.get('items', [])
    total_weight = sum(item.get('weight', 1) for item in items)
    
    if total_weight > 10:
        base_shipping += (total_weight - 10) * 0.5
    
    return round(base_shipping, 2)


def calculate_customer_metrics(customer: Dict[str, Any], 
                               order_history: List[Dict[str, Any]],
                               current_order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate customer-level metrics
    
    Args:
        customer: Customer data
        order_history: Past orders
        current_order: Current order summary
        
    Returns:
        Customer metrics
    """
    # Calculate historical metrics
    order_count = len(order_history) + 1  # Include current
    total_spent = sum(order.get('totalAmount', 0) for order in order_history)
    total_spent += current_order.get('total', 0)
    
    avg_order_value = total_spent / order_count if order_count > 0 else 0
    
    return {
        'orderCount': order_count,
        'totalSpent': round(total_spent, 2),
        'averageOrderValue': round(avg_order_value, 2),
        'lifetimeValue': customer.get('lifetimeValue', 0),
        'customerSegment': customer.get('segment', 'Unknown'),
        'tier': customer.get('tier', 'Standard')
    }


def transform_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform product data"""
    transformed = []
    
    for product in products:
        transformed.append({
            'productId': product.get('productId'),
            'name': product.get('name', '').strip(),
            'category': product.get('category', 'General'),
            'quantity': product.get('quantity', 1),
            'unitPrice': float(product.get('unitPrice', 0)),
            'totalPrice': float(product.get('unitPrice', 0)) * product.get('quantity', 1),
            'inStock': product.get('inStock', True),
            'supplier': product.get('supplier', 'Unknown')
        })
    
    return transformed


def build_analytics_data(extracted: Dict[str, Any],
                        order_summary: Dict[str, Any],
                        customer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build analytics metadata
    
    Args:
        extracted: Extracted data
        order_summary: Order summary
        customer: Customer data
        
    Returns:
        Analytics metadata
    """
    raw_order = extracted.get('rawOrderDetails', {})
    products = extracted.get('products', [])
    
    # Extract categories
    categories = list(set(p.get('category', 'General') for p in products))
    
    # Determine channel
    channel = raw_order.get('channel', 'Web')
    
    # Geographic region
    state = customer.get('address', {}).get('state', 'Unknown')
    region = get_region_from_state(state)
    
    return {
        'productCategories': categories,
        'region': region,
        'state': state,
        'channel': channel,
        'orderValue': order_summary.get('total', 0),
        'isPremiumCustomer': customer.get('tier') in ['Platinum', 'Gold'],
        'fraudRisk': extracted.get('fraudCheck', {}).get('status', 'UNKNOWN'),
        'processingDate': datetime.utcnow().strftime('%Y-%m-%d'),
        'processingHour': datetime.utcnow().hour
    }


def get_region_from_state(state: str) -> str:
    """Map state to region"""
    regions = {
        'Northeast': ['NY', 'PA', 'NJ', 'CT', 'MA', 'VT', 'NH', 'ME', 'RI'],
        'Southeast': ['FL', 'GA', 'NC', 'SC', 'VA', 'WV', 'AL', 'MS', 'TN', 'KY'],
        'Midwest': ['IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'MN', 'MO', 'ND', 'SD', 'NE', 'KS'],
        'Southwest': ['TX', 'OK', 'AR', 'LA', 'AZ', 'NM'],
        'West': ['CA', 'OR', 'WA', 'NV', 'ID', 'MT', 'WY', 'CO', 'UT'],
    }
    
    for region, states in regions.items():
        if state in states:
            return region
    
    return 'Unknown'


def assess_data_quality(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess data quality metrics
    
    Args:
        extracted: Extracted data
        
    Returns:
        Data quality assessment
    """
    issues = []
    completeness = 100.0
    
    customer = extracted.get('customer', {})
    
    # Check for missing customer data
    if not customer.get('email'):
        issues.append('Missing customer email')
        completeness -= 10
    
    if not customer.get('phone'):
        issues.append('Missing customer phone')
        completeness -= 5
    
    if not customer.get('address', {}).get('state'):
        issues.append('Missing state information')
        completeness -= 10
    
    # Check product data
    products = extracted.get('products', [])
    if not products:
        issues.append('No products in order')
        completeness -= 20
    
    return {
        'completeness': max(0, completeness),
        'issues': issues,
        'isValid': completeness >= 80,
        'assessedAt': datetime.utcnow().isoformat()
    }

#!/usr/bin/env python3
"""
Seed sample data into DynamoDB for testing
Creates realistic test data for all 3 DynamoDB tables:

1. CUSTOMERS_TABLE: Customer profiles with tiers (Platinum, Gold, Silver, Standard)
2. ORDERS_TABLE: Historical order data for testing order history queries
3. EXECUTIONS_TABLE: Execution tracking records for idempotency testing

Usage:
    python seed_sample_data.py

Note: Update table names below if your Terraform deployment uses different names.
"""
import boto3
from datetime import datetime, timedelta
import random
import uuid

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

# Table names (update with your actual table names from Terraform outputs)
CUSTOMERS_TABLE = 'ecommerce-order-processing-dev-customers'
ORDERS_TABLE = 'ecommerce-order-processing-dev-orders'
EXECUTIONS_TABLE = 'ecommerce-order-processing-dev-executions'

def seed_customers():
    """Create sample customer records with diverse profiles"""
    table = dynamodb.Table(CUSTOMERS_TABLE)
    
    customers = [
        # Platinum tier customers (high value)
        {
            'customerId': 'CUST-123456',
            'name': 'Jane Smith',
            'email': 'jane.smith@example.com',
            'phone': '(555) 987-6543',
            'tier': 'Platinum',
            'lifetimeValue': 15000.00,
            'registrationDate': '2023-06-20T14:30:00Z',
            'address': {
                'street': '456 Tech Avenue',
                'city': 'San Francisco',
                'state': 'CA',
                'zipCode': '94105'
            }
        },
        {
            'customerId': 'CUST-999888',
            'name': 'Robert Johnson',
            'email': 'robert.j@example.com',
            'phone': '(555) 111-2222',
            'tier': 'Platinum',
            'lifetimeValue': 22000.00,
            'registrationDate': '2022-03-10T09:00:00Z',
            'address': {
                'street': '789 Executive Blvd',
                'city': 'Seattle',
                'state': 'WA',
                'zipCode': '98101'
            }
        },
        
        # Gold tier customers (medium value)
        {
            'customerId': 'CUST-567890',
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '(555) 123-4567',
            'tier': 'Gold',
            'lifetimeValue': 5000.00,
            'registrationDate': '2024-01-15T10:00:00Z',
            'address': {
                'street': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'zipCode': '10001'
            }
        },
        {
            'customerId': 'CUST-445566',
            'name': 'Maria Garcia',
            'email': 'maria.garcia@example.com',
            'phone': '(555) 334-5566',
            'tier': 'Gold',
            'lifetimeValue': 7500.00,
            'registrationDate': '2024-05-01T12:00:00Z',
            'address': {
                'street': '321 Oak Street',
                'city': 'Austin',
                'state': 'TX',
                'zipCode': '78701'
            }
        },
        
        # Silver tier customers
        {
            'customerId': 'CUST-778899',
            'name': 'David Lee',
            'email': 'david.lee@example.com',
            'phone': '(555) 778-8990',
            'tier': 'Silver',
            'lifetimeValue': 2500.00,
            'registrationDate': '2024-08-15T14:00:00Z',
            'address': {
                'street': '555 Park Ave',
                'city': 'Chicago',
                'state': 'IL',
                'zipCode': '60601'
            }
        },
        
        # Standard tier customers (new/low value)
        {
            'customerId': 'CUST-TEST-001',
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '(555) 000-0000',
            'tier': 'Standard',
            'lifetimeValue': 500.00,
            'registrationDate': '2026-01-01T00:00:00Z',
            'address': {
                'street': '123 Test St',
                'city': 'Boston',
                'state': 'MA',
                'zipCode': '02101'
            }
        },
        {
            'customerId': 'CUST-112233',
            'name': 'Sarah Wilson',
            'email': 'sarah.w@example.com',
            'phone': '(555) 112-2334',
            'tier': 'Standard',
            'lifetimeValue': 150.00,
            'registrationDate': '2025-12-01T10:00:00Z',
            'address': {
                'street': '999 First St',
                'city': 'Miami',
                'state': 'FL',
                'zipCode': '33101'
            }
        },
        
        # New customer (for fraud testing)
        {
            'customerId': 'NEW-CUST-001',
            'name': 'New Customer Test',
            'email': 'newcustomer@example.com',
            'phone': '(555) 999-9999',
            'tier': 'Standard',
            'lifetimeValue': 0.00,
            'registrationDate': '2026-04-01T00:00:00Z',
            'address': {
                'street': '100 New St',
                'city': 'Phoenix',
                'state': 'AZ',
                'zipCode': '85001'
            }
        }
    ]
    
    print("Seeding customers...")
    for customer in customers:
        table.put_item(Item=customer)
        print(f"  ✓ Created customer: {customer['customerId']} - {customer['name']} ({customer['tier']})")
    
    print(f"✓ Seeded {len(customers)} customers")

def seed_orders():
    """Create sample order history with diverse statuses"""
    table = dynamodb.Table(ORDERS_TABLE)
    
    # Generate some historical orders
    orders = []
    
    # Orders for CUST-567890 (John Doe - Gold tier)
    base_date = datetime.now() - timedelta(days=90)
    for i in range(5):
        order_date = base_date + timedelta(days=i*15)
        orders.append({
            'orderId': f'ORD-2026-{str(i+1).zfill(6)}',
            'customerId': 'CUST-567890',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(100, 500), 2),
            'status': 'Delivered',
            'itemCount': random.randint(1, 5)
        })
    
    # Orders for CUST-123456 (Jane Smith - Platinum tier)
    for i in range(10):
        order_date = base_date + timedelta(days=i*9)
        orders.append({
            'orderId': f'ORD-2026-{str(i+100).zfill(6)}',
            'customerId': 'CUST-123456',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(200, 2000), 2),
            'status': 'Delivered',
            'itemCount': random.randint(1, 8)
        })
    
    # Orders for CUST-999888 (Robert Johnson - Platinum tier)
    for i in range(8):
        order_date = base_date + timedelta(days=i*11)
        orders.append({
            'orderId': f'ORD-2026-{str(i+200).zfill(6)}',
            'customerId': 'CUST-999888',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(500, 3000), 2),
            'status': random.choice(['Delivered', 'Shipped', 'Processing']),
            'itemCount': random.randint(2, 10)
        })
    
    # Orders for CUST-445566 (Maria Garcia - Gold tier)
    for i in range(6):
        order_date = base_date + timedelta(days=i*14)
        orders.append({
            'orderId': f'ORD-2026-{str(i+300).zfill(6)}',
            'customerId': 'CUST-445566',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(150, 800), 2),
            'status': 'Delivered',
            'itemCount': random.randint(1, 6)
        })
    
    # Orders for CUST-778899 (David Lee - Silver tier)
    for i in range(4):
        order_date = base_date + timedelta(days=i*20)
        orders.append({
            'orderId': f'ORD-2026-{str(i+400).zfill(6)}',
            'customerId': 'CUST-778899',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(80, 400), 2),
            'status': 'Delivered',
            'itemCount': random.randint(1, 3)
        })
    
    # Orders for CUST-112233 (Sarah Wilson - Standard tier)
    for i in range(2):
        order_date = base_date + timedelta(days=i*30)
        orders.append({
            'orderId': f'ORD-2026-{str(i+500).zfill(6)}',
            'customerId': 'CUST-112233',
            'orderDate': order_date.isoformat(),
            'totalAmount': round(random.uniform(50, 150), 2),
            'status': 'Delivered',
            'itemCount': random.randint(1, 2)
        })
    
    # Recent order for CUST-TEST-001 (for testing)
    orders.append({
        'orderId': 'ORD-2026-TEST001',
        'customerId': 'CUST-TEST-001',
        'orderDate': (datetime.now() - timedelta(days=1)).isoformat(),
        'totalAmount': 299.99,
        'status': 'Processing',
        'itemCount': 2
    })
    
    print("\nSeeding orders...")
    for order in orders:
        table.put_item(Item=order)
        print(f"  ✓ Created order: {order['orderId']} for {order['customerId']} (${order['totalAmount']})")
    
    print(f"✓ Seeded {len(orders)} orders")


def seed_executions():
    """Create sample execution tracking records for idempotency testing"""
    table = dynamodb.Table(EXECUTIONS_TABLE)
    
    # Calculate TTL (7 days from now)
    ttl_timestamp = int((datetime.now() + timedelta(days=7)).timestamp())
    
    executions = [
        # Recent executions (last 24 hours)
        {
            'orderId': 'ORD-2026-000001',
            'eventId': str(uuid.uuid4()),
            'executionArn': f'arn:aws:states:us-east-1:123456789012:execution:order-processing:ORD-2026-000001-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'ttl': ttl_timestamp
        },
        {
            'orderId': 'ORD-2026-000100',
            'eventId': str(uuid.uuid4()),
            'executionArn': f'arn:aws:states:us-east-1:123456789012:execution:order-processing:ORD-2026-000100-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
            'ttl': ttl_timestamp
        },
        {
            'orderId': 'ORD-2026-TEST001',
            'eventId': str(uuid.uuid4()),
            'executionArn': f'arn:aws:states:us-east-1:123456789012:execution:order-processing:ORD-2026-TEST001-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'ttl': ttl_timestamp
        },
        # For duplicate event testing
        {
            'orderId': 'ORD-2026-DUP001',
            'eventId': 'duplicate-test-event-001',
            'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:order-processing:ORD-2026-DUP001-20260405100000',
            'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'ttl': ttl_timestamp
        }
    ]
    
    print("\nSeeding execution tracking records...")
    for execution in executions:
        table.put_item(Item=execution)
        print(f"  ✓ Created execution: {execution['orderId']} | Event: {execution['eventId'][:8]}...")
    
    print(f"✓ Seeded {len(executions)} execution records")

def main():
    """Main seeding function"""
    print("\n" + "="*60)
    print("Seeding Sample Data for All 3 DynamoDB Tables")
    print("="*60 + "\n")
    
    try:
        # Seed all 3 tables
        seed_customers()
        seed_orders()
        seed_executions()
        
        print("\n" + "="*60)
        print("✓ Successfully seeded all sample data!")
        print("="*60)
        print("\nSummary:")
        print("  • Customers Table: 8 customers (Platinum, Gold, Silver, Standard)")
        print("  • Orders Table: 35+ historical orders")
        print("  • Executions Table: 4 execution tracking records")
        print("\nReady for testing!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error seeding data: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Verify tables exist in DynamoDB:")
        print(f"     - {CUSTOMERS_TABLE}")
        print(f"     - {ORDERS_TABLE}")
        print(f"     - {EXECUTIONS_TABLE}")
        print("  2. Check AWS credentials are configured (aws configure)")
        print("  3. Ensure you have DynamoDB write permissions")
        print("  4. Update table names in this script if using different names")
        print("")

if __name__ == '__main__':
    main()

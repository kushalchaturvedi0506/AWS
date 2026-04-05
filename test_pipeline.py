#!/usr/bin/env python3
"""
Test script for the order processing pipeline
"""
import json
import boto3
import time
from datetime import datetime

# Initialize AWS clients
events_client = boto3.client('events')
sfn_client = boto3.client('stepfunctions')
logs_client = boto3.client('logs')

# Configuration
EVENT_BUS_NAME = 'ecommerce-order-processing-dev'
STATE_MACHINE_ARN = None  # Will be fetched

def get_state_machine_arn():
    """Get Step Function ARN"""
    response = sfn_client.list_state_machines()
    for sm in response['stateMachines']:
        if 'ecommerce-order-processing' in sm['name']:
            return sm['stateMachineArn']
    return None

def send_test_event():
    """Send a test order event"""
    test_order = {
        'orderId': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'customerId': 'CUST-TEST-001',
        'orderDate': datetime.utcnow().isoformat(),
        'totalAmount': 299.99,
        'currency': 'USD',
        'channel': 'Web',
        'items': [
            {
                'productId': 'PROD-TEST-001',
                'name': 'Test Product',
                'category': 'Electronics',
                'quantity': 1,
                'unitPrice': 299.99,
                'weight': 1.0
            }
        ],
        'shippingAddress': {
            'street': '123 Test St',
            'city': 'Boston',
            'state': 'MA',
            'zipCode': '02101',
            'country': 'US'
        }
    }
    
    print(f"\n{'='*60}")
    print("Sending test order event...")
    print(f"{'='*60}")
    print(f"Order ID: {test_order['orderId']}")
    print(f"Customer ID: {test_order['customerId']}")
    print(f"Amount: ${test_order['totalAmount']}")
    
    response = events_client.put_events(
        Entries=[
            {
                'Source': 'ecommerce.orders',
                'DetailType': 'OrderCreated',
                'Detail': json.dumps(test_order),
                'EventBusName': EVENT_BUS_NAME
            }
        ]
    )
    
    if response['FailedEntryCount'] == 0:
        print("✓ Event sent successfully!")
        return test_order['orderId']
    else:
        print("✗ Failed to send event")
        print(response)
        return None

def wait_for_execution(order_id, timeout=60):
    """Wait for Step Function execution to start"""
    print(f"\nWaiting for execution to start (timeout: {timeout}s)...")
    
    state_machine_arn = get_state_machine_arn()
    if not state_machine_arn:
        print("✗ Could not find state machine")
        return None
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = sfn_client.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=10
        )
        
        for execution in response['executions']:
            if order_id in execution['name']:
                print(f"✓ Found execution: {execution['name']}")
                return execution['executionArn']
        
        time.sleep(2)
    
    print("✗ Execution not found within timeout")
    return None

def monitor_execution(execution_arn, timeout=120):
    """Monitor Step Function execution"""
    print(f"\n{'='*60}")
    print("Monitoring execution...")
    print(f"{'='*60}")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        response = sfn_client.describe_execution(
            executionArn=execution_arn
        )
        
        status = response['status']
        
        if status != last_status:
            print(f"\nStatus: {status}")
            last_status = status
        
        if status == 'SUCCEEDED':
            print("\n✓ Execution completed successfully!")
            output = json.loads(response.get('output', '{}'))
            
            # Print summary
            print(f"\n{'='*60}")
            print("Execution Summary")
            print(f"{'='*60}")
            if 'loadResult' in output:
                load_result = output['loadResult']
                print(f"S3 Location: {load_result.get('s3Location', 'N/A')}")
                print(f"Records Count: {load_result.get('recordsCount', 'N/A')}")
            
            return True
        
        elif status == 'FAILED':
            print("\n✗ Execution failed!")
            print(f"Error: {response.get('error', 'Unknown')}")
            print(f"Cause: {response.get('cause', 'Unknown')}")
            return False
        
        elif status == 'TIMED_OUT':
            print("\n✗ Execution timed out!")
            return False
        
        elif status == 'ABORTED':
            print("\n✗ Execution was aborted!")
            return False
        
        time.sleep(3)
    
    print("\n✗ Monitoring timeout reached")
    return False

def main():
    """Main test function"""
    print(f"\n{'#'*60}")
    print("E-Commerce Order Processing Pipeline - Test Script")
    print(f"{'#'*60}")
    
    # Send test event
    order_id = send_test_event()
    if not order_id:
        return
    
    # Wait for execution to start
    execution_arn = wait_for_execution(order_id)
    if not execution_arn:
        print("\nTest completed with warnings")
        return
    
    # Monitor execution
    success = monitor_execution(execution_arn)
    
    # Print final result
    print(f"\n{'='*60}")
    if success:
        print("✓ TEST PASSED - Pipeline executed successfully!")
    else:
        print("✗ TEST FAILED - Pipeline execution failed")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()

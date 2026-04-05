"""
Lambda Load Function
Loads transformed data to S3 Data Lake in Parquet format
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any
import logging
import io

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS Clients
s3_client = boto3.client('s3')
glue_client = boto3.client('glue')

# Environment variables
DATA_LAKE_BUCKET = os.environ['DATA_LAKE_BUCKET']
GLUE_DATABASE_NAME = os.environ['GLUE_DATABASE_NAME']

# Try to import optional dependencies
try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    logger.warning("Parquet libraries not available, falling back to JSON")
    PARQUET_AVAILABLE = False


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Load Lambda
    
    Args:
        event: Contains orderId and transformedData
        context: Lambda context
        
    Returns:
        Load results with S3 location
    """
    logger.info(f"Load function started for order: {event.get('orderId')}")
    
    try:
        order_id = event.get('orderId')
        transformed_data = event.get('transformedData', {})
        
        if not order_id:
            raise ValueError("Missing orderId")
        
        # Generate partition path
        now = datetime.utcnow()
        partition_path = get_partition_path(now)
        
        # Write to S3 in multiple formats/locations
        s3_locations = []
        
        # 1. Write detailed order data
        order_location = write_order_data(
            order_id,
            transformed_data,
            partition_path
        )
        s3_locations.append(order_location)
        
        # 2. Write customer aggregates
        customer_location = write_customer_data(
            transformed_data.get('customer', {}),
            transformed_data.get('customerMetrics', {}),
            partition_path
        )
        s3_locations.append(customer_location)
        
        # 3. Write analytics data
        analytics_location = write_analytics_data(
            order_id,
            transformed_data.get('analytics', {}),
            transformed_data.get('orderSummary', {}),
            partition_path
        )
        s3_locations.append(analytics_location)
        
        # 4. Update Glue Data Catalog partitions
        update_glue_partitions(now)
        
        logger.info(f"Load completed for order {order_id}")
        
        return {
            'statusCode': 200,
            'body': {
                'orderId': order_id,
                's3Location': order_location,
                'allLocations': s3_locations,
                'recordsCount': len(s3_locations),
                'loadedAt': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.exception(f"Error in load function: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'orderId': event.get('orderId', 'unknown')
            }
        }


def get_partition_path(dt: datetime) -> str:
    """
    Generate S3 partition path based on date
    
    Args:
        dt: Datetime object
        
    Returns:
        Partition path string
    """
    return f"year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/hour={dt.hour:02d}"


def write_order_data(order_id: str, data: Dict[str, Any], partition_path: str) -> str:
    """
    Write order data to S3
    
    Args:
        order_id: Order ID
        data: Transformed order data
        partition_path: S3 partition path
        
    Returns:
        S3 location
    """
    # Prepare order record
    order_record = {
        'order_id': order_id,
        'customer_id': data.get('customer', {}).get('customerId'),
        'customer_name': data.get('customer', {}).get('name'),
        'customer_email': data.get('customer', {}).get('email'),
        'customer_tier': data.get('customer', {}).get('tier'),
        'subtotal': data.get('orderSummary', {}).get('subtotal'),
        'discount': data.get('orderSummary', {}).get('discount'),
        'tax': data.get('orderSummary', {}).get('tax'),
        'shipping': data.get('orderSummary', {}).get('shipping'),
        'total': data.get('orderSummary', {}).get('total'),
        'currency': data.get('orderSummary', {}).get('currency', 'USD'),
        'item_count': data.get('orderSummary', {}).get('itemCount'),
        'fraud_status': data.get('fraudCheck', {}).get('status'),
        'fraud_score': data.get('fraudCheck', {}).get('score'),
        'data_quality_score': data.get('dataQuality', {}).get('completeness'),
        'processed_at': datetime.utcnow().isoformat(),
        'products': json.dumps(data.get('products', []))
    }
    
    # Write to S3
    s3_key = f"orders/{partition_path}/{order_id}.json"
    
    if PARQUET_AVAILABLE:
        s3_key = f"orders/{partition_path}/{order_id}.parquet"
        return write_parquet(s3_key, [order_record])
    else:
        return write_json(s3_key, order_record)


def write_customer_data(customer: Dict[str, Any], metrics: Dict[str, Any], 
                       partition_path: str) -> str:
    """
    Write customer metrics to S3
    
    Args:
        customer: Customer data
        metrics: Customer metrics
        partition_path: S3 partition path
        
    Returns:
        S3 location
    """
    customer_id = customer.get('customerId', 'unknown')
    
    customer_record = {
        'customer_id': customer_id,
        'name': customer.get('name'),
        'email': customer.get('email'),
        'phone': customer.get('phone'),
        'tier': customer.get('tier'),
        'segment': customer.get('segment'),
        'state': customer.get('address', {}).get('state'),
        'city': customer.get('address', {}).get('city'),
        'order_count': metrics.get('orderCount'),
        'total_spent': metrics.get('totalSpent'),
        'average_order_value': metrics.get('averageOrderValue'),
        'lifetime_value': metrics.get('lifetimeValue'),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    s3_key = f"customers/{partition_path}/{customer_id}.json"
    
    if PARQUET_AVAILABLE:
        s3_key = f"customers/{partition_path}/{customer_id}.parquet"
        return write_parquet(s3_key, [customer_record])
    else:
        return write_json(s3_key, customer_record)


def write_analytics_data(order_id: str, analytics: Dict[str, Any], 
                        order_summary: Dict[str, Any], partition_path: str) -> str:
    """
    Write analytics data to S3
    
    Args:
        order_id: Order ID
        analytics: Analytics metadata
        order_summary: Order summary
        partition_path: S3 partition path
        
    Returns:
        S3 location
    """
    analytics_record = {
        'order_id': order_id,
        'order_value': analytics.get('orderValue'),
        'region': analytics.get('region'),
        'state': analytics.get('state'),
        'channel': analytics.get('channel'),
        'product_categories': ','.join(analytics.get('productCategories', [])),
        'is_premium_customer': analytics.get('isPremiumCustomer'),
        'fraud_risk': analytics.get('fraudRisk'),
        'processing_date': analytics.get('processingDate'),
        'processing_hour': analytics.get('processingHour'),
        'item_count': order_summary.get('itemCount'),
        'tax_amount': order_summary.get('tax'),
        'shipping_amount': order_summary.get('shipping'),
        'discount_amount': order_summary.get('discount'),
        'created_at': datetime.utcnow().isoformat()
    }
    
    s3_key = f"analytics/{partition_path}/{order_id}.json"
    
    if PARQUET_AVAILABLE:
        s3_key = f"analytics/{partition_path}/{order_id}.parquet"
        return write_parquet(s3_key, [analytics_record])
    else:
        return write_json(s3_key, analytics_record)


def write_json(s3_key: str, data: Dict[str, Any]) -> str:
    """
    Write data to S3 as JSON
    
    Args:
        s3_key: S3 key
        data: Data to write
        
    Returns:
        S3 location
    """
    s3_client.put_object(
        Bucket=DATA_LAKE_BUCKET,
        Key=s3_key,
        Body=json.dumps(data, default=str),
        ContentType='application/json',
        ServerSideEncryption='aws:kms'
    )
    
    location = f"s3://{DATA_LAKE_BUCKET}/{s3_key}"
    logger.info(f"Wrote JSON to {location}")
    return location


def write_parquet(s3_key: str, records: list) -> str:
    """
    Write data to S3 as Parquet
    
    Args:
        s3_key: S3 key
        records: List of records
        
    Returns:
        S3 location
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Convert to Parquet
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=DATA_LAKE_BUCKET,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType='application/x-parquet',
            ServerSideEncryption='aws:kms'
        )
        
        location = f"s3://{DATA_LAKE_BUCKET}/{s3_key}"
        logger.info(f"Wrote Parquet to {location}")
        return location
        
    except Exception as e:
        logger.error(f"Error writing Parquet: {str(e)}, falling back to JSON")
        # Fallback to JSON
        json_key = s3_key.replace('.parquet', '.json')
        return write_json(json_key, records[0] if records else {})


def update_glue_partitions(dt: datetime) -> None:
    """
    Update Glue Data Catalog partitions
    
    Args:
        dt: Datetime for partition
    """
    try:
        partition_values = [
            str(dt.year),
            f"{dt.month:02d}",
            f"{dt.day:02d}"
        ]
        
        # Update partitions for each table
        for table_name in ['orders', 'customers', 'analytics']:
            try:
                glue_client.create_partition(
                    DatabaseName=GLUE_DATABASE_NAME,
                    TableName=table_name,
                    PartitionInput={
                        'Values': partition_values,
                        'StorageDescriptor': {
                            'Location': f"s3://{DATA_LAKE_BUCKET}/{table_name}/year={partition_values[0]}/month={partition_values[1]}/day={partition_values[2]}/",
                            'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                            'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                            'SerdeInfo': {
                                'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
                            }
                        }
                    }
                )
                logger.info(f"Created partition for {table_name}: {partition_values}")
            except glue_client.exceptions.AlreadyExistsException:
                logger.debug(f"Partition already exists for {table_name}: {partition_values}")
            except Exception as e:
                logger.warning(f"Error creating partition for {table_name}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error updating Glue partitions: {str(e)}")
        # Don't fail the load if partition update fails

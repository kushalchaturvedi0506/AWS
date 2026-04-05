# Visual Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         E-Commerce Order Processing                       │
│                         Event-Driven ETL Pipeline                         │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Order Events    │
│  (Mobile, Web,   │
│   API, etc.)     │
└────────┬─────────┘
         │
         │ PUT Event
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Amazon EventBridge                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ OrderCreated │  │ OrderUpdated │  │ High Priority│                   │
│  │     Rule     │  │     Rule     │  │     Rule     │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
└─────────┼──────────────────┼──────────────────┼───────────────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
          ┌──────────────────────────────────┐
          │    Lambda Trigger Function       │
          │  • Validate event schema         │
          │  • Check idempotency             │
          │  • Start Step Function           │
          └──────────────┬───────────────────┘
                         │
                         ▼
          ┌──────────────────────────────────┐
          │   AWS Step Functions Workflow    │
          │                                  │
          │   ┌────────────────────────┐    │
          │   │   Extract Stage        │    │
          │   │   Lambda 1             │    │
          │   └──────────┬─────────────┘    │
          │              │                   │
          │              ▼                   │
          │   ┌────────────────────────┐    │
          │   │   Transform Stage      │    │
          │   │   Lambda 2             │    │
          │   └──────────┬─────────────┘    │
          │              │                   │
          │              ▼                   │
          │   ┌────────────────────────┐    │
          │   │   Load Stage           │    │
          │   │   Lambda 3             │    │
          │   └──────────┬─────────────┘    │
          └──────────────┼───────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  DynamoDB    │  │  S3 Data     │  │  Glue Data   │
│  - Orders    │  │  Lake        │  │  Catalog     │
│  - Customers │  │  - Parquet   │  │              │
│  - Tracking  │  │  - Partitions│  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Detailed Data Flow

```
Step 1: EVENT INGESTION
─────────────────────────
Order Event → EventBridge → Event Archive (7 days)
                    ↓
                Route by pattern
                    ↓
            Lambda Trigger
                    ↓
            DynamoDB Check (Idempotency)
                    ↓
    ┌──────────────────────────────┐
    │  Step Function Execution     │
    └──────────────────────────────┘


Step 2: EXTRACT (Lambda 1)
───────────────────────────
Input: { orderId, customerId, orderDetails }
    ↓
┌─────────────────────────────┐
│  Data Sources:              │
│  • DynamoDB: customers      │
│  • DynamoDB: order history  │
│  • External API: fraud check│
└─────────────────────────────┘
    ↓
Output: {
  customer: {...},
  orderHistory: [...],
  products: [...],
  fraudCheck: {...}
}


Step 3: TRANSFORM (Lambda 2)
─────────────────────────────
Input: extractedData
    ↓
┌─────────────────────────────┐
│  Transformations:           │
│  • Cleanse addresses        │
│  • Calculate tax            │
│  • Apply discounts          │
│  • Enrich with metrics      │
│  • Quality assessment       │
└─────────────────────────────┘
    ↓
Output: {
  orderSummary: {...},
  customerMetrics: {...},
  analytics: {...},
  dataQuality: {...}
}


Step 4: LOAD (Lambda 3)
───────────────────────
Input: transformedData
    ↓
┌─────────────────────────────────────┐
│  Write to S3:                       │
│  • orders/year=2026/month=04/...    │
│  • customers/year=2026/month=04/... │
│  • analytics/year=2026/month=04/... │
│                                     │
│  Format: Parquet (Snappy)           │
│  Encryption: KMS                    │
└─────────────────────────────────────┘
    ↓
Update Glue Catalog Partitions
    ↓
Output: {
  s3Location: "s3://...",
  recordsCount: 3
}
```

## Error Handling Flow

```
┌─────────────┐
│   Extract   │
└──────┬──────┘
       │
       ├─ Success ──────────────► Transform
       │
       └─ Error
            ↓
       ┌──────────────┐
       │ Retry 3x     │
       │ Exponential  │
       │ Backoff      │
       └──────┬───────┘
              │
              ├─ Success ──────► Transform
              │
              └─ All Failed
                   ↓
              ┌──────────┐
              │ Send SNS │
              │  Alert   │
              └──────────┘
                   ↓
              ┌──────────┐
              │   Fail   │
              │  State   │
              └──────────┘
```

## Monitoring & Observability

```
┌────────────────────────────────────────────────────────┐
│                 CloudWatch Monitoring                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │   Metrics    │  │     Logs     │  │   Alarms     ││
│  ├──────────────┤  ├──────────────┤  ├──────────────┤│
│  │ • Invocations│  │ /aws/lambda/ │  │ • Errors > 5 ││
│  │ • Errors     │  │   trigger    │  │ • Throttles  ││
│  │ • Duration   │  │   extract    │  │ • Duration   ││
│  │ • Throttles  │  │   transform  │  │ • DLQ msgs   ││
│  │              │  │   load       │  │              ││
│  │ • SF Success │  │              │  │ → SNS Alert  ││
│  │ • SF Failed  │  │ /aws/sfn/    │  │              ││
│  └──────────────┘  └──────────────┘  └──────────────┘│
└────────────────────────────────────────────────────────┘
                            ↓
                    ┌──────────────┐
                    │  Dashboard   │
                    └──────────────┘


┌────────────────────────────────────────────────────────┐
│                   AWS X-Ray Tracing                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  EventBridge → Lambda → Step Functions                │
│                  ↓         ↓                           │
│            DynamoDB    Lambda Extract                  │
│                        Lambda Transform                │
│                        Lambda Load → S3                │
│                                                        │
│  Service Map | Latency Analysis | Error Traces        │
└────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Security Layers                      │
└────────────────────────────────────────────────────────┘

Layer 1: IAM Roles & Policies
─────────────────────────────
Lambda Trigger    → Start Step Function, DynamoDB Put/Get
Lambda Extract    → DynamoDB Read, Secrets Manager
Lambda Transform  → CloudWatch Logs
Lambda Load       → S3 Write, KMS Encrypt, Glue Update
Step Functions    → Invoke Lambda, SNS Publish


Layer 2: Encryption
───────────────────
At Rest:
  • S3: SSE-KMS (Customer Managed Key)
  • DynamoDB: Encryption Enabled
  • Lambda: Environment Variables Encrypted

In Transit:
  • TLS 1.2+ for all AWS API calls
  • VPC Endpoints (optional)


Layer 3: Network Security
──────────────────────────
Optional VPC Configuration:
  ┌─────────────────────────────┐
  │  VPC                        │
  │  ┌───────────────────────┐  │
  │  │ Private Subnets       │  │
  │  │ • Lambda Functions    │  │
  │  │ • Security Groups     │  │
  │  └───────────────────────┘  │
  │           ↓                 │
  │  ┌───────────────────────┐  │
  │  │ VPC Endpoints         │  │
  │  │ • S3                  │  │
  │  │ • DynamoDB            │  │
  │  │ • Secrets Manager     │  │
  │  └───────────────────────┘  │
  └─────────────────────────────┘


Layer 4: Access Control
───────────────────────
• Least Privilege IAM
• S3 Bucket Policies (Block Public Access)
• Resource-based Policies
• KMS Key Policies
```

## Scalability Model

```
┌────────────────────────────────────────────────────────┐
│               Throughput Capabilities                  │
└────────────────────────────────────────────────────────┘

EventBridge:    10,000+ events/second
                    ↓
Lambda Trigger: 1,000 concurrent (configurable)
                    ↓
Step Functions: 4,000+ executions/second
                    ↓
Lambda Extract: 100 reserved concurrency
Lambda Transform: 100 reserved concurrency
Lambda Load:    100 reserved concurrency
                    ↓
S3:             5,500+ PUT/second per prefix
DynamoDB:       Unlimited (on-demand)


Auto-Scaling:
─────────────
┌──────────────┐
│ Event Rate   │
│   Increases  │
└──────┬───────┘
       │
       ▼
Lambda scales automatically
       │
       ▼
Step Functions queue executions
       │
       ▼
S3 handles concurrent writes
       │
       ▼
DynamoDB auto-scales capacity
```

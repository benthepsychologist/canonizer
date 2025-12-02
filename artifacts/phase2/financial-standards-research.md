# Financial Standards Research for Stripe Schemas

## Overview

Research into financial standards relevant to transforming Stripe billing data into canonical formats.

## Stripe API Object Structures

### Customer Object

Key fields from [Stripe Customer API](https://docs.stripe.com/api/customers/object):

- `id` (string) - Unique identifier
- `email` (string, nullable) - Customer email
- `name` (string, nullable) - Full name or business name
- `phone` (string, nullable) - Phone number
- `address` (object) - Address with line1, line2, city, state, postal_code, country
- `shipping` (object) - Shipping address
- `metadata` (object) - Custom key-value pairs
- `created` (timestamp) - Creation time
- `balance` (integer) - Current balance in cents
- `currency` (string) - Default currency
- `delinquent` (boolean) - Delinquency status

### Invoice Object

Key fields from [Stripe Invoice API](https://docs.stripe.com/api/invoices/object):

- `id` (string) - Unique identifier
- `number` (string) - Invoice number
- `customer` (string) - Customer ID
- `status` (enum) - draft, open, paid, uncollectible, void
- `amount_due` (integer) - Amount in cents
- `amount_paid` (integer) - Amount paid
- `currency` (string) - Three-letter ISO code
- `due_date` (timestamp) - Due date
- `lines` (object) - Line items array
- `hosted_invoice_url` (string) - Payment page URL
- `invoice_pdf` (string) - PDF download URL
- `created` (timestamp) - Creation time
- `metadata` (object) - Custom key-value pairs

### PaymentIntent Object

Key fields from [Stripe PaymentIntent API](https://docs.stripe.com/api/payment_intents/object):

- `id` (string) - Unique identifier
- `amount` (integer) - Amount in cents
- `amount_received` (integer) - Amount collected
- `currency` (string) - Three-letter ISO code
- `customer` (string) - Customer ID
- `status` (string) - requires_payment_method, requires_confirmation, requires_action, processing, requires_capture, canceled, succeeded
- `payment_method` (string) - Payment method ID
- `latest_charge` (string) - Latest charge ID
- `description` (string) - Description
- `created` (timestamp) - Creation time
- `metadata` (object) - Custom key-value pairs

### Refund Object

Key fields from [Stripe Refund API](https://docs.stripe.com/api/refunds/object):

- `id` (string) - Unique identifier
- `amount` (integer) - Refund amount in cents
- `charge` (string) - Charge ID being refunded
- `payment_intent` (string) - PaymentIntent ID
- `currency` (string) - Three-letter ISO code
- `status` (string) - pending, requires_action, succeeded, failed, canceled
- `reason` (enum) - duplicate, fraudulent, requested_by_customer
- `failure_reason` (string) - Reason for failure
- `created` (timestamp) - Creation time
- `metadata` (object) - Custom key-value pairs

## Relevant Standards

### ISO 20022

ISO 20022 is the international standard for financial messaging. Relevant concepts:

- **Party identification** - Customer naming conventions
- **Amount representation** - Currency + amount as integer (smallest unit)
- **Date/time** - ISO 8601 timestamps
- **Status codes** - Standardized payment status lifecycle

### OpenFinance/Open Banking

Common patterns:

- **Account identifiers** - Unique customer/account IDs
- **Transaction status** - pending, completed, failed, reversed
- **Amount handling** - Separate amount and currency fields
- **Timestamps** - ISO 8601 format

## Canonical Schema Design Decisions

### Customer Canonical

Map Stripe customer to simplified customer with:
- `customer_id` - External identifier
- `email`, `name`, `phone` - Contact info
- `address` - Standardized address object
- `status` - active/inactive based on delinquent flag
- `created_at`, `updated_at` - ISO timestamps

### Invoice Canonical

Map Stripe invoice to simplified billing document:
- `invoice_id` - External identifier
- `invoice_number` - Human-readable number
- `customer_id` - Reference to customer
- `status` - Normalized status enum
- `amount_due`, `amount_paid` - In smallest currency unit
- `currency` - ISO 4217 code
- `due_date`, `created_at` - ISO timestamps
- `line_items` - Array of line item objects

### Payment Canonical

Map Stripe payment_intent to payment record:
- `payment_id` - External identifier
- `customer_id` - Reference to customer
- `amount`, `currency` - Payment amount
- `status` - Normalized status enum
- `payment_method_type` - card, bank_transfer, etc.
- `created_at` - ISO timestamp

### Refund Canonical

Map Stripe refund to refund record:
- `refund_id` - External identifier
- `payment_id` - Reference to original payment
- `amount`, `currency` - Refund amount
- `status` - Normalized status enum
- `reason` - Refund reason
- `created_at` - ISO timestamp

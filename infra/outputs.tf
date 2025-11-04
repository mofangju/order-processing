output "sqs_queue_url" {
  description = "URL of the SQS order queue"
  value       = aws_sqs_queue.order_queue.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS order queue"
  value       = aws_sqs_queue.order_queue.arn
}

output "sqs_dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.dlq.url
}

output "sqs_dlq_arn" {
  description = "ARN of the SQS dead letter queue"
  value       = aws_sqs_queue.dlq.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB orders table"
  value       = aws_dynamodb_table.orders.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB orders table"
  value       = aws_dynamodb_table.orders.arn
}


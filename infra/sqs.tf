# SQS Queue for order processing
resource "aws_sqs_queue" "order_queue" {
  name                        = "${local.name_prefix}-order-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = var.sqs_visibility_timeout_seconds
  message_retention_seconds   = var.sqs_message_retention_seconds

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-order-queue"
    }
  )
}

# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name_prefix}-order-queue-dlq.fifo"
  fifo_queue                = true
  message_retention_seconds = var.dlq_message_retention_seconds

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-order-queue-dlq"
    }
  )
}

# Redrive policy to send failed messages to DLQ
resource "aws_sqs_queue_redrive_policy" "order_queue" {
  queue_url = aws_sqs_queue.order_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })
}


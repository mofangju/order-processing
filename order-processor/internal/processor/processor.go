package processor

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog/log"
)

const (
	// Default AWS region for LocalStack or development
	defaultRegion = "us-east-1"

	// SQS polling configuration
	maxMessagesPerPoll = 5
	waitTimeSeconds    = 10
	visibilityTimeout  = 60

	// Retry configuration
	pollRetryDelay = 2 * time.Second

	// Metrics server configuration
	metricsPort   = ":9090"
	metricsPath   = "/metrics"
	healthPath    = "/health"
	readinessPath = "/ready"

	// Order status
	orderStatusProcessed = "PROCESSED"

	// Environment variable names
	envAWSEndpoint  = "AWS_ENDPOINT_URL"
	envSQSQueueURL  = "SQS_QUEUE_URL"
	envDDBTable     = "DDB_TABLE"
	envEnvironment  = "ENVIRONMENT"
	envAWSRegion    = "AWS_REGION"
	envAWSAccessKey = "AWS_ACCESS_KEY_ID"
	envAWSSecretKey = "AWS_SECRET_ACCESS_KEY"

	// Default environment for metrics
	defaultEnvironment = "local"
)

var (
	// ErrMissingQueueURL is returned when SQS_QUEUE_URL is not set
	ErrMissingQueueURL = errors.New("SQS_QUEUE_URL environment variable is required")
	// ErrMissingTableName is returned when DDB_TABLE is not set
	ErrMissingTableName = errors.New("DDB_TABLE environment variable is required")
)

type Order struct {
	OrderID string `json:"order_id" dynamodbav:"order_id"`
	UserID  string `json:"user_id" dynamodbav:"user_id"`
	Amount  int    `json:"amount" dynamodbav:"amount"`
	Status  string `json:"status" dynamodbav:"status"`
}

type sqsClientI interface {
	ReceiveMessage(context.Context, *sqs.ReceiveMessageInput, ...func(*sqs.Options)) (*sqs.ReceiveMessageOutput, error)
	DeleteMessage(context.Context, *sqs.DeleteMessageInput, ...func(*sqs.Options)) (*sqs.DeleteMessageOutput, error)
}

type ddbClientI interface {
	PutItem(context.Context, *dynamodb.PutItemInput, ...func(*dynamodb.Options)) (*dynamodb.PutItemOutput, error)
}

type Processor struct {
	sqsClient       sqsClientI
	ddbClient       ddbClientI
	queueURL        string
	tableName       string
	ordersProcessed *prometheus.CounterVec
	environment     string
	metricsServer   *http.Server
}

func NewProcessor(ctx context.Context) (*Processor, error) {
	queueURL := os.Getenv(envSQSQueueURL)
	if queueURL == "" {
		return nil, ErrMissingQueueURL
	}

	tableName := os.Getenv(envDDBTable)
	if tableName == "" {
		return nil, ErrMissingTableName
	}

	environment := os.Getenv(envEnvironment)
	if environment == "" {
		environment = defaultEnvironment
	}

	endpoint := os.Getenv(envAWSEndpoint)
	region := os.Getenv(envAWSRegion)
	if region == "" {
		region = defaultRegion
	}

	// Get credentials - use static credentials for LocalStack, default chain for production
	accessKey := os.Getenv("AWS_ACCESS_KEY_ID")
	secretKey := os.Getenv("AWS_SECRET_ACCESS_KEY")

	// If endpoint is set (LocalStack), always use static credentials
	// Default to "test"/"test" if not explicitly provided
	var credsProvider aws.CredentialsProvider
	if endpoint != "" {
		if accessKey == "" {
			accessKey = "test" // Default for LocalStack
		}
		if secretKey == "" {
			secretKey = "test" // Default for LocalStack
		}
		credsProvider = credentials.StaticCredentialsProvider{
			Value: aws.Credentials{
				AccessKeyID:     accessKey,
				SecretAccessKey: secretKey,
				Source:          "static",
			},
		}
	} else if accessKey != "" && secretKey != "" {
		// Explicit credentials provided for non-LocalStack (dev/staging)
		credsProvider = credentials.StaticCredentialsProvider{
			Value: aws.Credentials{
				AccessKeyID:     accessKey,
				SecretAccessKey: secretKey,
				Source:          "env",
			},
		}
	}

	// Load AWS config
	cfgOpts := []func(*config.LoadOptions) error{
		config.WithRegion(region),
	}

	// Only set credentials if we have static credentials
	// Otherwise, use default credential chain (IAM roles, etc.)
	if credsProvider != nil {
		cfgOpts = append(cfgOpts, config.WithCredentialsProvider(credsProvider))
	}

	cfg, err := config.LoadDefaultConfig(ctx, cfgOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	// Set custom endpoint for LocalStack using service-specific options
	var sqsClient *sqs.Client
	var ddbClient *dynamodb.Client
	if endpoint != "" {
		// Use BaseEndpoint option for service-specific endpoint resolution
		sqsClient = sqs.NewFromConfig(cfg, func(o *sqs.Options) {
			o.BaseEndpoint = aws.String(endpoint)
		})
		ddbClient = dynamodb.NewFromConfig(cfg, func(o *dynamodb.Options) {
			o.BaseEndpoint = aws.String(endpoint)
		})
	} else {
		sqsClient = sqs.NewFromConfig(cfg)
		ddbClient = dynamodb.NewFromConfig(cfg)
	}

	ordersProcessed := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "orders_processed_total",
			Help: "Total number of orders processed",
		},
		[]string{"status", "env"},
	)
	prometheus.MustRegister(ordersProcessed)

	metricsServer := &http.Server{
		Addr:    metricsPort,
		Handler: http.DefaultServeMux,
	}

	http.Handle(metricsPath, promhttp.Handler())

	// Health check endpoint
	http.HandleFunc(healthPath, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		if _, err := w.Write([]byte(`{"status":"healthy"}`)); err != nil {
			log.Error().Err(err).Msg("failed to write health check response")
		}
	})

	// Readiness check endpoint
	http.HandleFunc(readinessPath, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// Check if required services are configured
		if queueURL == "" || tableName == "" {
			w.WriteHeader(http.StatusServiceUnavailable)
			if _, err := w.Write([]byte(`{"status":"not ready","reason":"missing configuration"}`)); err != nil {
				log.Error().Err(err).Msg("failed to write readiness check response")
			}
			return
		}
		w.WriteHeader(http.StatusOK)
		if _, err := w.Write([]byte(`{"status":"ready"}`)); err != nil {
			log.Error().Err(err).Msg("failed to write readiness check response")
		}
	})

	go func() {
		log.Info().
			Str("port", metricsPort).
			Str("metrics_path", metricsPath).
			Str("health_path", healthPath).
			Str("readiness_path", readinessPath).
			Msg("starting HTTP server for metrics and health checks")
		if err := metricsServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error().Err(err).Msg("HTTP server failed")
		}
	}()

	return &Processor{
		sqsClient:       sqsClient,
		ddbClient:       ddbClient,
		queueURL:        queueURL,
		tableName:       tableName,
		ordersProcessed: ordersProcessed,
		environment:     environment,
		metricsServer:   metricsServer,
	}, nil
}

func (p *Processor) Start(ctx context.Context) error {
	defer p.shutdownMetricsServer()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			if err := p.pollAndProcess(ctx); err != nil {
				log.Error().Err(err).Msg("poll failed")
				select {
				case <-ctx.Done():
					return ctx.Err()
				case <-time.After(pollRetryDelay):
					// Continue polling after delay
				}
			}
		}
	}
}

func (p *Processor) shutdownMetricsServer() {
	if p.metricsServer != nil {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := p.metricsServer.Shutdown(shutdownCtx); err != nil {
			log.Error().Err(err).Msg("error shutting down metrics server")
		} else {
			log.Info().Msg("metrics server shut down gracefully")
		}
	}
}

func (p *Processor) pollAndProcess(ctx context.Context) error {
	out, err := p.sqsClient.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
		QueueUrl:            &p.queueURL,
		MaxNumberOfMessages: int32(maxMessagesPerPoll),
		WaitTimeSeconds:     int32(waitTimeSeconds),
		VisibilityTimeout:   int32(visibilityTimeout),
	})
	if err != nil {
		return fmt.Errorf("receive message: %w", err)
	}

	if len(out.Messages) == 0 {
		return nil
	}

	for _, msg := range out.Messages {
		msgID := "unknown"
		if msg.MessageId != nil {
			msgID = *msg.MessageId
		}

		if err := p.handleMessage(ctx, msg); err != nil {
			p.ordersProcessed.WithLabelValues("error", p.environment).Inc()
			log.Error().
				Str("msg_id", msgID).
				Err(err).
				Msg("failed to process message - message will be retried or sent to DLQ")
			continue
		}

		if err := p.deleteMessage(ctx, msg); err != nil {
			log.Error().
				Str("msg_id", msgID).
				Err(err).
				Msg("failed to delete message from queue - message may be reprocessed")
			// Continue processing other messages even if deletion fails
			// The message will become visible again after visibility timeout
		}
	}

	return nil
}

func (p *Processor) deleteMessage(ctx context.Context, msg types.Message) error {
	_, err := p.sqsClient.DeleteMessage(ctx, &sqs.DeleteMessageInput{
		QueueUrl:      &p.queueURL,
		ReceiptHandle: msg.ReceiptHandle,
	})
	if err != nil {
		return fmt.Errorf("delete message: %w", err)
	}
	return nil
}

func (p *Processor) handleMessage(ctx context.Context, msg types.Message) error {
	if msg.Body == nil {
		return fmt.Errorf("message body is nil")
	}

	var order Order
	if err := json.Unmarshal([]byte(*msg.Body), &order); err != nil {
		return fmt.Errorf("invalid JSON: %w", err)
	}

	if order.OrderID == "" {
		return fmt.Errorf("order_id is required")
	}

	order.Status = orderStatusProcessed

	item, err := attributevalue.MarshalMap(order)
	if err != nil {
		return fmt.Errorf("failed to marshal order: %w", err)
	}

	_, err = p.ddbClient.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: &p.tableName,
		Item:      item,
	})
	if err != nil {
		return fmt.Errorf("failed to put item to DynamoDB: %w", err)
	}

	p.ordersProcessed.WithLabelValues("success", p.environment).Inc()
	log.Info().
		Str("order_id", order.OrderID).
		Str("user_id", order.UserID).
		Int("amount", order.Amount).
		Msg("order processed successfully")
	return nil
}

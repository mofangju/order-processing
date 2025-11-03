package processor

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog/log"
)

type Order struct {
	OrderID string `json:"order_id" dynamodbav:"order_id"`
	UserID  string `json:"user_id" dynamodbav:"user_id"`
	Amount  int    `json:"amount" dynamodbav:"amount"`
	Status  string `json:"status" dynamodbav:"status"`
}

// internal/processor/processor.go   (add near the top, after imports)
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
}

func NewProcessor(ctx context.Context) (*Processor, error) {
	endpoint := os.Getenv("AWS_ENDPOINT_URL")
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion("us-east-1"),
		config.WithCredentialsProvider(aws.CredentialsProviderFunc(func(ctx context.Context) (aws.Credentials, error) {
			return aws.Credentials{
				AccessKeyID: "test", SecretAccessKey: "test", Source: "mock",
			}, nil
		})),
	)
	if err != nil {
		return nil, err
	}

	if endpoint != "" {
		cfg.EndpointResolverWithOptions = aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
			return aws.Endpoint{URL: endpoint}, nil
		})
	}

	sqsClient := sqs.NewFromConfig(cfg)
	ddbClient := dynamodb.NewFromConfig(cfg)

	// Prometheus
	ordersProcessed := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "orders_processed_total",
			Help: "Total number of orders processed",
		},
		[]string{"status", "env"},
	)
	prometheus.MustRegister(ordersProcessed)

	// Start /metrics server
	go func() {
		http.Handle("/metrics", promhttp.Handler())
		log.Info().Msg("Prometheus metrics on :9090/metrics")
		http.ListenAndServe(":9090", nil)
	}()

	return &Processor{
		sqsClient:       sqsClient,
		ddbClient:       ddbClient,
		queueURL:        os.Getenv("SQS_QUEUE_URL"),
		tableName:       os.Getenv("DDB_TABLE"),
		ordersProcessed: ordersProcessed,
	}, nil
}

func (p *Processor) Start(ctx context.Context) error {
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			if err := p.pollAndProcess(ctx); err != nil {
				log.Error().Err(err).Msg("poll failed")
				time.Sleep(2 * time.Second)
			}
		}
	}
}

func (p *Processor) pollAndProcess(ctx context.Context) error {
	out, err := p.sqsClient.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
		QueueUrl:            &p.queueURL,
		MaxNumberOfMessages: 5,
		WaitTimeSeconds:     10,
		VisibilityTimeout:   int32(60),
	})
	if err != nil {
		return fmt.Errorf("receive message: %w", err)
	}

	if len(out.Messages) == 0 {
		return nil
	}

	for _, msg := range out.Messages {
		if err := p.handleMessage(ctx, msg); err != nil {
			p.ordersProcessed.WithLabelValues("error", "local").Inc()
			log.Error().Str("msg_id", *msg.MessageId).Err(err).Msg("failed")
			continue
		}

		_, err = p.sqsClient.DeleteMessage(ctx, &sqs.DeleteMessageInput{
			QueueUrl:      &p.queueURL,
			ReceiptHandle: msg.ReceiptHandle,
		})
		if err != nil {
			log.Error().Err(err).Msg("failed to delete")
		}
	}

	return nil
}

func (p *Processor) handleMessage(ctx context.Context, msg types.Message) error {
	var order Order
	if err := json.Unmarshal([]byte(*msg.Body), &order); err != nil {
		return fmt.Errorf("invalid JSON: %w", err)
	}

	order.Status = "PROCESSED"
	item, err := attributevalue.MarshalMap(order)
	if err != nil {
		return err
	}

	_, err = p.ddbClient.PutItem(ctx, &dynamodb.PutItemInput{
		TableName: &p.tableName,
		Item:      item,
	})
	if err != nil {
		return err
	}

	p.ordersProcessed.WithLabelValues("success", "local").Inc()
	log.Info().Str("order_id", order.OrderID).Msg("order processed")
	return nil
}

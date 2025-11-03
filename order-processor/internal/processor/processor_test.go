// internal/processor/processor_test.go
package processor

import (
	"context"
	"testing"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	dtypes "github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	stypes "github.com/aws/aws-sdk-go-v2/service/sqs/types"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/testutil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// ────────────────────── MOCKS ──────────────────────
type MockSQSClient struct{ mock.Mock }

func (m *MockSQSClient) ReceiveMessage(
	ctx context.Context,
	input *sqs.ReceiveMessageInput,
	opts ...func(*sqs.Options),
) (*sqs.ReceiveMessageOutput, error) {
	args := m.Called(ctx, input)
	return args.Get(0).(*sqs.ReceiveMessageOutput), args.Error(1)
}

func (m *MockSQSClient) DeleteMessage(
	ctx context.Context,
	input *sqs.DeleteMessageInput,
	opts ...func(*sqs.Options),
) (*sqs.DeleteMessageOutput, error) {
	args := m.Called(ctx, input)
	return args.Get(0).(*sqs.DeleteMessageOutput), args.Error(1)
}

type MockDynamoDBClient struct{ mock.Mock }

func (m *MockDynamoDBClient) PutItem(
	ctx context.Context,
	input *dynamodb.PutItemInput,
	opts ...func(*dynamodb.Options),
) (*dynamodb.PutItemOutput, error) {
	args := m.Called(ctx, input)
	return args.Get(0).(*dynamodb.PutItemOutput), args.Error(1)
}

// ────────────────────── TEST HELPER ──────────────────────
func NewCounterVec() *prometheus.CounterVec {
	return prometheus.NewCounterVec(
		prometheus.CounterOpts{Name: "orders_processed_total", Help: "Total processed"},
		[]string{"status", "env"},
	)
}

// ────────────────────── TESTS ──────────────────────
func TestPollAndProcess_Success(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
	}

	// Mock ReceiveMessage → returns one message
	msg := stypes.Message{
		Body:          aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}
	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	// Mock PutItem
	expectedItem := map[string]dtypes.AttributeValue{
		"order_id": &dtypes.AttributeValueMemberS{Value: "o1"},
		"user_id":  &dtypes.AttributeValueMemberS{Value: "u1"},
		"amount":   &dtypes.AttributeValueMemberN{Value: "100"},
		"status":   &dtypes.AttributeValueMemberS{Value: "PROCESSED"},
	}
	mockDDB.On("PutItem", mock.Anything, mock.MatchedBy(func(input *dynamodb.PutItemInput) bool {
		return *input.TableName == "Orders" && assert.Equal(t, expectedItem, input.Item)
	})).Return(&dynamodb.PutItemOutput{}, nil)

	// Mock DeleteMessage
	mockSQS.On("DeleteMessage", mock.Anything, mock.MatchedBy(func(input *sqs.DeleteMessageInput) bool {
		return *input.ReceiptHandle == "r1"
	})).Return(&sqs.DeleteMessageOutput{}, nil)

	// Act: Call pollAndProcess
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	err := proc.pollAndProcess(ctx)

	// Assert
	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	// Metric
	count := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("success", "local"))
	assert.Equal(t, 1.0, count)
}

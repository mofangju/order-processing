// internal/processor/processor_test.go
package processor

import (
	"context"
	"errors"
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
type MockSQSClient struct {
	mock.Mock
}

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

type MockDynamoDBClient struct {
	mock.Mock
}

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
		environment:     "test",
	}

	// Mock ReceiveMessage → returns one message
	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
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
	count := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("success", "test"))
	assert.Equal(t, 1.0, count)
}

func TestPollAndProcess_EmptyQueue(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{}}, nil)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)
}

func TestPollAndProcess_MultipleMessages(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg1 := stypes.Message{
		MessageId:     aws.String("msg-1"),
		Body:          aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}
	msg2 := stypes.Message{
		MessageId:     aws.String("msg-2"),
		Body:          aws.String(`{"order_id":"o2","user_id":"u2","amount":200}`),
		ReceiptHandle: aws.String("r2"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg1, msg2}}, nil)

	mockDDB.On("PutItem", mock.Anything, mock.MatchedBy(func(input *dynamodb.PutItemInput) bool {
		return *input.TableName == "Orders"
	})).Return(&dynamodb.PutItemOutput{}, nil).Twice()

	mockSQS.On("DeleteMessage", mock.Anything, mock.MatchedBy(func(input *sqs.DeleteMessageInput) bool {
		return *input.ReceiptHandle == "r1" || *input.ReceiptHandle == "r2"
	})).Return(&sqs.DeleteMessageOutput{}, nil).Twice()

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	successCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("success", "test"))
	assert.Equal(t, 2.0, successCount)
}

func TestPollAndProcess_ReceiveMessageError(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	expectedErr := errors.New("SQS error")
	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return((*sqs.ReceiveMessageOutput)(nil), expectedErr)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "receive message")
	mockSQS.AssertExpectations(t)
}

func TestPollAndProcess_InvalidJSON(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
		Body:          aws.String(`invalid json`),
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err) // pollAndProcess doesn't return error, just logs it
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	errorCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("error", "test"))
	assert.Equal(t, 1.0, errorCount)
}

func TestPollAndProcess_MissingOrderID(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
		Body:          aws.String(`{"user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	errorCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("error", "test"))
	assert.Equal(t, 1.0, errorCount)
}

func TestPollAndProcess_NilMessageBody(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
		Body:          nil,
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	errorCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("error", "test"))
	assert.Equal(t, 1.0, errorCount)
}

func TestPollAndProcess_DynamoDBError(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
		Body:          aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	ddbErr := errors.New("DynamoDB error")
	mockDDB.On("PutItem", mock.Anything, mock.Anything).
		Return((*dynamodb.PutItemOutput)(nil), ddbErr)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err) // pollAndProcess doesn't return error, just logs it
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	errorCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("error", "test"))
	assert.Equal(t, 1.0, errorCount)
}

func TestPollAndProcess_DeleteMessageError(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     aws.String("msg-123"),
		Body:          aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	mockDDB.On("PutItem", mock.Anything, mock.Anything).
		Return(&dynamodb.PutItemOutput{}, nil)

	deleteErr := errors.New("delete error")
	mockSQS.On("DeleteMessage", mock.Anything, mock.Anything).
		Return((*sqs.DeleteMessageOutput)(nil), deleteErr)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	// pollAndProcess should continue even if delete fails
	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	successCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("success", "test"))
	assert.Equal(t, 1.0, successCount)
}

func TestPollAndProcess_MessageWithoutMessageID(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		MessageId:     nil,
		Body:          aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Return(&sqs.ReceiveMessageOutput{Messages: []stypes.Message{msg}}, nil)

	mockDDB.On("PutItem", mock.Anything, mock.Anything).
		Return(&dynamodb.PutItemOutput{}, nil)

	mockSQS.On("DeleteMessage", mock.Anything, mock.Anything).
		Return(&sqs.DeleteMessageOutput{}, nil)

	ctx := context.Background()
	err := proc.pollAndProcess(ctx)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
	mockDDB.AssertExpectations(t)

	successCount := testutil.ToFloat64(proc.ordersProcessed.WithLabelValues("success", "test"))
	assert.Equal(t, 1.0, successCount)
}

func TestHandleMessage_NilBody(t *testing.T) {
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		ddbClient:       mockDDB,
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		Body: nil,
	}

	ctx := context.Background()
	err := proc.handleMessage(ctx, msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "message body is nil")
}

func TestHandleMessage_InvalidJSON(t *testing.T) {
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		ddbClient:       mockDDB,
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		Body: aws.String(`invalid json`),
	}

	ctx := context.Background()
	err := proc.handleMessage(ctx, msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid JSON")
}

func TestHandleMessage_MissingOrderID(t *testing.T) {
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		ddbClient:       mockDDB,
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		Body: aws.String(`{"user_id":"u1","amount":100}`),
	}

	ctx := context.Background()
	err := proc.handleMessage(ctx, msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "order_id is required")
}

func TestHandleMessage_DynamoDBError(t *testing.T) {
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		ddbClient:       mockDDB,
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
	}

	msg := stypes.Message{
		Body: aws.String(`{"order_id":"o1","user_id":"u1","amount":100}`),
	}

	ddbErr := errors.New("DynamoDB error")
	mockDDB.On("PutItem", mock.Anything, mock.Anything).
		Return((*dynamodb.PutItemOutput)(nil), ddbErr)

	ctx := context.Background()
	err := proc.handleMessage(ctx, msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to put item to DynamoDB")
	mockDDB.AssertExpectations(t)
}

func TestDeleteMessage_Success(t *testing.T) {
	mockSQS := &MockSQSClient{}

	proc := &Processor{
		sqsClient: mockSQS,
		queueURL:  "test-queue",
	}

	msg := stypes.Message{
		ReceiptHandle: aws.String("r1"),
	}

	mockSQS.On("DeleteMessage", mock.Anything, mock.MatchedBy(func(input *sqs.DeleteMessageInput) bool {
		return *input.QueueUrl == "test-queue" && *input.ReceiptHandle == "r1"
	})).Return(&sqs.DeleteMessageOutput{}, nil)

	ctx := context.Background()
	err := proc.deleteMessage(ctx, msg)

	assert.NoError(t, err)
	mockSQS.AssertExpectations(t)
}

func TestDeleteMessage_Error(t *testing.T) {
	mockSQS := &MockSQSClient{}

	proc := &Processor{
		sqsClient: mockSQS,
		queueURL:  "test-queue",
	}

	msg := stypes.Message{
		ReceiptHandle: aws.String("r1"),
	}

	deleteErr := errors.New("delete error")
	mockSQS.On("DeleteMessage", mock.Anything, mock.Anything).
		Return((*sqs.DeleteMessageOutput)(nil), deleteErr)

	ctx := context.Background()
	err := proc.deleteMessage(ctx, msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "delete message")
	mockSQS.AssertExpectations(t)
}

func TestStart_ContextCancellation_Immediate(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
		metricsServer:   nil, // No metrics server for this test
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel before starting

	// Start should return immediately with context.Canceled
	err := proc.Start(ctx)

	assert.Error(t, err)
	assert.Equal(t, context.Canceled, err)
}

func TestStart_ContextCancellation_AfterError(t *testing.T) {
	mockSQS := &MockSQSClient{}
	mockDDB := &MockDynamoDBClient{}

	proc := &Processor{
		sqsClient:       mockSQS,
		ddbClient:       mockDDB,
		queueURL:        "test-queue",
		tableName:       "Orders",
		ordersProcessed: NewCounterVec(),
		environment:     "test",
		metricsServer:   nil, // No metrics server for this test
	}

	// Use a channel to signal when ReceiveMessage is called
	callChan := make(chan struct{}, 1)

	// Return an error to trigger the retry logic which checks context
	pollErr := errors.New("poll error")
	mockSQS.On("ReceiveMessage", mock.Anything, mock.Anything).
		Run(func(args mock.Arguments) {
			callChan <- struct{}{}
		}).
		Return((*sqs.ReceiveMessageOutput)(nil), pollErr).
		Once()

	ctx, cancel := context.WithCancel(context.Background())

	// Start processing in a goroutine
	done := make(chan error, 1)
	go func() {
		done <- proc.Start(ctx)
	}()

	// Wait for ReceiveMessage to be called, then cancel
	// This ensures we test cancellation during the retry delay
	<-callChan
	cancel()

	// Wait for the error
	err := <-done

	assert.Error(t, err)
	assert.Equal(t, context.Canceled, err)
	mockSQS.AssertExpectations(t)
}

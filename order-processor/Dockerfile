# Build
FROM golang:1.24-alpine AS builder
WORKDIR /app

# Install git (required for go mod download)
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -o /processor ./cmd/processor

# Runtime
FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /processor /processor
ENTRYPOINT ["/processor"]
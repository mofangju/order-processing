package main

import (
	"context"
	"errors"
	"order-processor/internal/processor"
	"os"
	"os/signal"
	"syscall"

	"github.com/rs/zerolog/log"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	p, err := processor.NewProcessor(ctx)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to create processor")
	}

	log.Info().Msg("starting SQS poller")
	if err := p.Start(ctx); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatal().Err(err).Msg("processor stopped with error")
	}

	log.Info().Msg("shutting down gracefully")
}

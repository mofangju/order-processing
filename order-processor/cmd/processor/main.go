package main

import (
	"context"
	"order-processor/internal/processor"
	"os"
	"os/signal"

	"github.com/rs/zerolog/log"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()

	p, err := processor.NewProcessor(ctx)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to create processor")
	}

	log.Info().Msg("starting SQS poller...")
	if err := p.Start(ctx); err != nil && err != context.Canceled {
		log.Fatal().Err(err).Msg("processor stopped with error")
	}

	log.Info().Msg("shutting down gracefully")
}

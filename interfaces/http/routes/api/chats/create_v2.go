package chats

import (
	"bufio"
	"encoding/json"
	"errors"
	"io"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type chatV2RequeryBody struct {
	DatasetIDs []string `json:"dataset_ids"`
	ProjectIDs []string `json:"project_ids"`
	UserInput  string   `json:"user_input"`
}

func (h *httpHandler) chat_v2(ctx *fiber.Ctx) error {
	// Parse the request body
	var body chatV2RequeryBody
	if err := json.Unmarshal(ctx.Body(), &body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).SendString("Invalid request body")
	}

	// Validate the input
	if len(body.DatasetIDs) == 0 && len(body.ProjectIDs) == 0 {
		return ctx.Status(fiber.StatusBadRequest).SendString("At least one dataset_id or project_id is required")
	}
	if body.UserInput == "" {
		return ctx.Status(fiber.StatusBadRequest).SendString("user_input is required")
	}

	// Set headers for SSE
	ctx.Set("Content-Type", "text/event-stream; charset=utf-8")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")
	ctx.Set("X-Accel-Buffering", "no")

	// Create buffered channels for communication to prevent blocking
	dataChan := make(chan []byte, 10)
	errChan := make(chan error, 10)

	params := &models.AIAgentChatParams{
		ProjectIDs: body.ProjectIDs,
		DatasetIDs: body.DatasetIDs,
		UserInput:  body.UserInput,
		DataChan:   dataChan,
		ErrChan:    errChan,
	}

	// Call the chat service with the parsed parameters
	ctx.Context().Response.SetBodyStreamWriter(func(w *bufio.Writer) {
		h.chatSvc.ChatWithAiAgent(ctx.Context(), params)

		sendMessage := func(eventType, data string) error {
			_, err := w.WriteString("event: " + eventType + "\ndata: " + data + "\n\n")
			if err != nil {
				return err
			}
			return w.Flush()
		}

		clientDisconnected := make(chan struct{})
		go func() {
			<-ctx.Context().Done()
			close(clientDisconnected)
		}()

		for {
			select {
			case data, ok := <-dataChan:
				if !ok {
					return
				}
				if err := sendMessage("message", string(data)); err != nil {
					h.logger.Error("Error writing to response stream", zap.Error(err))
					return
				}

			case err, ok := <-errChan:
				if !ok {
					// Channel was closed
					return
				}

				if errors.Is(err, io.EOF) {
					// End of data from service
					h.logger.Info("Chat completed successfully")
					sendMessage("close", "")
					return
				}

				if err != nil {
					h.logger.Error("Error in chat service", zap.Error(err))
					sendMessage("error", err.Error())
					return
				}

			case <-clientDisconnected:
				// Client disconnected
				h.logger.Info("Connection closed by client")
				return

			}
		}
	})

	return nil
}

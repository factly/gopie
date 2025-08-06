package routes

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/queue"
	"github.com/factly/gopie/downlods-server/server/middleware"
	"github.com/gofiber/fiber/v2"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
)

func (h *httpHandler) downloadEvents(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	var req models.CreateDownloadRequest
	if err := ctx.BodyParser(&req); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}
	req.OrgID = orgID
	req.UserID = userID

	ctx.Set("Content-Type", "text/event-stream")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")

	ctxDone := ctx.Context().Done()

	ctx.Context().SetBodyStreamWriter(fasthttp.StreamWriter(func(w *bufio.Writer) {
		fmt.Fprintf(w, "event: request_received\ndata: {\"message\": \"Request received, preparing to submit to queue...\"}\n\n")
		w.Flush()

		bgCtx := context.Background()

		downloadJob, err := h.queue.Submit(bgCtx, &req)
		if err != nil {
			h.logger.Error("Failed to submit download job", zap.Error(err))
			errorEvent, _ := json.Marshal(map[string]string{"type": "error", "message": "could not create download job"})
			fmt.Fprintf(w, "event: error\ndata: %s\n\n", errorEvent)
			w.Flush()
			return
		}
		downloadID := downloadJob.ID.String()

		clientChan := h.queue.Manager.Subscribe(downloadID)
		defer h.queue.Manager.Unsubscribe(downloadID, clientChan)

		event, _ := json.Marshal(downloadJob)
		fmt.Fprintf(w, "event: job_created\ndata: %s\n\n", event)
		w.Flush()

		for {
			select {
			case event, ok := <-clientChan:
				if !ok {
					return // Channel closed
				}
				fmt.Fprintf(w, "data: %s\n\n", event)
				if err := w.Flush(); err != nil {
					h.logger.Info("SSE stream writer flush error", zap.Error(err), zap.String("download_id", downloadID))
					return
				}

				var eventData queue.ProgressEvent
				if err := json.Unmarshal([]byte(event), &eventData); err == nil {
					if eventData.Type == "complete" || eventData.Type == "error" {
						h.logger.Info("SSE stream finished, closing connection.", zap.String("download_id", downloadID), zap.String("reason", eventData.Type))
						return
					}
				}
			case <-ctxDone:
				h.logger.Info("SSE client disconnected", zap.String("download_id", downloadID))
				return
			}
		}
	}))

	return nil
}

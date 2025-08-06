package routes

import (
	"bufio"
	"fmt"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/server/middleware"
	"github.com/gofiber/fiber/v2"
	"github.com/valyala/fasthttp"
)

func (h *httpHandler) createDownload(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	var req models.CreateDownloadRequest
	if err := ctx.BodyParser(&req); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}
	req.OrgID = orgID
	req.UserID = userID

	downloadJob, err := h.queue.Submit(ctx.Context(), &req)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not create download job"})
	}

	return ctx.Status(fiber.StatusAccepted).JSON(downloadJob)
}

func (h *httpHandler) downloadEvents(ctx *fiber.Ctx) error {
	downloadID := ctx.Params("downloadID")
	if downloadID == "" {
		return ctx.SendStatus(fiber.StatusBadRequest)
	}

	ctx.Set("Content-Type", "text/event-stream")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")

	clientChan := h.queue.Manager.Register(downloadID)
	defer h.queue.Manager.Unregister(downloadID, clientChan)

	ctx.Context().SetBodyStreamWriter(fasthttp.StreamWriter(func(w *bufio.Writer) {
		fmt.Fprintf(w, "event: connected\ndata: {}\n\n")
		w.Flush()

		for {
			select {
			case event, ok := <-clientChan:
				if !ok {
					return
				}
				fmt.Fprintf(w, "data: %s\n\n", event)
				if err := w.Flush(); err != nil {
					return
				}
			case <-ctx.Context().Done():
				return
			}
		}
	}))

	return nil
}

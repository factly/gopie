package s3

import (
	"github.com/factly/gopie/application/services"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	svc *services.Driver
}

func newHTTPHandler(svc *services.Driver) *httpHandler {
	return &httpHandler{svc}
}

func Routes(router fiber.Router, svc *services.Driver) {
	httpHandler := newHTTPHandler(svc)
	router.Post("/upload", httpHandler.upload)
}

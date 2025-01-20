package s3

import "github.com/gofiber/fiber/v2"

type reqBody struct {
	FilePath string `json:"file_path"`
}

// upload files to gopie from s3
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	var body reqBody
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	dataset, err := h.svc.UploadFile(ctx.Context(), body.FilePath)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error uploading file",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(dataset)
}

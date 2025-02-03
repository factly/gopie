package datasets

import "github.com/gofiber/fiber/v2"

func (h *httpHandler) details(ctx *fiber.Ctx) error {
	datasetID := ctx.Params("datasetID")
	dataset, err := h.svc.Details(datasetID)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(dataset)
}

package database

import (
	"github.com/factly/gopie/domain"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// @Summary Delete a database source
// @Description Delete a database source by its ID
// @Tags database
// @Accept json
// @Produce json
// @Param id path string true "Database Source ID"
// @Success 200 {object} responses.SuccessResponse "Successfully deleted database source"
// @Failure 400 {object} responses.ErrorResponse "Invalid ID format"
// @Failure 404 {object} responses.ErrorResponse "Database source not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/{id} [delete]
func (h *httpHandler) deleteHandler(ctx *fiber.Ctx) error {
	id := ctx.Params("id")
	if id == "" {
		h.logger.Error("Database source ID is required")
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "ID is required",
			"message": "Database source ID is required in path",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Optional: Validate if ID is in UUID format if that's your standard
	// _, err := uuid.Parse(id)
	// if err != nil {
	// 	h.logger.Error("Invalid database source ID format", zap.Error(err), zap.String("id", id))
	// 	return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
	// 		"error":   err.Error(),
	// 		"message": "Invalid database source ID format",
	// 		"code":    fiber.StatusBadRequest,
	// 	})
	// }

	err := h.dbSourceSvc.Delete(id)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Database source not found for deletion", zap.Error(err), zap.String("id", id))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Database source not found",
				"message": "Database source with ID " + id + " not found",
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error deleting database source", zap.Error(err), zap.String("id", id))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting database source",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusOK).JSON(fiber.Map{
		"message": "Database source deleted successfully",
	})
}

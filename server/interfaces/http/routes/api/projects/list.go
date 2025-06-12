package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
)

// @Summary List all projects
// @Description Get all projects with pagination and search
// @Tags projects
// @Accept json
// @Produce json
// @Param limit query integer false "Number of items per page" default(10)
// @Param page query integer false "Page number" default(1)
// @Param query query string false "Search query"
// @Success 200 {array} models.Project
// @Failure 400 {object} responses.ErrorResponse "Invalid query parameters"
// @Failure 404 {object} responses.ErrorResponse "No projects found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects [get]
func (h *httpHandler) list(ctx *fiber.Ctx) error {
	limitStr := ctx.Query("limit")
	pageStr := ctx.Query("page")
	query := ctx.Query("query")
	organizationID := ctx.Get("X-Organization-ID")

	limit, page := pkg.ParseLimitAndPage(limitStr, pageStr)

	projects, err := h.svc.List(query, limit, page, organizationID)
	if err != nil {
		if domain.IsStoreError(err) {
			switch err {
			case domain.ErrRecordNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "No projects found",
					"message": "No projects exist with the given criteria",
					"code":    fiber.StatusNotFound,
				})
			case domain.ErrInvalidData:
				return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
					"error":   "Invalid query parameters",
					"message": "The provided search parameters are invalid",
					"code":    fiber.StatusBadRequest,
				})
			}
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching projects",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(projects)
}

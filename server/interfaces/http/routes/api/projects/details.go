package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

// @Summary Get project details
// @Description Get details of a specific project
// @Tags projects
// @Accept json
// @Produce json
// @Param projectID path string true "Project ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} models.Project
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID} [get]
func (h *httpHandler) details(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")
	orgID := ctx.Get(middleware.OrganizationIDHeader)

	project, err := h.svc.Details(projectID, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Project not found",
				"message": "The requested project does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(project)
}

package datasets

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

// @Summary List project datasets
// @Description Get all datasets in a project with pagination
// @Tags datasets
// @Accept json
// @Produce json
// @Param projectID path string true "Project ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param limit query integer false "Number of items per page" default(10)
// @Param page query integer false "Page number" default(1)
// @Success 200 {array} models.Dataset
// @Failure 400 {object} responses.ErrorResponse "Invalid query parameters"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID}/datasets [get]
func (h *httpHandler) list(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	role := ctx.Locals(middleware.RoleCtxKey).(models.Role)
	limitStr := ctx.Query("limit")
	pageStr := ctx.Query("page")

	limit, page := pkg.ParseLimitAndPage(limitStr, pageStr)

	datasets, err := h.datasetsSvc.List(projectID, role, orgID, userID, limit, page)
	if err != nil {
		if domain.IsStoreError(err) {
			switch err {
			case domain.ErrRecordNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "No datasets found",
					"message": "No datasets exist for this project",
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
			"message": "Error fetching datasets",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(datasets)
}

func (h *httpHandler) listAllDatasets(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	datasets, err := h.datasetsSvc.ListALlDatasetsFromProject(projectID)
	if err != nil {
		if domain.IsStoreError(err) {
			switch err {
			case domain.ErrRecordNotFound:
				return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
					"error":   "No datasets found",
					"message": "No datasets exist for this project",
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
			"message": "Error fetching datasets",
			"code":    fiber.StatusInternalServerError,
		})
	}
	return ctx.JSON(datasets)
}

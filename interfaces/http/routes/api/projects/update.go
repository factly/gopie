package projects

import (
	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/gofiber/fiber/v2"
)

// updateProjectBody represents the request body for updating a project
// @Description Request body for updating an existing project
type updateProjectBody struct {
	// Name of the project
	Name string `json:"name,omitempty" validate:"required,min=3,max=50" example:"Updated Project Name"`
	// Description of the project
	Description string `json:"description,omitempty" validate:"omitempty,max=500" example:"Updated project description"`
	UpdatedBy   string `json:"updated_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
}

// @Summary Update a project
// @Description Update an existing project's name and/or description
// @Tags projects
// @Accept json
// @Produce json
// @Param projectID path string true "Project ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Param project body updateProjectBody true "Project object"
// @Success 200 {object} responses.SuccessResponse{data=models.Project}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects/{projectID} [patch]
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	projectID := ctx.Params("projectID")

	body := updateProjectBody{}
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	project, err := h.svc.Update(projectID, &models.UpdateProjectParams{
		Name:        body.Name,
		Description: body.Description,
		UpdatedBy:   body.UpdatedBy,
	})
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
			"message": "Error updating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.JSON(map[string]interface{}{
		"data": project,
	})
}

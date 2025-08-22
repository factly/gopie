package projects

import (
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

// createRequestBody represents the request body for creating a project
// @Description Request body for creating a new project
type createRequestBody struct {
	// Name of the project
	Name string `json:"name" validate:"required,min=3,max=50" example:"My New Project"`
	// Description of the project
	Description  string `json:"description" validate:"required,min=10,max=1000" example:"This is a detailed description of my new project"`
	CustomPrompt string `json:"custom_prompt"`
}

// @Summary Create a new project
// @Description Create a new project with the given name and description
// @Tags projects
// @Accept json
// @Produce json
// @Param project body createRequestBody true "Project object"
// @Success 201 {object} responses.SuccessResponse{data=models.Project}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /v1/api/projects [post]
func (h *httpHandler) create(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)

	body := createRequestBody{}
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

	project, err := h.projectSvc.Create(models.CreateProjectParams{
		Name:         body.Name,
		Description:  body.Description,
		CreatedBy:    userID,
		OrgID:        orgID,
		CustomPrompt: body.CustomPrompt,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": project,
	})
}

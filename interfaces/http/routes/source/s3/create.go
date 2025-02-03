package s3

import (
	"errors"
	"os"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

type reqBody struct {
	FilePath    string `json:"file_path" validate:"required"`
	Description string `json:"description" validate:"required,min=10,max=500"`
	ProjectID   string `json:"project_id" validate:"required"`
}

// upload files to gopie from s3
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	var body reqBody
	if err := ctx.BodyParser(&body); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Validate project exists
	_, err := h.projectSvc.Details(body.ProjectID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Project not found",
				"message": "The specified project does not exist",
				"code":    fiber.StatusNotFound,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	res, err := h.olapSvc.UploadFile(ctx.Context(), body.FilePath)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading file. Please check if the file exists and is accessible",
			"code":    fiber.StatusBadRequest,
		})
	}

	countSql := "select count(*) from " + res.TableName

	countResult, err := h.olapSvc.ExecuteQuery(countSql)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching row count from uploaded file",
			"code":    fiber.StatusInternalServerError,
		})
	}

	count, ok := countResult[0]["count_star()"].(int64)
	if !ok {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Invalid count result",
			"message": "Error processing row count from uploaded file",
			"code":    fiber.StatusInternalServerError,
		})
	}
	h.logger.Info("count", zap.Int64("count", count))

	columns, err := h.olapSvc.ExecuteQuery("desc " + res.TableName)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching column information from uploaded file",
			"code":    fiber.StatusInternalServerError,
		})
	}

	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:        res.TableName,
		Description: body.Description,
		ProjectID:   body.ProjectID,
		Columns:     columns,
		Format:      res.Format,
		FilePath:    body.FilePath,
		RowCount:    int(count),
		Size:        res.Size,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// delete res.FilePath in tmp
	if err = os.Remove(res.FilePath); err != nil {
		h.logger.Error("Error deleting temporary file", zap.Error(err), zap.String("path", res.FilePath))
	}

	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

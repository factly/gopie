package s3

import (
	"os"

	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type uploadRequestBody struct {
	FilePath    string `json:"file_path" validate:"required,min=1"`
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500"`
	ProjectID   string `json:"project_id" validate:"required,uuid"`
}

// upload files to gopie from s3
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	body := ctx.Locals("body").(*uploadRequestBody)

	res, err := h.olapSvc.UploadFile(ctx.Context(), body.FilePath)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error uploading file",
			"code":    fiber.StatusInternalServerError,
		})
	}

	countSql := "select count(*) from " + res.TableName

	countResult, err := h.olapSvc.ExecuteQuery(countSql)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error fetching count",
			"code":    fiber.StatusInternalServerError,
		})
	}

	count, ok := countResult[0]["count_star()"].(int64)
	if !ok {
		return fiber.NewError(fiber.StatusInternalServerError, "error fetching count")
	}

	columns, err := h.olapSvc.ExecuteQuery("desc " + res.TableName)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error fetching columns",
			"code":    fiber.StatusInternalServerError,
		})

	}

	// BUG: for some reason size and row count is not being returned fix this
	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:        res.TableName,
		Description: "Dataset created from S3",
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
			"message": "error creating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}
	// delete res.FilePath in tmp
	err = os.Remove(res.FilePath)
	if err != nil {
		h.logger.Error("Error deleting file from tmp dir you might to delete it manually", zap.Error(err))
	}

	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

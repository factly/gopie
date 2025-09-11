package middleware

import (
	"strings"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type body struct {
	Query string `json:"query"`
}

func AuthorizeDatasetsAccessFromSql(olap *services.OlapService, store *services.ProjectService, logger *logger.Logger) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		b := &body{}
		err := ctx.BodyParser(b)
		if err != nil {
			logger.Error("Error parsing body", zap.Error(err))
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"message": "Bad Request",
				"error":   "Invalid request body",
				"code":    fiber.StatusBadRequest,
			})
		}

		tableNames, err := olap.TableNames(b.Query)
		if err != nil {
			logger.Error("Error extracting table names from query", zap.Error(err))
			return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"message": "Bad Request",
				"error":   "Invalid SQL query",
				"code":    fiber.StatusBadRequest,
			})
		}

		belongs, err := store.ProjectsBelongToOrg(tableNames, ctx.Locals("org_id").(string))
		if err != nil {
			logger.Error("Error checking if datasets belong to org", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"message": "Internal Server Error",
				"error":   "Could not verify dataset access",
				"code":    fiber.StatusInternalServerError,
			})
		}

		if !belongs {
			return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"message": "Forbidden",
				"error":   "Access to one or more datasets is forbidden",
				"code":    fiber.StatusForbidden,
			})
		}

		return ctx.Next()
	}
}

func AuthorizeDatasetsFromParams(store *services.ProjectService, logger *logger.Logger) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		// ignore if the endpoint is sql
		// as it will be handled by AuthorizeDatasetsAccessFromSql middleware
		if strings.HasSuffix(ctx.Path(), "/sql") {
			return ctx.Next()
		}

		tableName := ctx.Params("tableName")

		belongs, err := store.DatasetsBelongToOrg([]string{tableName}, ctx.Locals("org_id").(string))
		if err != nil {
			logger.Error("Error checking if dataset belongs to org", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"message": "Internal Server Error",
				"error":   "Could not verify dataset access",
				"code":    fiber.StatusInternalServerError,
			})
		}

		if !belongs {
			return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"message": "Forbidden",
				"error":   "Access to the dataset is forbidden",
				"code":    fiber.StatusForbidden,
			})
		}

		return ctx.Next()
	}
}

func AuthorizeProjectsAndDatasetsFromHeaders(store *services.ProjectService, logger *logger.Logger) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		projectIDs := strings.Split(ctx.Get("x-project-ids"), ",")
		datasetNames := strings.Split(ctx.Get("x-dataset-ids"), ",")
		orgID := ctx.Locals("org_id").(string)

		if len(projectIDs) > 0 && projectIDs[0] != "" {
			type result struct {
				belongs bool
				err     error
			}

			projectCh := make(chan result, 1)
			datasetCh := make(chan result, 1)

			go func() {
				belongs, err := store.ProjectsBelongToOrg(projectIDs, orgID)
				projectCh <- result{belongs, err}
			}()

			go func() {
				belongs, err := store.DatasetsBelongToOrg(datasetNames, orgID)
				datasetCh <- result{belongs, err}
			}()

			projectRes := <-projectCh
			datasetRes := <-datasetCh

			if projectRes.err != nil {
				logger.Error("Error checking if projects belong to org", zap.Error(projectRes.err))
				return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"message": "Internal Server Error",
					"error":   "Could not verify project access",
					"code":    fiber.StatusInternalServerError,
				})
			}

			if !projectRes.belongs {
				return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
					"message": "Forbidden",
					"error":   "Access to one or more projects is forbidden",
					"code":    fiber.StatusForbidden,
				})
			}

			if datasetRes.err != nil {
				logger.Error("Error checking if datasets belong to org", zap.Error(datasetRes.err))
				return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"message": "Internal Server Error",
					"error":   "Could not verify dataset access",
					"code":    fiber.StatusInternalServerError,
				})
			}

			if !datasetRes.belongs {
				return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
					"message": "Forbidden",
					"error":   "Access to one or more datasets is forbidden",
					"code":    fiber.StatusForbidden,
				})
			}

			return ctx.Next()
		}

		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"message": "Bad Request",
			"error":   "No project IDs provided",
			"code":    fiber.StatusBadRequest,
		})
	}
}

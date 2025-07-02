package database

import (
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	pg_query "github.com/pganalyze/pg_query_go/v6"
	"go.uber.org/zap"
	"vitess.io/vitess/go/vt/sqlparser"
)

// createRequestBody represents the request body for creating a database source
// @Description Request body for creating a database source dataset
type createRequestBody struct {
	// Driver of the database
	Driver string `json:"driver" validate:"required,oneof=postgres mysql" example:"postgres"`
	// Connection string for the Postgres database
	ConnectionString string `json:"connection_string" validate:"required" example:"postgres://username:password@localhost:5432/database"`
	// SQL query to execute
	SQLQuery string `json:"sql_query" validate:"required" example:"SELECT * FROM users"`
	// Description of the dataset
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500" example:"User data from our production database"`
	// ID of the project to add the dataset to
	ProjectID string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// User ID of the creator
	CreatedBy string `json:"created_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Alias of the dataset
	Alias string `json:"alias" validate:"required,min=3" example:"users_data"`
}

// @Summary Create dataset from Postgres
// @Description Create a new dataset from a Postgres database query
// @Tags database
// @Accept json
// @Produce json
// @Param body body createRequestBody true "Create request parameters"
// @Success 201 {object} responses.SuccessResponse{data=models.Dataset}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or database connection error"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/upload [post]
func (h *httpHandler) create(ctx *fiber.Ctx) error {
	orgID := ctx.Get(middleware.OrganizationIDHeader)
	if orgID == "" {
		h.logger.Error("Organization ID header is missing")
		return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
			"error":   "Organization ID header is required",
			"message": "Please provide the organization ID in the request header",
			"code":    fiber.StatusForbidden,
		})
	}

	// Get request body from context
	var body createRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body format",
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

	err = h.parseSQLQuery(body.SQLQuery, body.Driver)
	if err != nil {
		h.logger.Error("Error parsing SQL query", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid SQL query",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Check if project exists
	project, err := h.projectSvc.Details(body.ProjectID, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Project not found", zap.Error(err), zap.String("project_id", body.ProjectID))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Project not found",
				"message": fmt.Sprintf("Project with ID %s not found", body.ProjectID),
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching project", zap.Error(err), zap.String("project_id", body.ProjectID))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Creating database source dataset", zap.String("project_id", project.ID))

	tableName := fmt.Sprintf("gp_%s", pkg.RandomString(13))

	if body.Driver == "postgres" {
		err := h.olapSvc.CreateTableFromPostgres(body.ConnectionString, body.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from postgres", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from postgres",
				"code":    fiber.StatusInternalServerError,
			})
		}
	} else {
		err := h.olapSvc.CreateTableFromMySql(body.ConnectionString, body.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from mysql", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from mysql",
				"code":    fiber.StatusInternalServerError,
			})
		}
	}

	// Create the database source
	dbSourceParams := &models.CreateDatabaseSourceParams{
		ConnectionString: body.ConnectionString,
		SQLQuery:         body.SQLQuery,
		Alias:            body.Alias,
		Description:      body.Description,
		ProjectID:        project.ID,
		CreatedBy:        body.CreatedBy,
		Driver:           body.Driver,
	}

	source, err := h.dbSourceSvc.Create(dbSourceParams)
	if err != nil {
		// Clean up the created OLAP table since source creation failed
		h.logger.Error("Error creating database source", zap.Error(err))
		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating database source",
			"code":    fiber.StatusInternalServerError,
		})
	}

	time.Sleep(2 * time.Second) // Wait for the table to be created in OLAP

	count, columns, err := h.getMetrics(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", tableName))

		// Clean up the created OLAP table since metrics fetch failed
		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:        tableName,
		Description: body.Description,
		ProjectID:   project.ID,
		Columns:     columns,
		Format:      body.Driver,
		RowCount:    count,
		Alias:       body.Alias,
		CreatedBy:   body.CreatedBy,
		UpdatedBy:   body.CreatedBy,
		OrgID:       orgID,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))

		// Clean up the created OLAP table since dataset record creation failed
		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		deleteErr := h.dbSourceSvc.Delete(source.ID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteErr), zap.String("source_id", source.ID))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))

		// Clean up the dataset record and OLAP table since dataset summary fetch failed
		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(tableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))

		// Clean up the dataset record and OLAP table since dataset summary creation failed
		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.UploadSchemaParams{
		DatasetID: dataset.ID,
		ProjectID: project.ID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))

		// Clean up all created resources since schema upload failed
		summaryErr := h.datasetSvc.DeleteDatasetSummary(tableName)
		if summaryErr != nil {
			h.logger.Error("Failed to delete dataset summary during cleanup", zap.Error(summaryErr), zap.String("dataset_name", tableName))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading schema to AI agent",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Database source dataset creation completed successfully",
		zap.String("dataset_id", dataset.ID),
		zap.String("project_id", project.ID),
		zap.String("table_name", tableName))

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": map[string]any{
			"dataset": dataset,
			"summary": summary,
			"source":  source,
		},
	})
}

// parse and validate sql query
func (h *httpHandler) parseSQLQuery(sqlQuery, driver string) error {
	// First check if the query starts with SELECT (case insensitive)
	trimmedQuery := strings.TrimSpace(sqlQuery)
	if !strings.HasPrefix(strings.ToUpper(trimmedQuery), "SELECT") {
		h.logger.Error("SQL query must be a SELECT statement")
		return fmt.Errorf("invalid SQL query: only SELECT statements are allowed")
	}

	if driver == "postgres" {
		parseResult, err := pg_query.Parse(sqlQuery)
		if err != nil {
			h.logger.Error("Error parsing PostgreSQL query", zap.Error(err))
			return fmt.Errorf("invalid SQL query: %w", err)
		}

		if len(parseResult.GetStmts()) == 0 {
			h.logger.Error("No statements found in SQL query")
			return fmt.Errorf("invalid SQL query: no statements found")
		}

		// Check if the query is a SELECT statement for PostgreSQL
		stmt := parseResult.GetStmts()[0]
		if stmt.GetStmt().GetSelectStmt() == nil {
			h.logger.Error("SQL query must be a SELECT statement")
			return fmt.Errorf("invalid SQL query: only SELECT statements are allowed")
		}

		return nil
	} else if driver == "mysql" {
		// For MySQL, use the vitess parser
		parser, err := sqlparser.New(sqlparser.Options{})
		if err != nil {
			h.logger.Error("Error creating SQL parser", zap.Error(err))
			return fmt.Errorf("invalid SQL query: %w", err)
		}

		parseResult, err := parser.Parse(sqlQuery)
		if err != nil {
			h.logger.Error("Error parsing SQL query", zap.Error(err))
			return fmt.Errorf("invalid SQL query: %w", err)
		}

		if parseResult == nil {
			h.logger.Error("No result from SQL parser")
			return fmt.Errorf("invalid SQL query: parsing returned no result")
		}

		// Check if the query is a SELECT statement
		if _, ok := parseResult.(*sqlparser.Select); !ok {
			h.logger.Error("SQL query must be a SELECT statement")
			return fmt.Errorf("invalid SQL query: only SELECT statements are allowed")
		}

		return nil
	}

	return fmt.Errorf("unsupported database driver: %s", driver)
}

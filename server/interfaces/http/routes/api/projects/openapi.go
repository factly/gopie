package projects

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// projectOpenAPI handles the OpenAPI specification endpoint for a project
// It returns OpenAPI specs for all datasets in a project
func (h *httpHandler) projectOpenAPI(c *fiber.Ctx) error {
	projectID := c.Params("projectID")
	if projectID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "project ID is required",
		})
	}

	// Get all datasets for this project
	datasets, err := h.datasetSvc.List(projectID, 1000, 0)
	if err != nil {
		h.logger.Error("Error getting datasets for project", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "failed to retrieve datasets",
		})
	}

	// Base OpenAPI specification structure
	spec := map[string]interface{}{
		"openapi": "3.0.0",
		"info": map[string]interface{}{
			"title":       "Gopie Project API - Dataset Endpoints",
			"description": "API endpoints for all datasets in project: " + projectID,
			"version":     "1.0.0",
		},
		"paths": map[string]interface{}{},
	}

	paths := spec["paths"].(map[string]interface{})

	// Add endpoints for each dataset
	for _, dataset := range datasets.Results {
		tableName := dataset.Name

		// Fetch schema for this dataset
		schema := dataset.Columns
		// Generate property definitions based on schema
		schemaProperties := make(map[string]interface{})
		for _, columnInfo := range schema {
			// Extract column name and type from the schema
			columnName, nameOk := columnInfo["column_name"].(string)
			if !nameOk {
				columnName, nameOk = columnInfo["name"].(string)
				if !nameOk {
					continue
				}
			}

			// Extract type information
			columnType, typeOk := columnInfo["column_type"].(string)
			if !typeOk {
				columnType, typeOk = columnInfo["type"].(string)
				if !typeOk {
					continue
				}
			}

			// Convert DuckDB types to OpenAPI types
			openAPIType := "string" // Default
			switch strings.ToUpper(columnType) {
			case "INTEGER", "BIGINT", "TINYINT", "SMALLINT":
				openAPIType = "integer"
			case "DOUBLE", "FLOAT", "DECIMAL", "REAL":
				openAPIType = "number"
			case "BOOLEAN":
				openAPIType = "boolean"
			}

			schemaProperties[columnName] = map[string]interface{}{
				"type": openAPIType,
			}
		}

		// Add dataset endpoints
		prefix := "v1/api"
		paths[prefix+"/tables"+tableName] = map[string]any{
			"get": map[string]any{
				"summary":     "Get dataset table data",
				"description": "Returns the table data for dataset " + tableName,
				"parameters": []map[string]any{
					{
						"name":        "columns",
						"in":          "query",
						"description": "Comma-separated list of columns to return",
						"schema":      map[string]any{"type": "string"},
						"example":     "id,name,value",
					},
					{
						"name":        "sort",
						"in":          "query",
						"description": "Sort order (column name with optional -prefix for desc)",
						"schema":      map[string]interface{}{"type": "string"},
						"example":     "-created_at",
					},
					{
						"name":        "limit",
						"in":          "query",
						"description": "Number of records to return",
						"schema":      map[string]interface{}{"type": "integer"},
						"example":     10,
					},
					{
						"name":        "page",
						"in":          "query",
						"description": "Page number",
						"schema":      map[string]interface{}{"type": "integer"},
						"example":     1,
					},
				},
				"responses": map[string]interface{}{
					"200": map[string]interface{}{
						"description": "Successful response",
						"content": map[string]interface{}{
							"application/json": map[string]interface{}{
								"schema": map[string]interface{}{
									"type": "array",
									"items": map[string]interface{}{
										"type":       "object",
										"properties": schemaProperties,
									},
								},
							},
						},
					},
					"400": map[string]interface{}{
						"description": "Invalid query parameters",
					},
					"500": map[string]interface{}{
						"description": "Internal server error",
					},
				},
			},
		}

		paths[prefix+"/schemas/"+tableName] = map[string]interface{}{
			"get": map[string]interface{}{
				"summary":     "Get dataset schema",
				"description": "Returns the schema information for dataset " + tableName,
				"responses": map[string]interface{}{
					"200": map[string]interface{}{
						"description": "Successful response",
						"content": map[string]interface{}{
							"application/json": map[string]interface{}{
								"schema": map[string]interface{}{
									"type": "object",
									"properties": map[string]interface{}{
										"schema": map[string]interface{}{
											"type": "object",
										},
									},
								},
							},
						},
					},
					"404": map[string]interface{}{
						"description": "Dataset not found",
					},
					"500": map[string]interface{}{
						"description": "Internal server error",
					},
				},
			},
		}

		paths[prefix+"/summary/"+tableName] = map[string]interface{}{
			"get": map[string]interface{}{
				"summary":     "Get dataset summary",
				"description": "Returns summary information for dataset " + tableName,
				"responses": map[string]interface{}{
					"200": map[string]interface{}{
						"description": "Successful response",
						"content": map[string]interface{}{
							"application/json": map[string]interface{}{
								"schema": map[string]interface{}{
									"type": "object",
									"properties": map[string]interface{}{
										"summary": map[string]interface{}{
											"type": "array",
											"items": map[string]interface{}{
												"type": "object",
												"properties": map[string]interface{}{
													"column": map[string]interface{}{
														"type": "string",
													},
													"stats": map[string]interface{}{
														"type": "object",
													},
												},
											},
										},
									},
								},
							},
						},
					},
					"404": map[string]interface{}{
						"description": "Dataset not found",
					},
					"500": map[string]interface{}{
						"description": "Internal server error",
					},
				},
			},
		} // <-- The erroneous comma was removed here

		paths[prefix+"/sql"] = map[string]interface{}{
			"post": map[string]interface{}{
				"summary":     "Execute SQL query",
				"description": "Executes SQL query against dataset " + tableName,
				"requestBody": map[string]interface{}{
					"required": true,
					"content": map[string]interface{}{
						"application/json": map[string]interface{}{
							"schema": map[string]interface{}{
								"type": "object",
								"properties": map[string]interface{}{
									"query": map[string]interface{}{
										"type":        "string",
										"description": "SQL query string",
									},
								},
								"required": []string{"query"},
							},
						},
					},
				},
				"responses": map[string]interface{}{
					"200": map[string]interface{}{
						"description": "Successful response",
						"content": map[string]interface{}{
							"application/json": map[string]interface{}{
								"schema": map[string]interface{}{
									"type": "object",
									"properties": map[string]interface{}{
										"data": map[string]interface{}{
											"type": "array",
											"items": map[string]interface{}{
												"type": "object",
											},
										},
									},
								},
							},
						},
					},
					"400": map[string]interface{}{
						"description": "Invalid SQL query",
					},
					"500": map[string]interface{}{
						"description": "Internal server error",
					},
				},
			},
		}

		paths[prefix+"/nl2sql"] = map[string]interface{}{
			"post": map[string]interface{}{
				"summary":     "Convert natural language to SQL",
				"description": "Converts a natural language query to SQL for dataset " + tableName,
				"requestBody": map[string]interface{}{
					"required": true,
					"content": map[string]interface{}{
						"application/json": map[string]interface{}{
							"schema": map[string]interface{}{
								"type": "object",
								"properties": map[string]interface{}{
									"query": map[string]interface{}{
										"type":        "string",
										"description": "Natural language query",
									},
								},
								"required": []string{"query"},
							},
						},
					},
				},
				"responses": map[string]interface{}{
					"200": map[string]interface{}{
						"description": "Successful response",
						"content": map[string]interface{}{
							"application/json": map[string]interface{}{
								"schema": map[string]interface{}{
									"type": "object",
								},
							},
						},
					},
					"400": map[string]interface{}{
						"description": "Invalid query",
					},
					"500": map[string]interface{}{
						"description": "Internal server error",
					},
				},
			},
		}
	}

	return c.JSON(spec)
}

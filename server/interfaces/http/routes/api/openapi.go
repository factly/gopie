package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// OpenAPIHandler handles the OpenAPI specification endpoint
func (h *httpHandler) datasetOpenAPI(c *fiber.Ctx) error {
	tableName := c.Params("tableName")
	if tableName == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "table name is required",
		})
	}

	// Fetch the actual schema for this table to include in the OpenAPI spec
	schema, err := h.driverSvc.GetTableSchema(tableName)
	if err != nil {
		h.logger.Error("Error getting table schema for OpenAPI spec", zap.Error(err))
		// Continue with empty schema if we can't fetch it
	}

	// Generate property definitions based on schema if available
	schemaProperties := make(map[string]interface{})
	
	// Process the schema data - GetTableSchema returns []map[string]any directly
	for _, columnInfo := range schema {
		// Extract column name and type from the schema
		columnName, nameOk := columnInfo["column_name"].(string)
		if !nameOk {
			// Try alternate field name 
			columnName, nameOk = columnInfo["name"].(string)
			if !nameOk {
				continue // Skip if we can't find column name
			}
		}
		
		// Extract type information
		columnType, typeOk := columnInfo["column_type"].(string) 
		if !typeOk {
			// Try alternate field name
			columnType, typeOk = columnInfo["type"].(string)
			if !typeOk {
				continue // Skip if we can't find column type
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
		
		// Add the property to our schema
		schemaProperties[columnName] = map[string]interface{}{
			"type": openAPIType,
		}
	}

	// Generate OpenAPI specification for the dataset
	spec := map[string]interface{}{
		"openapi": "3.0.0",
		"info": map[string]interface{}{
			"title":       "Gopie Dataset API - " + tableName,
			"description": "API for interacting with " + tableName + " dataset",
			"version":     "1.0.0",
		},
		"paths": map[string]interface{}{
			"/tables/" + tableName: map[string]interface{}{
				"get": map[string]interface{}{
					"summary":     "Get dataset table data",
					"description": "Returns the table data for the specified dataset",
					"parameters": []map[string]interface{}{
						{
							"name":        "columns",
							"in":          "query",
							"description": "Comma-separated list of columns to return",
							"schema":      map[string]interface{}{"type": "string"},
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
			},
			"/schemas/" + tableName: map[string]interface{}{
				"get": map[string]interface{}{
					"summary":     "Get dataset schema",
					"description": "Returns the schema information for the specified dataset",
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
			},
			"/summary/" + tableName: map[string]interface{}{
				"get": map[string]interface{}{
					"summary":     "Get dataset summary",
					"description": "Returns summary information for the specified dataset",
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
			},
			"/sql": map[string]interface{}{
				"post": map[string]interface{}{
					"summary":     "Execute SQL query",
					"description": "Executes SQL query against the datasets",
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
			},
			"/nl2sql": map[string]interface{}{
				"post": map[string]interface{}{
					"summary":     "Convert natural language to SQL",
					"description": "Converts a natural language query to SQL for the specified dataset",
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
			},
		},
	}

	return c.JSON(spec)
}

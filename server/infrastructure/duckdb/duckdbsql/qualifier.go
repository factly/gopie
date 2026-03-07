package duckdbsql


// QualifyUnqualifiedTables sets the schema for all unqualified tables in the AST.
// CTEs are ignored.
func (a *AST) QualifyUnqualifiedTables(schemaName string) error {
	if a.ast == nil {
		return nil
	}

	statements := toNodeArray(a.ast, astKeyStatements)
	for _, stmt := range statements {
		node := toNode(stmt, astKeyNode)
		if node == nil {
			continue
		}

		// Collect CTE names for exclusion
		cteNames := make(map[string]struct{})
		collectCTENames(node, cteNames)
		if withArr, ok := node["with"].([]any); ok {
			for _, item := range withArr {
				if itemNode, ok := item.(map[string]any); ok {
					if cteName, ok := itemNode["cte_name"].(string); ok && cteName != "" {
						cteNames[cteName] = struct{}{}
					}
				}
			}
		}

		// Walk and qualify
		qualifyTablesInNode(node, schemaName, cteNames)
	}

	return nil
}


// qualifyTablesInNode recursively sets schemaName for unqualified table references
func qualifyTablesInNode(node astNode, schemaName string, cteNames map[string]struct{}) {
	if node == nil {
		return
	}

	nodeType := toString(node, astKeyType)
	switch nodeType {
	case "BASE_TABLE", "TABLE_REF": // handle both common AST types
		tableName := toString(node, "table_name")
		tableSchema := toString(node, "schema_name")
		catalogName := toString(node, "catalog_name")
		if tableName != "" {
			if _, isCTE := cteNames[tableName]; !isCTE {
				if catalogName == "" {
					if tableSchema == "" {
						// Unqualified table: set schema to the alias
						node["schema_name"] = schemaName
					} else {
						// Schema-qualified but no catalog (e.g. intermediate.table):
						// set catalog to the alias so DuckDB resolves it as alias.schema.table
						node["catalog_name"] = schemaName
					}
				}
			}
		}
	}

	// Recurse into children
	for _, value := range node {
		switch v := value.(type) {
		case map[string]any:
			qualifyTablesInNode(v, schemaName, cteNames)
		case []any:
			for _, item := range v {
				if itemNode, ok := item.(map[string]any); ok {
					qualifyTablesInNode(itemNode, schemaName, cteNames)
				}
			}
		}
	}
}

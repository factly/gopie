package duckdbsql

// TableNames extracts all unique table names from the parsed SQL query.
// It traverses the AST to find all table references, excluding CTE names.
func (a *AST) TableNames() ([]string, error) {
	if a.ast == nil {
		return nil, nil
	}

	tables := make(map[string]struct{})
	statements := toNodeArray(a.ast, astKeyStatements)
	for _, statement := range statements {
		// First, collect CTE names to exclude them from table names
		cteNames := make(map[string]struct{})
		node := toNode(statement, astKeyNode)
		if node != nil {
			collectCTENames(node, cteNames)
		}

		// Then find table names, excluding CTEs
		findTablesInNode(node, tables, cteNames)
	}

	tableNames := make([]string, 0, len(tables))
	for name := range tables {
		tableNames = append(tableNames, name)
	}

	return tableNames, nil
}

// collectCTENames collects all CTE names from the cte_map
func collectCTENames(node astNode, cteNames map[string]struct{}) {
	if node == nil {
		return
	}

	cteMap := toNode(node, astKeyCTE)
	if cteMap != nil {
		// Check the actual type of the "map" value
		if mapValue, exists := cteMap["map"]; exists {
			// Try accessing as an array first
			if mapArray, ok := mapValue.([]any); ok {
				for _, item := range mapArray {
					if itemNode, ok := item.(map[string]any); ok {
						// Look for CTE name in the "key" field
						if cteName := toString(itemNode, "key"); cteName != "" {
							cteNames[cteName] = struct{}{}
						}
					}
				}
			} else {
				// Try as a node
				mapNode := toNode(cteMap, "map")
				for cteName := range mapNode {
					cteNames[cteName] = struct{}{}
				}
			}
		}
	}
}

// findTablesInNode is a recursive helper function to walk the AST and collect table names.
func findTablesInNode(node astNode, tables map[string]struct{}, cteNames map[string]struct{}) {
	if node == nil {
		return
	}

	// Check if the current node is a base table reference. This is where the table name is found.
	if toString(node, astKeyType) == "BASE_TABLE" {
		if tableName := toString(node, "table_name"); tableName != "" {
			// Only include if it's not a CTE name
			if _, isCTE := cteNames[tableName]; !isCTE {
				tables[tableName] = struct{}{}
			}
		}
		return
	}

	// If it's not a table reference, recursively traverse its children.
	// This will handle all query types (SELECT, JOIN, CTE, Subquery, etc.).
	for _, value := range node {
		switch v := value.(type) {
		case map[string]any: // Child is a single node (astNode)
			findTablesInNode(v, tables, cteNames)
		case []any: // Child is an array of items
			for _, item := range v {
				// Check if the item in the array is a node before recursing
				if itemNode, ok := item.(map[string]any); ok {
					findTablesInNode(itemNode, tables, cteNames)
				}
			}
		}
	}
}

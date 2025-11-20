package duckdbsql

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
)

// parseExpressionList parses a SQL expression string (like "col > 10" or "col1, col2")
// into a list of AST nodes by wrapping it in a dummy SELECT statement,
// parsing it, and extracting the select_list.
func (a *AST) parseExpressionList(sqlExpressionList string) ([]astNode, error) {
	dummySQL := fmt.Sprintf("SELECT %s", sqlExpressionList)

	sqlAst, err := queryString(a.db, "select json_serialize_sql(?::VARCHAR)::BLOB", dummySQL)
	if err != nil {
		return nil, fmt.Errorf("parsing expression query '%s': %w", dummySQL, err)
	}

	rootNode := astNode{}
	decoder := json.NewDecoder(bytes.NewReader(sqlAst))
	decoder.UseNumber()
	if err = decoder.Decode(&rootNode); err != nil {
		if errMsg, ok := rootNode["error_message"].(string); ok && rootNode["error"] == true {
			return nil, fmt.Errorf("duckdb parsing error for '%s': %s", dummySQL, errMsg)
		}
		return nil, fmt.Errorf("decoding expression ast: %w", err)
	}
	if isError, ok := rootNode["error"].(bool); ok && isError {
		errMsg, _ := rootNode["error_message"].(string)
		return nil, fmt.Errorf("duckdb parsing error flag set for '%s': %s", dummySQL, errMsg)
	}

	statements := toNodeArray(rootNode, astKeyStatements)
	if len(statements) == 0 {
		return nil, fmt.Errorf("no statements found in parsed expression")
	}

	selectNode := toNode(statements[0], astKeyNode)
	if selectNode == nil {
		return nil, fmt.Errorf("no 'node' found in parsed expression statement")
	}

	selectList := toNodeArray(selectNode, astKeySelect)
	if len(selectList) == 0 {
		if sqlExpressionList != "" {
			if sqlExpressionList == "*" {
				return []astNode{
					{
						astKeyClass:       "STAR",
						astKeyType:        "STAR",
						astKeyAlias:       "",
						astKeyExcludeList: []any{}, // Add empty exclude list
					},
				}, nil
			}
			if nodeClass, ok := selectNode[astKeyClass].(string); ok && nodeClass != "" {
				return []astNode{selectNode}, nil
			}

			return nil, fmt.Errorf("parsing yielded empty select_list for non-empty input '%s'", sqlExpressionList)
		}
		return nil, fmt.Errorf("parsed select list is empty for '%s'", sqlExpressionList)

	}

	return selectList, nil
}

func (a *AST) AddWhere(condition string) error {
	if a.ast == nil {
		return fmt.Errorf("calling AddWhere on failed parse")
	}
	if len(a.rootNodes) == 0 {
		return fmt.Errorf("no root node found in query")
	}

	rootSelectNode := a.rootNodes[0]
	rootMap := rootSelectNode.ast

	existingWhereInterface, whereExists := rootMap[astKeyWhere]
	var combinedConditionSQL string

	if whereExists && existingWhereInterface != nil {
		_, err := json.Marshal(existingWhereInterface)
		if err != nil {
			return fmt.Errorf("failed to marshal existing where clause node: %w", err)
		}

		dummySelectAST := astNode{
			astKeyStatements: []any{
				map[string]any{ // statement node
					"node": map[string]any{ // select node
						astKeyType: "SELECT_NODE",
						astKeySelect: []any{map[string]any{
							"type":            "STAR",
							"class":           "STAR",
							astKeyExcludeList: []any{},
						}},
						astKeyWhere: existingWhereInterface,
						astKeyCTE: map[string]any{
							"map": []any{},
						},
						astKeyAggregateHandling: "STANDARD_HANDLING",
					},
				},
			},
		}
		tempAstJSONFull, errMarshal := json.Marshal(dummySelectAST)
		if errMarshal != nil {
			return fmt.Errorf("failed to marshal temporary AST for existing where clause: %w", errMarshal)
		}

		// Now deserialize the dummy SELECT statement
		existingWhereFullSQLBytes, errDeserialize := queryString(a.db, "SELECT json_deserialize_sql(?::JSON)::VARCHAR", string(tempAstJSONFull))
		if errDeserialize != nil {
			return fmt.Errorf("failed to deserialize existing where clause SQL using dummy SELECT: %w", errDeserialize)
		}

		// Extract the condition part after "WHERE"
		selectSQL := string(existingWhereFullSQLBytes)
		whereIndex := strings.Index(selectSQL, "WHERE")
		if whereIndex == -1 {
			fmt.Printf("Warning: Deserialized existing clause has no WHERE: %s\n", selectSQL)
			combinedConditionSQL = condition
		} else {
			existingCondition := strings.TrimSpace(selectSQL[whereIndex+len("WHERE"):])
			if existingCondition == "" {
				fmt.Printf("Warning: Extracted existing condition is empty: %s\n", selectSQL)
				combinedConditionSQL = condition
			} else {
				combinedConditionSQL = fmt.Sprintf("(%s) AND (%s)", existingCondition, condition)
			}
		}

	} else {
		combinedConditionSQL = condition
	}

	exprList, err := a.parseExpressionList(combinedConditionSQL)
	if err != nil {
		return fmt.Errorf("failed to parse combined where condition '%s': %w", combinedConditionSQL, err)
	}
	if len(exprList) != 1 {
		return fmt.Errorf("parsing combined where condition resulted in %d nodes, expected 1 for '%s'", len(exprList), combinedConditionSQL)
	}

	rootMap[astKeyWhere] = exprList[0]

	return nil
}

// SetSelectList replaces the main query's entire SELECT list with a new one.
// The columns string must be a valid SQL select list (e.g., "col1", "col1, col2", "*").
func (a *AST) SetSelectList(columns string) error {
	if a.ast == nil {
		return fmt.Errorf("calling SetSelectList on failed parse")
	}
	if len(a.rootNodes) == 0 {
		return fmt.Errorf("no root node found in query")
	}

	newSelectList, err := a.parseExpressionList(columns)
	if err != nil {
		return fmt.Errorf("failed to parse select list '%s': %w", columns, err)
	}
	rootNode := a.rootNodes[0].ast

	selectListInterface := make([]any, len(newSelectList))
	for i, node := range newSelectList {
		selectListInterface[i] = node
	}
	rootNode[astKeySelect] = selectListInterface

	return nil
}

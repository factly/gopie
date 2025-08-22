package duckdbsql

import "fmt"

func (a *AST) ToCountQuery() (string, error) {
	if a.ast == nil {
		return "", fmt.Errorf("calling ToCountQuery on failed parse")
	}
	if len(a.rootNodes) == 0 {
		return "", fmt.Errorf("no root node found in query")
	}

	rootNode := a.rootNodes[0].ast

	// 1. Remove ORDER BY from the modifiers array (preserve LIMIT for accurate counts)
	originalModifiers := toNodeArray(rootNode, astKeyModifiers)
	newModifiers := make([]astNode, 0, len(originalModifiers))
	for _, modifier := range originalModifiers {
		modifierType := toString(modifier, astKeyType)
		// Keep any modifier that is NOT for ORDER BY (preserve LIMIT for count accuracy)
		if modifierType != "ORDER_MODIFIER" {
			newModifiers = append(newModifiers, modifier)
		}
	}

	if len(newModifiers) > 0 {
		rootNode[astKeyModifiers] = newModifiers
	} else {
		// If no other modifiers are left, remove the key entirely
		delete(rootNode, astKeyModifiers)
	}

	// 2. Format the cleaned query
	cleanSQL, err := a.Format()
	if err != nil {
		return "", err
	}

	// 3. Wrap the clean query in a count subquery
	countQuery := fmt.Sprintf("SELECT count(*) FROM (%s)", cleanSQL)

	return countQuery, nil
}
